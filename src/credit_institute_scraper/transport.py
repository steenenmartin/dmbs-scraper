"""Bounded network work. Each job owns its session and any browser it launches."""

import asyncio
import json
import logging
import os
import traceback
from contextlib import AsyncExitStack
from time import monotonic
from urllib.parse import urlsplit

import aiohttp
from playwright.async_api import Browser, BrowserContext, Page, Route, async_playwright
from playwright.async_api import Error as BrowserError
from playwright.async_api import TimeoutError as BrowserTimeout

from .sources import ENDPOINTS

logger = logging.getLogger(__name__)

type JsonValue = dict[str, JsonValue] | list[JsonValue] | str | int | float | bool | None

FETCH_SECONDS = 90
RETRY_STATUS = {408, 429, 500, 502, 503, 504}
PAGE = "https://www.jyskebank.dk/bolig/realkreditkurser"
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "origin": "https://www.jyskebank.dk",
    "referer": PAGE,
}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0"
PAGE_FETCH = """async (url) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10000);
    try {
        const response = await fetch(url, {credentials: 'include',
            headers: {'accept': 'application/json, text/plain, */*'}, signal: controller.signal});
        return {ok: response.ok, status: response.status, text: await response.text()};
    } catch (error) { return {ok: false, error: String(error)}; }
    finally { clearTimeout(timer); }
}"""


class FetchError(Exception):
    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


async def close_resource(resource: Browser | BrowserContext) -> None:
    try:
        async with asyncio.timeout(5):
            await resource.close()
    except Exception:
        logger.info("Browser resource cleanup failed", exc_info=True)


async def prepare_jyske_page(page: Page) -> None:
    await page.goto(PAGE, wait_until="domcontentloaded", timeout=15000)
    for selector in (
        "button:has-text('Acceptér alle')",
        "button:has-text('Accepter')",
        "[data-testid='uc-accept-all']",
    ):
        try:
            await page.locator(selector).first.click(timeout=350)
            break
        except BrowserTimeout:
            pass
    await page.evaluate("window.scrollTo(0, 600); window.scrollTo(0, 0)")


async def jyske_page_payload(page: Page, url: str) -> JsonValue:
    """Read the site's own request, including any headers added by its scripts."""
    endpoint = urlsplit(url)
    started = monotonic()
    try:
        # Bound navigation, waiting for the API and reading its body together.
        async with asyncio.timeout(20):
            async with page.expect_response(
                lambda response: response.request.method == "GET"
                and urlsplit(response.url)[:3] == endpoint[:3],
                timeout=20000,
            ) as pending:
                await prepare_jyske_page(page)
            response = await pending.value
            logger.info(
                "fetch_path institute=Jyske url=%s path=page_response status=%s elapsed_ms=%.0f",
                url,
                response.status,
                (monotonic() - started) * 1000,
            )
            if not response.ok:
                raise FetchError(f"Jyske page response HTTP {response.status}")
            return await response.json()
    except (TimeoutError, BrowserTimeout) as error:
        raise FetchError("Jyske page response timed out", retryable=True) from error


