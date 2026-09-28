import asyncio
import gc
import json
import subprocess
import unittest
import weakref
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import aiohttp
import playwright
from aiohttp import web

from src.credit_institute_scraper import transport


class NetworkTests(unittest.IsolatedAsyncioTestCase):
    async def test_expected_failures_release_request_objects_before_retry_or_return(self):
        class ResponseBuffer:
            pass

        references = []

        async def failing_request(session, institute, url, *, attempt=1):
            self.assertTrue(all(ref() is None for ref in references))
            buffer = ResponseBuffer()
            buffer.body = bytearray(1024 * 1024)
            references.append(weakref.ref(buffer))
            try:
                raise TimeoutError("body timed out")
            except TimeoutError as cause:
                raise transport.FetchError("Jyske fetch timed out", retryable=True) from cause

        enabled = gc.isenabled()
        gc.disable()
        try:
            with (
                patch.object(transport, "request_json", failing_request),
                patch.object(transport.asyncio, "sleep", AsyncMock()),
            ):
                results = {}
                await transport.retry(None, "Jyske", "url", results)
            self.assertEqual(len(references), 11)
            self.assertTrue(all(ref() is None for ref in references))
            self.assertEqual(str(results["url"]), "Jyske fetch timed out")
        finally:
            if enabled:
                gc.enable()

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
            (transport.BrowserError("Page.evaluate: Execution context was destroyed, most likely because of a navigation"), 3),
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

        async def request(session, institute, url, *, attempt=1):
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

    async def test_jyske_can_recover_after_the_old_three_attempt_limit(self):
        request = AsyncMock(side_effect=[
            *[transport.FetchError("HTTP 403", retryable=True) for _ in range(4)],
            {"recovered": True},
        ])
        with (
            patch.object(transport, "request_json", request),
            patch.object(transport.asyncio, "sleep", AsyncMock()) as sleep,
        ):
            results = await transport.fetch("Jyske")
        self.assertEqual(results, {transport.ENDPOINTS["Jyske"][0]: {"recovered": True}})
        self.assertEqual(request.await_count, 5)
        self.assertEqual(sleep.await_args_list, [call(5)] * 4)

    async def test_total_budget_cancels_hang_but_retains_other_endpoint(self):
        cancelled = asyncio.Event()

        async def request(session, institute, url, *, attempt=1):
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

    async def test_budget_timeout_keeps_last_failure_without_retaining_its_frames(self):
        error = transport.FetchError("Jyske HTTP 403; in-page status=400", retryable=True)
        async def request(session, institute, url, *, attempt=1):
            if attempt == 1:
                raise error
            await asyncio.Event().wait()

        with (
            patch.object(transport, "request_json", request),
            patch.object(transport.asyncio, "sleep", AsyncMock()),
            patch.object(transport, "JYSKE_FETCH_SECONDS", 0.05),
        ):
            result = (await transport.fetch("Jyske"))[transport.ENDPOINTS["Jyske"][0]]
        self.assertIsInstance(result, TimeoutError)
        self.assertIn("exceeded 0.05s fetch budget", str(result))
        self.assertIn("last_error=FetchError: Jyske HTTP 403; in-page status=400", str(result))
        self.assertIsNone(error.__traceback__)

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

    async def test_jyske_direct_http_uses_headers_and_starts_browser_only_on_failure(self):
        observed = []

        async def serve(request):
            observed.append(dict(request.headers))
            if request.path == "/blocked":
                return web.Response(status=403, text="Forbidden")
            return web.Response(text='{"fastRenteProdukter": []}')

        app = web.Application()
        app.router.add_get("/{path}", serve)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        base = f"http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}"
        try:
            async with aiohttp.ClientSession() as session:
                with patch.object(transport, "jyske", AsyncMock(return_value={"fallback": True})) as browser:
                    result = await transport.request_json(session, "Jyske", base + "/prices")
                    self.assertEqual(result, {"fastRenteProdukter": []})
                    browser.assert_not_awaited()
                    result = await transport.request_json(session, "Jyske", base + "/blocked")
                    self.assertEqual(result, {"fallback": True})
                    browser.assert_awaited_once_with(base + "/blocked", fresh_session=False)
            for headers in observed:
                normalized = {key.lower(): value for key, value in headers.items()}
                self.assertIn("Chrome/", normalized["user-agent"])
                self.assertEqual(normalized["sec-fetch-mode"], "cors")
                self.assertEqual(normalized["sec-fetch-dest"], "empty")
                self.assertNotIn("sec-fetch-user", normalized)
                self.assertNotIn("upgrade-insecure-requests", normalized)
                for key, value in transport.HEADERS.items():
                    self.assertEqual(normalized[key], value)
        finally:
            await runner.cleanup()


class BrowserTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        session_patch = patch.object(transport, "_jyske_session", None)
        session_patch.start()
        self.addCleanup(session_patch.stop)
        http_patch = patch.object(transport, "_jyske_http_session", None)
        http_patch.start()
        self.addCleanup(http_patch.stop)

    def http_cookie(self, domain=".jyskebank.dk", name="example", value="private-http-value"):
        return transport.Cookie(
            version=0, name=name, value=value, port=None, port_specified=False,
            domain=domain, domain_specified=domain.startswith("."), domain_initial_dot=domain.startswith("."),
            path="/api", path_specified=True, secure=True, expires=None, discard=True,
            comment=None, comment_url=None, rest={"HttpOnly": None, "SameSite": "None"},
        )

    def test_http_cookie_snapshot_preserves_scope_and_is_detached_and_bounded(self):
        jar = transport.CookieJar()
        cookie = self.http_cookie(domain="jyskeberegner-api.jyskebank.dk")
        jar.set_cookie(cookie)
        expired = self.http_cookie(name="expired")
        expired.expires = 1
        jar.set_cookie(expired)
        jar.set_cookie(self.http_cookie(domain="not-jyskebank.dk"))
        with patch.object(transport, "monotonic", return_value=100):
            transport.remember_jyske_http_cookies(jar)
            cookie.value = "changed-after-capture"
            restored = list(transport.jyske_http_cookies())
            self.assertEqual(len(restored), 1)
            self.assertEqual(restored[0].value, "private-http-value")
            self.assertFalse(restored[0].domain_specified)
            self.assertEqual(restored[0].path, "/api")
            self.assertTrue(restored[0].secure)
            self.assertTrue(restored[0].has_nonstandard_attr("HttpOnly"))
            restored[0].value = "changed-after-restore"
            self.assertEqual(next(iter(transport.jyske_http_cookies())).value, "private-http-value")
        with patch.object(transport, "monotonic", return_value=100 + transport.JYSKE_SESSION_SECONDS):
            self.assertEqual(list(transport.jyske_http_cookies()), [])
            self.assertIsNone(transport._jyske_http_session)
        jar.set_cookie(self.http_cookie(value="x" * transport.JYSKE_SESSION_MAX_BYTES))
        transport.remember_jyske_http_cookies(jar)
        self.assertIsNone(transport._jyske_http_session)

    async def test_http_cookies_survive_session_close_and_honor_server_deletion(self):
        first, second = self.fixture(direct=True), self.fixture(direct=True)
        first[2].cookies.jar.set_cookie(self.http_cookie())
        with (
            patch.object(transport, "BrowserHttpSession", side_effect=[first[2], second[2]]) as factory,
            patch.object(transport, "async_playwright") as browser,
            self.assertLogs(level="INFO") as logs,
        ):
            await transport.request_json(None, "Jyske", transport.ENDPOINTS["Jyske"][0])
            first[2].__aexit__.assert_awaited_once()
            await transport.request_json(None, "Jyske", transport.ENDPOINTS["Jyske"][0])
        self.assertEqual(list(factory.call_args_list[0].kwargs["cookies"]), [])
        self.assertEqual(next(iter(factory.call_args_list[1].kwargs["cookies"])).value, "private-http-value")
        self.assertIsNone(transport._jyske_http_session)  # The second response's jar is empty.
        self.assertIn("session_restored=True", " ".join(logs.output))
        self.assertNotIn("private-http-value", " ".join(logs.output))
        browser.assert_not_called()
        self.assertIsNone(transport._jyske_session)

    def fixture(self, direct=False, in_page=True):
        runtime = MagicMock()
        manager = MagicMock()
        manager.__aenter__ = AsyncMock(return_value=runtime)
        manager.__aexit__ = AsyncMock(return_value=False)
        response = AsyncMock()
        response.ok, response.status = direct, 200 if direct else 403
        response.status_code = response.status
        response.headers = {"content-type": "application/json"}
        response.json.return_value = {"direct": True}
        response.text = '{"direct": true}'
        request = MagicMock()
        request.cookies.jar = transport.CookieJar()
        request.get = AsyncMock(return_value=response)
        self.response_context = request
        self.response_context.__aenter__ = AsyncMock(return_value=request)
        self.response_context.__aexit__ = AsyncMock(return_value=False)
        browser_http_patch = patch.object(transport, "BrowserHttpSession", return_value=request)
        browser_http_patch.start()
        self.addCleanup(browser_http_patch.stop)
        self.session = request
        session_context = MagicMock()
        session_context.__aenter__ = AsyncMock(return_value=request)
        session_context.__aexit__ = AsyncMock(return_value=False)
        session_patch = patch.object(transport.aiohttp, "ClientSession", return_value=session_context)
        session_patch.start()
        self.addCleanup(session_patch.stop)
        browser, context = AsyncMock(), AsyncMock()
        runtime.firefox.launch = AsyncMock(return_value=browser)
        browser.new_context.return_value = context
        context.storage_state.return_value = {"cookies": [], "origins": []}
        context.cookies.return_value = []
        page = MagicMock()
        context.new_page.return_value = page
        page.goto = AsyncMock(return_value=MagicMock(status=200, headers={"content-type": "text/html"}))
        page.locator.return_value.first.click = AsyncMock()
        page.evaluate = AsyncMock(side_effect=[None, {"ok": in_page, "text": "{}", "status": 503}])
        native = AsyncMock()
        native.ok, native.status = False, 503
        native.headers = {"content-type": "application/json"}
        pending = MagicMock()
        pending.value = asyncio.get_running_loop().create_future()
        pending.value.set_result(native)
        page.expect_response.return_value.__aenter__ = AsyncMock(return_value=pending)
        page.expect_response.return_value.__aexit__ = AsyncMock(return_value=False)
        fallback = AsyncMock()
        fallback.ok, fallback.status = True, 200
        fallback.headers = {"content-type": "application/json"}
        fallback.json.return_value = {"fallback": True}
        context.request.get.return_value = fallback
        return manager, runtime, request, browser, context, page

    async def test_direct_success_does_not_start_playwright(self):
        manager, runtime, request, *_ = self.fixture(direct=True)
        with patch.object(transport, "async_playwright", return_value=manager) as playwright_start:
            self.assertEqual(await transport.request_json(self.session, "Jyske", "url"), {"direct": True})
        self.response_context.__aexit__.assert_awaited_once()
        playwright_start.assert_not_called()
        runtime.firefox.launch.assert_not_awaited()

    async def test_browser_http_certificate_failure_does_not_start_firefox(self):
        manager, _, request, *_ = self.fixture()
        request.get.side_effect = transport.BrowserHttpSSLError("certificate verification failed")
        with patch.object(transport, "async_playwright", return_value=manager) as browser:
            result = (await transport.fetch("Jyske"))[transport.ENDPOINTS["Jyske"][0]]
        self.assertIsInstance(result, transport.FetchError)
        self.assertFalse(result.retryable)
        request.get.assert_awaited_once()
        request.__aexit__.assert_awaited_once()
        browser.assert_not_called()

    async def test_total_budget_cancels_browser_http_and_closes_session(self):
        _, _, request, *_ = self.fixture()
        cancelled = asyncio.Event()

        async def hang(*args, **kwargs):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        request.get.side_effect = hang
        with (
            patch.object(transport, "JYSKE_FETCH_SECONDS", 0.05),
            patch.object(transport, "async_playwright") as browser,
        ):
            result = (await transport.fetch("Jyske"))[transport.ENDPOINTS["Jyske"][0]]
        self.assertIsInstance(result, TimeoutError)
        self.assertTrue(cancelled.is_set())
        request.__aexit__.assert_awaited_once()
        browser.assert_not_called()

    async def test_successful_session_is_reused_with_native_browser_identity(self):
        first, second = self.fixture(), self.fixture()
        payload = {"fastRenteProdukter": [{"isin": "DK0009420069"}]}
        state = {"cookies": [{"name": "example", "value": "test-value"}], "origins": []}
        first[4].storage_state.return_value = state
        first[5].evaluate.side_effect = [None, {"ok": True, "text": json.dumps(payload)}]
        with patch.object(transport, "async_playwright", side_effect=[first[0], second[0]]):
            self.assertEqual(await transport.jyske("url"), payload)
            first[3].close.assert_awaited_once()
            # The saved state is detached from the closed context's objects.
            state["cookies"][0]["value"] = "changed-after-capture"
            await transport.jyske("url")
        self.assertIsNone(first[3].new_context.call_args.kwargs["storage_state"])
        restored = second[3].new_context.call_args.kwargs["storage_state"]
        self.assertEqual(restored["cookies"][0]["value"], "test-value")
        for _, _, _, browser, context, _ in (first, second):
            self.assertNotIn("user_agent", browser.new_context.call_args.kwargs)
            self.assertEqual(browser.new_context.call_args.kwargs["timezone_id"], "Europe/Copenhagen")
            context.add_init_script.assert_not_awaited()
            browser.close.assert_awaited_once()

    async def test_session_snapshot_expires_and_is_size_limited(self):
        _, _, _, _, context, _ = self.fixture()
        payload = {"variabelRenteProdukter": [{"fastrenteperiode": 3}]}
        with patch.object(transport, "monotonic", return_value=100):
            await transport.remember_jyske_session(context, payload)
            self.assertIsNotNone(transport.jyske_session_state())
        with patch.object(transport, "monotonic", return_value=100 + transport.JYSKE_SESSION_SECONDS):
            self.assertIsNone(transport.jyske_session_state())
            self.assertIsNone(transport._jyske_session)
        context.storage_state.return_value = {"large": "x" * transport.JYSKE_SESSION_MAX_BYTES}
        self.assertEqual(await transport.remember_jyske_session(context, payload), payload)
        self.assertIsNone(transport._jyske_session)

    async def test_invalid_payload_and_snapshot_failure_do_not_create_session(self):
        _, _, _, _, context, _ = self.fixture()
        for payload in ({}, {"fastRenteProdukter": []}, "challenge"):
            self.assertEqual(await transport.remember_jyske_session(context, payload), payload)
        context.storage_state.assert_not_awaited()
        context.storage_state.side_effect = transport.BrowserError("context closed")
        payload = {"fastRenteProdukter": [{"isin": "DK0009420069"}]}
        self.assertEqual(await transport.remember_jyske_session(context, payload), payload)
        self.assertIsNone(transport._jyske_session)

    async def test_full_snapshot_timeout_preserves_cookies_for_the_next_browser(self):
        first, second = self.fixture(), self.fixture()
        payload = {"fastRenteProdukter": [{"isin": "DK0009420069"}]}
        cookies = [{"name": "example", "value": "private-session-value", "domain": ".jyskebank.dk", "path": "/"}]
        first[4].storage_state.side_effect = TimeoutError("storage collection stalled")
        first[4].cookies.return_value = cookies
        first[5].evaluate.side_effect = [None, {"ok": True, "text": json.dumps(payload)}]
        with (
            patch.object(transport, "async_playwright", side_effect=[first[0], second[0]]),
            self.assertLogs(level="INFO") as logs,
        ):
            self.assertEqual(await transport.jyske("url"), payload)
            cookies[0]["value"] = "changed-after-capture"
            await transport.jyske("url")
        restored = second[3].new_context.call_args.kwargs["storage_state"]
        self.assertEqual(restored["cookies"][0]["value"], "private-session-value")
        self.assertEqual(restored["origins"], [])
        first[4].cookies.assert_awaited_once_with([transport.PAGE, transport.ENDPOINTS["Jyske"][0]])
        self.assertIn("mode=cookies", " ".join(logs.output))
        self.assertNotIn("private-session-value", " ".join(logs.output))
        for fixture in (first, second):
            fixture[3].close.assert_awaited_once()
            fixture[4].close.assert_awaited_once()

    async def test_cookie_snapshot_is_bounded_and_never_discards_fetched_quotes(self):
        _, _, _, _, context, _ = self.fixture()
        payload = {"fastRenteProdukter": [{"isin": "DK0009420069"}]}
        context.storage_state.side_effect = TimeoutError()
        context.cookies.return_value = [{"name": "large", "value": "x" * transport.JYSKE_SESSION_MAX_BYTES}]
        self.assertEqual(await transport.remember_jyske_session(context, payload), payload)
        self.assertIsNone(transport._jyske_session)
        cancelled = asyncio.Event()

        async def stalled_cookies(*args):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        context.cookies.side_effect = stalled_cookies
        real_timeout = asyncio.timeout
        with patch.object(transport.asyncio, "timeout", side_effect=lambda seconds: real_timeout(0.02)):
            self.assertEqual(await transport.remember_jyske_session(context, payload), payload)
        self.assertTrue(cancelled.is_set())
        self.assertIsNone(transport._jyske_session)

    async def test_failed_attempt_discards_previous_session_before_retry(self):
        fixtures = [self.fixture(in_page=False), self.fixture()]
        cached = {"cookies": [{"name": "example", "value": "old"}], "origins": []}
        transport._jyske_session = (transport.monotonic() + 1800, json.dumps(cached))
        fixtures[0][4].request.get.return_value.ok = False
        fixtures[0][4].request.get.return_value.status = 403

        async def after_failure(delay):
            self.assertIsNone(transport._jyske_session)

        with (
            patch.object(transport, "async_playwright", side_effect=[f[0] for f in fixtures]),
            patch.object(transport.asyncio, "sleep", AsyncMock(side_effect=after_failure)),
        ):
            self.assertEqual(await transport.fetch("Jyske"), {transport.ENDPOINTS["Jyske"][0]: {}})
        self.assertEqual(fixtures[0][3].new_context.call_args.kwargs["storage_state"], cached)
        self.assertIsNone(fixtures[1][3].new_context.call_args.kwargs["storage_state"])

    async def test_in_page_fallback_succeeds_without_quality_warning(self):
        manager, _, request, browser, context, page = self.fixture()
        with (
            patch.object(transport, "async_playwright", return_value=manager),
            self.assertNoLogs(level="WARNING"),
        ):
            self.assertEqual(await transport.request_json(self.session, "Jyske", "url"), {})
        self.response_context.__aexit__.assert_awaited_once()
        context.close.assert_awaited_once()
        browser.close.assert_awaited_once()
        context.request.get.assert_not_awaited()
        self.assertEqual(page.goto.await_args.kwargs["wait_until"], "domcontentloaded")

    async def test_page_response_avoids_duplicate_api_requests(self):
        manager, _, _, browser, context, page = self.fixture()
        native = page.expect_response.return_value.__aenter__.return_value.value.result()
        native.ok, native.status = True, 200
        native.json.return_value = {"fastRenteProdukter": [{"isin": "DK0009420069"}]}
        with patch.object(transport, "async_playwright", return_value=manager):
            self.assertEqual(await transport.request_json(self.session, "Jyske", "url"), native.json.return_value)
        self.assertEqual(page.evaluate.await_count, 1)  # Scroll only, no synthetic fetch.
        context.request.get.assert_not_awaited()
        context.close.assert_awaited_once()
        browser.close.assert_awaited_once()

    async def test_repeated_navigation_challenges_are_bounded_without_synthetic_calls(self):
        manager, runtime, _, browser, context, page = self.fixture()
        page.goto.return_value = MagicMock(status=403, headers={
            "content-type": "text/html",
            "cf-mitigated": "challenge",
            "cf-ray": "navigation-ray-DUB",
            "set-cookie": "private-cookie",
        })
        with (
            patch.object(transport, "async_playwright", return_value=manager),
            patch.object(transport.asyncio, "sleep", AsyncMock()) as sleep,
        ):
            result = (await transport.fetch("Jyske"))[transport.ENDPOINTS["Jyske"][0]]
        self.assertIsInstance(result, transport.PageUnavailable)
        self.assertIn("navigation HTTP 403", str(result))
        self.assertIn("cf_mitigated=challenge", str(result))
        self.assertIn("cf_ray=navigation-ray-DUB", str(result))
        self.assertNotIn("private-cookie", str(result))
        self.assertIsNone(result.__traceback__)
        self.assertEqual(runtime.firefox.launch.await_count, 11)
        page.evaluate.assert_not_awaited()
        context.request.get.assert_not_awaited()
        self.assertEqual(sleep.await_args_list, [call(5)] * 10)
        self.assertEqual(context.close.await_count, 11)
        self.assertEqual(browser.close.await_count, 11)

    async def test_transient_navigation_failure_retries_then_reads_native_response(self):
        for status in (403, 503):
            with self.subTest(status=status):
                first, second = self.fixture(), self.fixture()
                first[5].goto.return_value.status = status
                if status == 403:
                    first[5].goto.return_value.headers = {"cf-mitigated": "challenge"}
                native = second[5].expect_response.return_value.__aenter__.return_value.value.result()
                native.ok, native.status = True, 200
                native.json.return_value = {"fastRenteProdukter": [{"isin": "DK0009420069"}]}

                async def after_cleanup(delay):
                    first[3].close.assert_awaited_once()
                    first[4].close.assert_awaited_once()
                    second[1].firefox.launch.assert_not_awaited()

                with (
                    patch.object(transport, "async_playwright", side_effect=[first[0], second[0]]),
                    patch.object(transport.asyncio, "sleep", AsyncMock(side_effect=after_cleanup)) as sleep,
                ):
                    result = await transport.fetch("Jyske")
                self.assertEqual(result[transport.ENDPOINTS["Jyske"][0]], native.json.return_value)
                sleep.assert_awaited_once_with(5)
                first[5].evaluate.assert_not_awaited()
                for fixture in (first, second):
                    fixture[3].close.assert_awaited_once()
                    fixture[4].request.get.assert_not_awaited()

    async def test_page_response_matches_only_endpoint_gets(self):
        manager, _, _, _, _, page = self.fixture()
        url = transport.ENDPOINTS["Jyske"][0]
        with patch.object(transport, "async_playwright", return_value=manager):
            await transport.request_json(self.session, "Jyske", url, attempt=2)
        predicate = page.expect_response.call_args.args[0]
        response = MagicMock(url=url + "?cache=123")
        response.request.method = "GET"
        self.assertTrue(predicate(response))
        response.request.method = "OPTIONS"
        self.assertFalse(predicate(response))
        response.request.method = "GET"
        response.url = url + "/other"
        self.assertFalse(predicate(response))
        response.url = url.replace("jyskeberegner-api.jyskebank.dk", "example.com")
        self.assertFalse(predicate(response))

    async def test_direct_timeout_still_uses_browser_fallback(self):
        manager, _, request, browser, _, _ = self.fixture()
        self.response_context.__aenter__.side_effect = TimeoutError("direct request timed out")
        with patch.object(transport, "async_playwright", return_value=manager):
            self.assertEqual(await transport.request_json(self.session, "Jyske", "url"), {})
        browser.close.assert_awaited_once()

    async def test_page_timeout_or_bad_json_still_uses_in_page_fetch(self):
        for error in (
            transport.BrowserTimeout("no API response"),
            json.JSONDecodeError("bad", "", 0),
        ):
            with self.subTest(error=type(error).__name__):
                manager, _, _, _, _, page = self.fixture()
                waiter = page.expect_response.return_value
                native = waiter.__aenter__.return_value.value.result()
                native.ok, native.status = True, 200
                if isinstance(error, transport.BrowserTimeout):
                    waiter.__aexit__.side_effect = error
                else:
                    native.json.side_effect = error
                with patch.object(transport, "async_playwright", return_value=manager):
                    self.assertEqual(await transport.request_json(self.session, "Jyske", "url", attempt=2), {})
                self.assertEqual(page.evaluate.await_count, 2)

    async def test_page_body_stall_is_bounded_before_fallback(self):
        manager, _, _, _, _, page = self.fixture()
        native = page.expect_response.return_value.__aenter__.return_value.value.result()
        native.ok, native.status = True, 200
        cancelled = asyncio.Event()

        async def stalled_body():
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        native.json.side_effect = stalled_body
        real_timeout = asyncio.timeout
        with (
            patch.object(transport, "async_playwright", return_value=manager),
            patch.object(transport.asyncio, "timeout", side_effect=lambda seconds: real_timeout(0.05)),
        ):
            self.assertEqual(await transport.request_json(self.session, "Jyske", "url", attempt=2), {})
        self.assertTrue(cancelled.is_set())

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
            self.assertEqual(await transport.request_json(self.session, "Jyske", "url"), {"fallback": True})
        context.request.get.assert_awaited_once()
        browser.close.assert_awaited_once()
        self.assertIn("institute=Jyske url=url path=browser_http status=403", logs.output[0])
        self.assertTrue(any(
            "path=in_page status=None error=AbortError: body timed out" in entry
            for entry in logs.output
        ))
        self.assertIn("path=context_request status=200", logs.output[-1])
        self.assertTrue(all(
            "elapsed_ms=" in entry for entry in logs.output if "fetch_path" in entry
        ))

    async def test_blocks_video_but_loads_quote_application_on_first_attempt(self):
        manager, _, _, _, context, _ = self.fixture()
        with patch.object(transport, "async_playwright", return_value=manager):
            await transport.jyske("url")
        route_request = context.route.await_args.args[1]
        for resource_type, url, blocked in (
            ("document", "https://jyskebank.tv/v.ihtml/player.html", True),
            ("script", "https://jyskebank.tv/v.ihtml/player.js", True),
            ("script", "https://calculators.jyskebank.dk/jyske-kursliste-app/jyske-kursliste-app.js", False),
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
            await transport.request_json(self.session, "Jyske", "url")
        self.assertTrue(any(
            "institute=Jyske url=url path=in_page status=503" in entry for entry in logs.output
        ))

    async def test_blocked_fallback_preserves_statuses_for_retry(self):
        manager, _, request, _, context, page = self.fixture(in_page=False)
        page.evaluate.side_effect = [None, {"ok": False, "status": 400}]
        context.request.get.return_value.ok = False
        context.request.get.return_value.status = 403
        with (
            patch.object(transport, "async_playwright", return_value=manager),
            self.assertRaises(transport.FetchError) as raised,
        ):
            await transport.request_json(self.session, "Jyske", "url")
        self.assertTrue(raised.exception.retryable)
        self.assertIn("Jyske HTTP 403; in-page status=400", str(raised.exception))
        request.get.assert_called_once()

    async def test_network_error_and_400_retry_native_page_without_loading_video(self):
        fixtures = [self.fixture(in_page=False), self.fixture(in_page=False), self.fixture()]
        failures = [
            {"ok": False, "error": "TypeError: NetworkError when attempting to fetch resource."},
            {"ok": False, "status": 400, "text": "Bad Request" + "x" * 500},
        ]
        for fixture, failure in zip(fixtures, failures):
            fixture[5].evaluate.side_effect = [None, failure]
            fixture[4].request.get.return_value.ok = False
            fixture[4].request.get.return_value.status = 403
        with (
            patch.object(transport, "async_playwright", side_effect=[f[0] for f in fixtures]),
            patch.object(transport.asyncio, "sleep", AsyncMock()) as sleep,
            self.assertLogs(level="INFO") as logs,
        ):
            results = await transport.fetch("Jyske")
        self.assertEqual(results, {transport.ENDPOINTS["Jyske"][0]: {}})
        self.assertEqual(sleep.await_args_list, [call(5), call(5)])
        for attempt, (_, _, _, browser, context, _) in enumerate(fixtures, start=1):
            route_request = context.route.await_args.args[1]
            for resource_type, url, blocked in (
                ("script", "https://calculators.jyskebank.dk/jyske-kursliste-app/jyske-kursliste-app.js", False),
                ("document", "https://jyskebank.tv/v.ihtml/player.html", True),
                ("image", "https://www.jyskebank.dk/image.png", True),
                ("script", "https://www.jyskebank.dk/cdn-cgi/challenge-platform/scripts/jsd/main.js", False),
            ):
                with self.subTest(attempt=attempt, url=url):
                    route = AsyncMock()
                    route.request.resource_type, route.request.url = resource_type, url
                    await route_request(route)
                    self.assertEqual(route.abort.await_count, int(blocked))
                    self.assertEqual(route.continue_.await_count, int(not blocked))
            context.close.assert_awaited_once()
            browser.close.assert_awaited_once()
        paths = [line for line in logs.output if "path=in_page" in line]
        self.assertEqual(len(paths), 3)
        for line in paths:
            self.assertIn("profile=native", line)
        excerpt = next(line for line in logs.output if "body_excerpt=" in line)
        self.assertIn("Bad Request", excerpt)
        self.assertNotIn("x" * 300, excerpt)

    async def test_failed_context_cleanup_still_closes_browser(self):
        manager, _, _, browser, context, _ = self.fixture()
        context.close.side_effect = RuntimeError("closed")
        with (
            patch.object(transport, "async_playwright", return_value=manager),
            self.assertLogs(level="INFO"),
        ):
            await transport.request_json(self.session, "Jyske", "url")
        browser.close.assert_awaited_once()

    async def test_aborted_browser_then_403_retries_with_a_fresh_session(self):
        first = self.fixture(in_page=False)
        second = self.fixture()
        manager, _, _, browser, context, page = first
        page.evaluate.side_effect = [None, {"ok": False, "error": "AbortError: body timed out"}]
        context.request.get.return_value.ok = False
        context.request.get.return_value.status = 403

        async def after_cleanup(delay):
            self.assertEqual(delay, 5)
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

    async def test_navigation_during_evaluate_retries_after_browser_cleanup(self):
        first, second = self.fixture(), self.fixture()
        first[5].evaluate.side_effect = [
            None,
            transport.BrowserError(
                "Page.evaluate: Execution context was destroyed, most likely because of a navigation"
            ),
        ]

        async def after_cleanup(delay):
            self.assertEqual(delay, 5)
            first[3].close.assert_awaited_once()
            first[4].close.assert_awaited_once()
            second[1].firefox.launch.assert_not_awaited()

        with (
            patch.object(transport, "async_playwright", side_effect=[first[0], second[0]]),
            patch.object(transport.asyncio, "sleep", AsyncMock(side_effect=after_cleanup)),
        ):
            self.assertEqual(await transport.fetch("Jyske"), {transport.ENDPOINTS["Jyske"][0]: {}})
        second[3].close.assert_awaited_once()

    async def test_cloudflare_diagnostics_survive_in_final_error_without_cookies(self):
        manager, _, _, _, context, page = self.fixture(in_page=False)
        context.request.get.return_value.ok = False
        context.request.get.return_value.status = 403
        context.request.get.return_value.headers = {
            "content-type": "text/html",
            "cf-mitigated": "challenge",
            "cf-ray": "test-ray-CPH",
            "set-cookie": "private-cookie",
        }
        page.evaluate.side_effect = [None, {"ok": False, "status": 400}]
        with (
            patch.object(transport, "async_playwright", return_value=manager),
            self.assertLogs(level="INFO") as logs,
            self.assertRaises(transport.FetchError) as raised,
        ):
            await transport.request_json(self.session, "Jyske", "url")
        for detail in ("in-page status=400", "content_type=text/html", "cf_mitigated=challenge", "cf_ray=test-ray-CPH"):
            self.assertIn(detail, str(raised.exception))
        self.assertNotIn("private-cookie", str(raised.exception) + " ".join(logs.output))

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

    async def test_repeated_browser_abort_is_bounded_to_ten_retries(self):
        fixtures = [self.fixture(in_page=False) for _ in range(11)]
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
        self.assertEqual(sleep.await_args_list, [call(5)] * 10)
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
            patch.object(transport, "JYSKE_FETCH_SECONDS", 0.05),
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
            await transport.request_json(self.session, "Jyske", "url")
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
            if (delay !== 10000 || !cleared || result.ok || !result.error.includes('aborted')) process.exitCode = 1;
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
