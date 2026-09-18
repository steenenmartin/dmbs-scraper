import asyncio
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import aiohttp
import playwright
from aiohttp import web

from src.credit_institute_scraper import transport


class NetworkTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_transient_failures_are_retried(self):
        cases = [
            (
                transport.FetchError(str(code), code in transport.RETRY_STATUS),
                3 if code in transport.RETRY_STATUS else 1,
            )
            for code in (403, 404, 408, 429, 500, 502, 503, 504)
        ]
        cases += [
            (json.JSONDecodeError("bad JSON", "{", 1), 1),
            (TimeoutError(), 3),
            (aiohttp.ClientSSLError(None, OSError("certificate")), 1),
            (aiohttp.InvalidURL("bad"), 1),
            (transport.BrowserError("Page.goto: Page crashed"), 3),
            (transport.BrowserError("Target page, context or browser has been closed"), 3),
            (transport.BrowserError("Executable doesn't exist"), 1),
        ]
        for error, attempts in cases:
            request = AsyncMock(side_effect=error)
            sleep = AsyncMock()
            with (
                self.subTest(error=type(error).__name__),
                patch.object(transport, "request_json", request),
                patch.object(transport.asyncio, "sleep", sleep),
            ):
                results = {}
                await transport.retry(None, "Nordea", "url", results)
                self.assertIs(results["url"], error)
                self.assertEqual(request.await_count, attempts)
                self.assertEqual(sleep.await_args_list, [call(1), call(2)] if attempts == 3 else [])

    async def test_programming_errors_propagate_with_endpoint_context(self):
        for error in (
            TypeError("wrong argument"),
            AttributeError("missing method"),
            ValueError("bug"),
        ):
            request = AsyncMock(side_effect=error)
            with (
                self.subTest(error=type(error).__name__),
                patch.object(transport, "request_json", request),
                patch.object(transport.asyncio, "sleep", AsyncMock()) as sleep,
                self.assertRaises(ExceptionGroup) as raised,
            ):
                await transport.fetch("Nordea")
            self.assertEqual(raised.exception.exceptions, (error,))
            self.assertIsNotNone(error.__traceback__)
            self.assertEqual(
                error.__notes__,
                [
                    f"Fetch failed: institute=Nordea, url={transport.ENDPOINTS['Nordea'][0]}, attempt=1"
                ],
            )
            request.assert_awaited_once()
            sleep.assert_not_awaited()

    async def test_bad_json_preserves_success_from_other_endpoint(self):
        error = json.JSONDecodeError("bad JSON", "{", 1)

        async def request(session, institute, url):
            if url == "fixed":
                return {"ok": True}
            raise error

        with (
            patch.dict(transport.ENDPOINTS, {"RealKreditDanmark": ("fixed", "floating")}),
            patch.object(transport, "request_json", request),
        ):
            results = await transport.fetch("RealKreditDanmark")
        self.assertEqual(results, {"fixed": {"ok": True}, "floating": error})

    async def test_success_after_retry_is_not_an_issue(self):
        with (
            patch.object(
                transport,
                "request_json",
                AsyncMock(side_effect=[TimeoutError("body stalled"), {"data": 1}]),
            ),
            patch.object(transport.asyncio, "sleep", AsyncMock()),
            self.assertLogs(level="INFO") as logs,
        ):
            results = {}
            await transport.retry(None, "Nordea", "url", results)
        self.assertEqual(results, {"url": {"data": 1}})
        failed, succeeded = logs.output
        for context in (
            "institute=Nordea",
            "url=url",
            "attempt=1",
            "elapsed_ms=",
            "error=TimeoutError",
            "message=body stalled",
            "retry=True",
        ):
            self.assertIn(context, failed)
        self.assertIn("fetch_succeeded institute=Nordea url=url attempt=2", succeeded)
        self.assertIn("elapsed_ms=", succeeded)

    async def test_jyske_payload_is_fetched_once(self):
        request = AsyncMock(return_value={})
        with patch.object(transport, "request_json", request):
            results = await transport.fetch("Jyske")
        self.assertEqual(len(results), 1)
        self.assertEqual(request.await_count, 1)

    async def test_total_budget_cancels_hang_but_retains_other_endpoint(self):
        cancelled = asyncio.Event()

        async def request(session, institute, url):
            if url == "fast":
                return {"ok": True}
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        with (
            patch.dict(transport.ENDPOINTS, {"RealKreditDanmark": ("fast", "slow")}),
            patch.object(transport, "FETCH_SECONDS", 0.05),
            patch.object(transport, "request_json", request),
        ):
            results = await asyncio.wait_for(transport.fetch("RealKreditDanmark"), 2)
        self.assertEqual(results["fast"], {"ok": True})
        self.assertIsInstance(results["slow"], TimeoutError)
        self.assertTrue(cancelled.is_set())

    async def test_http_timeout_includes_a_hanging_response_body(self):
        release = asyncio.Event()

        async def serve(request):
            response = web.StreamResponse(headers={"Content-Type": "application/json"})
            await response.prepare(request)
            await response.write(b"{")
            await release.wait()
            return response

        app = web.Application()
        app.router.add_get("/", serve)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=0.05)) as session:
                with self.assertRaises(TimeoutError):
                    await transport.request_json(session, "Nordea", f"http://127.0.0.1:{port}/")
        finally:
            release.set()
            await runner.cleanup()

    async def test_http_status_is_checked_before_json(self):
        response = AsyncMock()
        response.status = 403
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=response)
        context.__aexit__ = AsyncMock(return_value=False)
        session = MagicMock(get=MagicMock(return_value=context))
        with self.assertRaises(transport.FetchError):
            await transport.request_json(session, "Nordea", "url")
        response.json.assert_not_awaited()
        context.__aexit__.assert_awaited_once()