async def jyske(url: str, *, full_page: bool = False) -> JsonValue:
    started = monotonic()
    async with async_playwright() as runtime, AsyncExitStack() as cleanup:
        browser = await runtime.firefox.launch(
            executable_path=os.getenv("FIREFOX_EXECUTABLE_PATH") or None,
            headless=True,
        )
        cleanup.push_async_callback(close_resource, browser)
        context = await browser.new_context(locale="da-DK", user_agent=USER_AGENT)
        cleanup.push_async_callback(close_resource, context)
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['da-DK','da','en-US','en']});
            Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
        """)

        async def route_request(route: Route) -> None:
            blocked = (
                "doubleclick.net",
                "google-analytics.com",
                "googletagmanager.com",
                "facebook.com",
                "facebook.net",
                "hotjar.com",
                "azure.com",
                "optimizely.com",
                "cdn.segment.com",
            )
            parsed_url = urlsplit(route.request.url)
            # Save memory on the first attempt, but restore the previously
            # working page on retries in case its initialization is required.
            optional_app = not full_page and (
                parsed_url.hostname == "jyskebank.tv"
                or (
                    parsed_url.hostname == "calculators.jyskebank.dk"
                    and parsed_url.path.startswith("/jyske-kursliste-app/")
                )
            )
            if route.request.resource_type in {
                "image",
                "media",
                "font",
                "stylesheet",
            } or any(h in route.request.url for h in blocked) or optional_app:
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", route_request)
        page = await context.new_page()
        if full_page:
            try:
                return await jyske_page_payload(page, url)
            except (FetchError, json.JSONDecodeError) as error:
                logger.info("Jyske page response unavailable url=%s error=%s", url, error)
                release_error_frames(error)
        else:
            # The lean profile blocks the quote application, so it cannot emit
            # a native API response. Do not spend its budget waiting for one.
            await prepare_jyske_page(page)
        result = await page.evaluate(PAGE_FETCH, url)
        logger.info(
            "fetch_path institute=Jyske url=%s path=in_page status=%s error=%s elapsed_ms=%.0f profile=%s",
            url,
            result.get("status"),
            result.get("error"),
            (monotonic() - started) * 1000,
            "full" if full_page else "lean",
        )
        if result.get("ok"):
            return json.loads(result["text"])
        if result.get("text"):
            # Only failed public feed responses; never log cookies/headers or
            # successful payloads. Keep enough context to distinguish HTTP 400s.
            logger.info(
                "fetch_response institute=Jyske url=%s status=%s body_excerpt=%r",
                url, result.get("status"), result["text"][:300],
            )
        response = await context.request.get(url, headers=HEADERS, max_redirects=3, timeout=10000)
        logger.info(
            "fetch_path institute=Jyske url=%s path=context_request status=%s elapsed_ms=%.0f",
            url,
            response.status,
            (monotonic() - started) * 1000,
        )
        if not response.ok:
            # The cookie-sharing HTTP fallback can return 403 even when the
            # browser failure was transient. Preserve both paths in the error;
            # retry() closes this session before starting a fresh browser.
            browser_transient = (
                bool(result.get("error"))
                or result.get("status") in RETRY_STATUS | {403}
            )
            raise FetchError(
                f"Jyske HTTP {response.status}; in-page status={result.get('status')} "
                f"error={result.get('error')}",
                browser_transient or response.status in RETRY_STATUS | {403},
            )
        return await response.json()


async def request_json(
    session: aiohttp.ClientSession, institute: str, url: str, *, attempt: int = 1
) -> JsonValue:
    if institute == "Jyske":
        started = monotonic()
        try:
            async with session.get(
                url,
                headers={**HEADERS, "user-agent": USER_AGENT},
                max_redirects=3,
                timeout=aiohttp.ClientTimeout(total=10, connect=5),
            ) as response:
                logger.info(
                    "fetch_path institute=Jyske url=%s path=direct status=%s elapsed_ms=%.0f",
                    url,
                    response.status,
                    (monotonic() - started) * 1000,
                )
                if response.status < 400:
                    return await response.json(content_type=None)
        except TimeoutError:
            logger.info(
                "fetch_path institute=Jyske url=%s path=direct error=TimeoutError elapsed_ms=%.0f",
                url,
                (monotonic() - started) * 1000,
            )
        # Release the HTTP response before starting the browser/Node processes.
        return await jyske(url, full_page=attempt > 1)
    async with session.get(url) as response:
        if response.status >= 400:
            raise FetchError(f"HTTP {response.status}: {url}", response.status in RETRY_STATUS)
        return await response.json(content_type=None)


def release_error_frames(error: BaseException) -> None:
    """Expected fetch failures are data; do not retain their request object graphs."""
    pending, seen = [error], set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        pending.extend(e for e in (current.__cause__, current.__context__) if e is not None)
        if current.__traceback__ is not None:
            traceback.clear_frames(current.__traceback__)
        current.__traceback__ = None
        current.__cause__ = None
        current.__context__ = None


async def retry(
    session: aiohttp.ClientSession,
    institute: str,
    url: str,
    results: dict[str, JsonValue | Exception],
) -> None:
    started = monotonic()
    for attempt in range(1, 4):
        try:
            results[url] = await request_json(session, institute, url, attempt=attempt)
            logger.info(
                "fetch_succeeded institute=%s url=%s attempt=%d elapsed_ms=%.0f",
                institute,
                url,
                attempt,
                (monotonic() - started) * 1000,
            )
            return
        except (
            FetchError,
            TimeoutError,
            aiohttp.ClientError,
            BrowserError,
            json.JSONDecodeError,
            UnicodeDecodeError,
        ) as error:
            transient = isinstance(
                error,
                (
                    TimeoutError,
                    BrowserTimeout,
                    aiohttp.ClientConnectionError,
                    aiohttp.ClientPayloadError,
                ),
            )
            if isinstance(error, (aiohttp.ClientSSLError, aiohttp.InvalidURL)):
                transient = False
            if isinstance(error, FetchError):
                transient = error.retryable
            if isinstance(error, BrowserError) and not isinstance(error, BrowserTimeout):
                transient = any(
                    s in str(error).lower()
                    for s in (
                        "net::err_connection",
                        "econnreset",
                        "econnrefused",
                        "etimedout",
                        "socket hang up",
                        "connection reset",
                        "connection closed",
                        "ns_error_net",
                        "page crashed",
                        "target page, context or browser has been closed",
                    )
                )
            will_retry = transient and attempt < 3
            logger.info(
                "fetch_failed institute=%s url=%s attempt=%d elapsed_ms=%.0f error=%s "
                "message=%s retry=%s",
                institute,
                url,
                attempt,
                (monotonic() - started) * 1000,
                type(error).__name__,
                error,
                will_retry,
            )
            release_error_frames(error)
            if not will_retry:
                results[url] = error
                return
            # A new browser immediately after a rejection can hit the same
            # transient failure. Jyske still shares the 90-second total budget.
            await asyncio.sleep(attempt * 5 if institute == "Jyske" else attempt)
        except Exception as error:
            error.add_note(f"Fetch failed: institute={institute}, url={url}, attempt={attempt}")
            raise


async def fetch(institute: str) -> dict[str, JsonValue | Exception]:
    """One payload per unique endpoint; preserve successes when another endpoint times out."""
    urls = tuple(dict.fromkeys(ENDPOINTS[institute]))
    results: dict[str, JsonValue | Exception] = {}
    try:
        async with asyncio.timeout(FETCH_SECONDS):
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=20, connect=5)
            ) as session:
                async with asyncio.TaskGroup() as tasks:
                    for url in urls:
                        tasks.create_task(retry(session, institute, url, results))
    except TimeoutError:
        pass
    return {
        url: results.get(
            url,
            TimeoutError(f"{institute} url={url} exceeded {FETCH_SECONDS}s fetch budget"),
        )
        for url in urls
    }
