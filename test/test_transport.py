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

        async def failing_request(session, institute, url):
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
            self.assertEqual(len(references), 3)
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
                    browser.assert_awaited_once_with(base + "/blocked")
            for headers in observed:
                normalized = {key.lower(): value for key, value in headers.items()}
                self.assertEqual(normalized["user-agent"], transport.USER_AGENT)
                for key, value in transport.HEADERS.items():
                    self.assertEqual(normalized[key], value)
        finally:
            await runner.cleanup()


class BrowserTests(unittest.IsolatedAsyncioTestCase):
    def fixture(self, direct=False, in_page=True):
        runtime = MagicMock()
        manager = MagicMock()
        manager.__aenter__ = AsyncMock(return_value=runtime)
        manager.__aexit__ = AsyncMock(return_value=False)
        response = AsyncMock()
        response.ok, response.status = direct, 200 if direct else 403
        response.json.return_value = {"direct": True}
        request = MagicMock()
        self.response_context = request.get.return_value
        self.response_context.__aenter__ = AsyncMock(return_value=response)
        self.response_context.__aexit__ = AsyncMock(return_value=False)
        self.session = request
        browser, context = AsyncMock(), AsyncMock()
        runtime.firefox.launch = AsyncMock(return_value=browser)
        browser.new_context.return_value = context
        page = MagicMock()
        context.new_page.return_value = page
        page.goto = AsyncMock()
        page.locator.return_value.first.click = AsyncMock()
        page.evaluate = AsyncMock(side_effect=[None, {"ok": in_page, "text": "{}", "status": 503}])
        native = AsyncMock()
        native.ok, native.status = False, 503
        pending = MagicMock()
        pending.value = asyncio.get_running_loop().create_future()
        pending.value.set_result(native)
        page.expect_response.return_value.__aenter__ = AsyncMock(return_value=pending)
        page.expect_response.return_value.__aexit__ = AsyncMock(return_value=False)
        fallback = AsyncMock()
        fallback.ok, fallback.status = True, 200
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

    async def test_page_response_matches_only_endpoint_gets(self):
        manager, _, _, _, _, page = self.fixture()
        url = transport.ENDPOINTS["Jyske"][0]
        with patch.object(transport, "async_playwright", return_value=manager):
            await transport.request_json(self.session, "Jyske", url)
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
                    self.assertEqual(await transport.request_json(self.session, "Jyske", "url"), {})
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
            self.assertEqual(await transport.request_json(self.session, "Jyske", "url"), {})
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
        self.assertIn("institute=Jyske url=url path=direct status=403", logs.output[0])
        self.assertTrue(any(
            "path=in_page status=None error=AbortError: body timed out" in entry
            for entry in logs.output
        ))
        self.assertIn("path=context_request status=200", logs.output[-1])
        self.assertTrue(all(
            "elapsed_ms=" in entry for entry in logs.output if "fetch_path" in entry
        ))

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

    async def test_blocked_fallback_preserves_statuses_without_retry(self):
        manager, _, request, _, context, page = self.fixture(in_page=False)
        page.evaluate.side_effect = [None, {"ok": False, "status": 400}]
        context.request.get.return_value.ok = False
        context.request.get.return_value.status = 403
        with patch.object(transport, "async_playwright", return_value=manager):
            results = {}
            await transport.retry(self.session, "Jyske", "url", results)
        self.assertIsInstance(results["url"], transport.FetchError)
        self.assertIn("Jyske HTTP 403; in-page status=400", str(results["url"]))
        request.get.assert_called_once()

    async def test_failed_context_cleanup_still_closes_browser(self):
        manager, _, _, browser, context, _ = self.fixture()
        context.close.side_effect = RuntimeError("closed")
        with (
            patch.object(transport, "async_playwright", return_value=manager),
            self.assertLogs(level="INFO"),
        ):
            await transport.request_json(self.session, "Jyske", "url")
        browser.close.assert_awaited_once()

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