class BrowserTests(unittest.IsolatedAsyncioTestCase):
    def fixture(self, direct=False, in_page=True):
        runtime = MagicMock()
        manager = MagicMock()
        manager.__aenter__ = AsyncMock(return_value=runtime)
        manager.__aexit__ = AsyncMock(return_value=False)
        response = AsyncMock()
        response.ok, response.status = direct, 200 if direct else 403
        response.json.return_value = {"direct": True}
        request = AsyncMock()
        request.get.return_value = response
        runtime.request.new_context = AsyncMock(return_value=request)
        browser, context = AsyncMock(), AsyncMock()
        runtime.firefox.launch = AsyncMock(return_value=browser)
        browser.new_context.return_value = context
        page = MagicMock()
        context.new_page.return_value = page
        page.goto = AsyncMock()
        page.locator.return_value.first.click = AsyncMock()
        page.evaluate = AsyncMock(side_effect=[None, {"ok": in_page, "text": "{}", "status": 503}])
        fallback = AsyncMock()
        fallback.ok, fallback.status = True, 200
        fallback.json.return_value = {"fallback": True}
        context.request.get.return_value = fallback
        return manager, runtime, request, browser, context, page

    async def test_direct_success_does_not_launch_browser(self):
        manager, runtime, request, *_ = self.fixture(direct=True)
        with patch.object(transport, "async_playwright", return_value=manager):
            self.assertEqual(await transport.jyske("url"), {"direct": True})
        request.dispose.assert_awaited_once()
        runtime.firefox.launch.assert_not_awaited()

    async def test_in_page_fallback_succeeds_without_quality_warning(self):
        manager, _, request, browser, context, page = self.fixture()
        with (
            patch.object(transport, "async_playwright", return_value=manager),
            self.assertNoLogs(level="WARNING"),
        ):
            self.assertEqual(await transport.jyske("url"), {})
        request.dispose.assert_awaited_once()
        context.close.assert_awaited_once()
        browser.close.assert_awaited_once()
        context.request.get.assert_not_awaited()
        self.assertEqual(page.goto.await_args.kwargs["wait_until"], "domcontentloaded")

    async def test_context_request_fallback_is_preserved(self):
        manager, _, _, browser, context, page = self.fixture(in_page=False)
        page.evaluate.side_effect = [
            None,
            {"ok": False, "error": "AbortError: body timed out"},
        ]
        with (
            patch.object(transport, "async_playwright", return_value=manager),
            self.assertLogs(level="INFO") as logs,
        ):
            self.assertEqual(await transport.jyske("url"), {"fallback": True})
        context.request.get.assert_awaited_once()
        browser.close.assert_awaited_once()
        self.assertIn("institute=Jyske url=url path=direct status=403", logs.output[0])
        self.assertIn("path=in_page status=None error=AbortError: body timed out", logs.output[1])
        self.assertIn("path=context_request status=200", logs.output[2])
        self.assertTrue(all("elapsed_ms=" in entry for entry in logs.output))

    async def test_blocks_video_and_duplicate_quote_ui_but_keeps_browser_fetch_dependencies(self):
        manager, _, _, _, context, _ = self.fixture()
        with patch.object(transport, "async_playwright", return_value=manager):
            await transport.jyske("url")
        route_request = context.route.await_args.args[1]
        for resource_type, url, blocked in (
            ("document", "https://jyskebank.tv/v.ihtml/player.html", True),
            ("script", "https://jyskebank.tv/v.ihtml/player.js", True),
            ("script", "https://calculators.jyskebank.dk/jyske-kursliste-app/jyske-kursliste-app.js", True),
            ("document", transport.PAGE, False),
            ("fetch", transport.ENDPOINTS["Jyske"][0], False),
            ("script", "https://www.jyskebank.dk/cdn-cgi/challenge-platform/scripts/jsd/main.js", False),
            ("script", "https://policy.app.cookieinformation.com/uc.js", False),
            ("script", "https://calculators.jyskebank.dk/other-app/script.js", False),
        ):
            with self.subTest(url=url):
                route = AsyncMock()
                route.request.resource_type = resource_type
                route.request.url = url
                await route_request(route)
                self.assertEqual(route.abort.await_count, int(blocked))
                self.assertEqual(route.continue_.await_count, int(not blocked))

    async def test_in_page_http_failure_logs_status_before_context_fallback(self):
        manager, _, _, _, _, _ = self.fixture(in_page=False)
        with (
            patch.object(transport, "async_playwright", return_value=manager),
            self.assertLogs(level="INFO") as logs,
        ):
            await transport.jyske("url")
        self.assertIn("institute=Jyske url=url path=in_page status=503", logs.output[1])

    async def test_failed_context_cleanup_still_closes_browser(self):
        manager, _, _, browser, context, _ = self.fixture()
        context.close.side_effect = RuntimeError("closed")
        with (
            patch.object(transport, "async_playwright", return_value=manager),
            self.assertLogs(level="INFO"),
        ):
            await transport.jyske("url")
        browser.close.assert_awaited_once()

    async def test_aborted_browser_then_403_retries_with_a_fresh_session(self):
        first = self.fixture(in_page=False)
        second = self.fixture()
        manager, _, _, browser, context, page = first
        page.evaluate.side_effect = [None, {"ok": False, "error": "AbortError: body timed out"}]
        context.request.get.return_value.ok = False
        context.request.get.return_value.status = 403

        async def after_cleanup(delay):
            self.assertEqual(delay, 1)
            context.close.assert_awaited_once()
            browser.close.assert_awaited_once()
            manager.__aexit__.assert_awaited_once()
            second[1].firefox.launch.assert_not_awaited()

        with (
            patch.object(transport, "async_playwright", side_effect=[manager, second[0]]),
            patch.object(transport.asyncio, "sleep", AsyncMock(side_effect=after_cleanup)),
            self.assertLogs(level="INFO") as logs,
        ):
            results = await transport.fetch("Jyske")
        self.assertEqual(results, {transport.ENDPOINTS["Jyske"][0]: {}})
        second[1].firefox.launch.assert_awaited_once()
        second[3].close.assert_awaited_once()
        failed = next(line for line in logs.output if "fetch_failed" in line)
        self.assertIn("AbortError: body timed out", failed)
        self.assertIn("Jyske HTTP 403", failed)
        self.assertIn("retry=True", failed)

    async def test_jyske_browser_failure_is_not_hidden_by_fallback_status(self):
        for in_page, fallback, retryable in (
            ({"status": 503}, 404, True),
            ({"status": 403}, 403, True),
            ({"status": 404}, 403, True),
            ({"status": 404}, 404, False),
        ):
            with self.subTest(in_page=in_page, fallback=fallback):
                manager, _, _, browser, context, page = self.fixture(in_page=False)
                page.evaluate.side_effect = [None, {"ok": False, **in_page}]
                context.request.get.return_value.ok = False
                context.request.get.return_value.status = fallback
                with (
                    patch.object(transport, "async_playwright", return_value=manager),
                    self.assertRaises(transport.FetchError) as raised,
                ):
                    await transport.jyske("url")
                self.assertEqual(raised.exception.retryable, retryable)
                browser.close.assert_awaited_once()

    async def test_repeated_browser_abort_is_bounded_to_three_attempts(self):
        fixtures = [self.fixture(in_page=False) for _ in range(3)]
        for _, _, _, _, context, page in fixtures:
            page.evaluate.side_effect = [None, {"ok": False, "error": "AbortError"}]
            context.request.get.return_value.ok = False
            context.request.get.return_value.status = 403
        with (
            patch.object(transport, "async_playwright", side_effect=[f[0] for f in fixtures]),
            patch.object(transport.asyncio, "sleep", AsyncMock()) as sleep,
        ):
            results = await transport.fetch("Jyske")
        error = results[transport.ENDPOINTS["Jyske"][0]]
        self.assertIsInstance(error, transport.FetchError)
        self.assertIn("AbortError", str(error))
        self.assertEqual(sleep.await_args_list, [call(1), call(2)])
        for _, _, _, browser, context, _ in fixtures:
            context.close.assert_awaited_once()
            browser.close.assert_awaited_once()

    async def test_total_budget_closes_hanging_browser(self):
        manager, _, _, browser, context, page = self.fixture()

        async def hang(*args):
            await asyncio.Event().wait()

        page.evaluate.side_effect = hang
        with (
            patch.object(transport, "async_playwright", return_value=manager),
            patch.object(transport, "FETCH_SECONDS", 0.05),
        ):
            results = await asyncio.wait_for(transport.fetch("Jyske"), 2)
        self.assertIsInstance(results[transport.ENDPOINTS["Jyske"][0]], TimeoutError)
        context.close.assert_awaited_once()
        browser.close.assert_awaited_once()
        manager.__aexit__.assert_awaited_once()

    async def test_cancellation_closes_owned_browser_and_context(self):
        manager, _, _, browser, context, page = self.fixture()
        page.goto.side_effect = asyncio.CancelledError()
        with (
            patch.object(transport, "async_playwright", return_value=manager),
            self.assertRaises(asyncio.CancelledError),
        ):
            await transport.jyske("url")
        context.close.assert_awaited_once()
        browser.close.assert_awaited_once()

    def test_actual_browser_script_aborts_body_and_clears_timer(self):
        driver = Path(playwright.__file__).parent / "driver"
        node = driver / ("node.exe" if (driver / "node.exe").exists() else "node")
        harness = (
            """
            const timer = global.setTimeout, clear = global.clearTimeout;
            let delay, cleared = false;
            global.setTimeout = (fn, ms) => {delay = ms; return timer(fn, 5)};
            global.clearTimeout = id => {cleared = true; clear(id)};
            global.fetch = async (_, {signal}) => ({ok: true, status: 200,
                text: () => new Promise((_, reject) => signal.addEventListener('abort', () => reject(new Error('aborted'))))});
        """
            + "\n("
            + transport.PAGE_FETCH
            + """
        )('url').then(result => {
            if (delay !== 30000 || !cleared || result.ok || !result.error.includes('aborted')) process.exitCode = 1;
        });
        """
        )
        result = subprocess.run(
            [str(node), "-e", harness],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
