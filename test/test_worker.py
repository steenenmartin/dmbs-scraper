import asyncio
import importlib
import io
import json
import signal
import tempfile
import threading
import unittest
import weakref
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from apscheduler.events import EVENT_JOB_MAX_INSTANCES
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.exc import IntegrityError

import scraper
from src.credit_institute_scraper import sources, storage
from test.support import ISIN, NORDEA, STAMP, DatabaseCase, payload


class WorkerTests(unittest.TestCase):
    def test_raw_responses_are_released_before_database_work(self):
        class Payload(dict):
            pass

        references = []

        async def fetch(institute):
            raw = Payload(next(iter(payload(institute).values())))
            responses = Payload({sources.ENDPOINTS[institute][0]: raw})
            references.extend((weakref.ref(raw), weakref.ref(responses)))
            return responses

        def save(*args, **kwargs):
            self.assertTrue(all(ref() is None for ref in references))
            self.assertTrue(kwargs["products"])
            return {"inserted": {}, "issues": 0, "committed_at": STAMP.isoformat()}

        with (
            patch.object(scraper.transport, "fetch", fetch),
            patch.object(storage, "save", save),
        ):
            scraper.run_institute(None, "Jyske", STAMP)

    def test_complete_daily_schedule_in_both_dst_seasons(self):
        for month, offset in ((1, 1), (9, 2)):
            now = datetime(2026, month, 14, tzinfo=timezone.utc)
            trigger = scraper.market_trigger()
            previous, slots = None, []
            while True:
                tick = trigger.get_next_fire_time(previous, now)
                if tick.day != 14:
                    break
                slots.append(tick)
                previous, now = tick, tick + timedelta(microseconds=1)
            self.assertEqual(len(slots), 97)
            self.assertEqual(
                (slots[0].hour, slots[0].minute, slots[-1].hour, slots[-1].minute), (9, 2, 17, 0)
            )
            self.assertEqual(slots[0].utcoffset(), timedelta(hours=offset))
            self.assertTrue(all(t.minute % 5 == 0 for t in slots[1:]))

    def test_each_institute_has_one_combined_job(self):
        scheduler = scraper.create_scheduler(None)
        self.assertEqual(len(scheduler.get_jobs()), 4)
        for job in scheduler.get_jobs():
            self.assertEqual(job.max_instances, 1)
            self.assertTrue(job.coalesce)
            self.assertEqual(job.misfire_grace_time, 60)

    def test_closed_market_never_fetches_or_connects(self):
        for stamp in (
            STAMP.replace(day=13),
            STAMP.replace(hour=6),
            STAMP.replace(hour=15, minute=5),
            STAMP.replace(month=12, day=24),
        ):
            with (
                patch.object(scraper.transport, "fetch", AsyncMock()) as fetch,
                patch.object(storage, "save") as save,
            ):
                self.assertIsNone(scraper.run_institute(None, "Jyske", stamp))
                fetch.assert_not_called()
                save.assert_not_called()

    def test_holidays_and_historical_store_bededag(self):
        for day in (
            "2026-01-01",
            "2026-04-02",
            "2026-04-03",
            "2026-04-06",
            "2026-05-14",
            "2026-05-15",
            "2026-05-25",
            "2026-06-05",
            "2026-12-24",
            "2026-12-31",
            "2027-01-01",
            "2023-05-05",
        ):
            self.assertTrue(scraper.is_holiday(datetime.fromisoformat(day)), day)
        self.assertFalse(scraper.is_holiday(datetime(2026, 5, 1)))

    def test_importing_worker_has_no_side_effects(self):
        with patch.object(storage, "open_engine") as open_engine:
            importlib.reload(scraper)
            open_engine.assert_not_called()

    def test_naive_time_is_rejected(self):
        with self.assertRaises(ValueError):
            scraper.run_institute(None, "Jyske", STAMP.replace(tzinfo=None))

    def test_shutdown_drains_scheduler_before_closing_pool(self):
        order = []
        engine, scheduler = MagicMock(), MagicMock()
        scheduler.start.side_effect = SystemExit(0)
        scheduler.shutdown.side_effect = lambda **_: order.append("drain")
        engine.dispose.side_effect = lambda: order.append("dispose")
        with (
            patch.object(storage, "open_engine", return_value=engine),
            patch.object(scraper, "create_scheduler", return_value=scheduler),
            patch.object(scraper.signal, "signal") as handler,
        ):
            scraper.main([])
        self.assertEqual(order, ["drain", "dispose"])
        scheduler.shutdown.assert_called_once_with(wait=True)
        handler.assert_called_once_with(signal.SIGTERM, scraper.stop_worker)

    def test_runtime_remains_four_modules(self):
        root = Path(__file__).resolve().parents[1]
        files = [root / "scraper.py", *(root / "src/credit_institute_scraper").rglob("*.py")]
        code = [
            p.read_text(encoding="utf-8") for p in files if p.read_text(encoding="utf-8").strip()
        ]
        self.assertLessEqual(len(code), 4)

    def test_inspect_saved_response_reports_products_and_issues_without_io(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(storage, "open_engine") as open_engine,
            patch.object(scraper.transport, "fetch", AsyncMock()) as fetch,
        ):
            path = Path(directory) / "nordea.json"
            for changes, expected_code in (({}, 0), ({"fundName": None}, 1)):
                with self.subTest(changes=changes):
                    data = next(iter(payload("Nordea", **changes).values()))
                    path.write_text(json.dumps(data), encoding="utf-8")
                    output = io.StringIO()
                    with redirect_stdout(output):
                        code = scraper.main(
                            ["--inspect", str(path), "--institute", "Nordea", "--kind", "fixed"]
                        )
                    report = json.loads(output.getvalue())
                    self.assertEqual(code, expected_code)
                    self.assertEqual(report["institute"], "Nordea")
                    if expected_code:
                        self.assertEqual(report["issues"][0]["product"], NORDEA)
                        self.assertIn("fundName", report["issues"][0]["message"])
                    else:
                        self.assertEqual(report["products"][0]["isin"], NORDEA)
                        self.assertEqual(report["issues"], [])
            open_engine.assert_not_called()
            fetch.assert_not_called()

    def test_inspect_rejects_incomplete_arguments_and_invalid_json_before_database(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(storage, "open_engine") as open_engine,
            patch.object(scraper.transport, "fetch", AsyncMock()) as fetch,
        ):
            path = Path(directory) / "broken.json"
            path.write_text("{", encoding="utf-8")
            for args in (
                ["--institute", "Jyske"],
                ["--inspect", str(path)],
                ["--inspect", str(path), "--institute", "Nordea", "--kind", "floating"],
                ["--inspect", str(path), "--institute", "Jyske", "--kind", "fixed"],
            ):
                with self.subTest(args=args), redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as stopped:
                        scraper.main(args)
                    self.assertEqual(stopped.exception.code, 2)
            path.write_text("1" * 5000, encoding="utf-8")
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as stopped:
                scraper.main(["--inspect", str(path), "--institute", "Nordea", "--kind", "fixed"])
            self.assertEqual(stopped.exception.code, 2)
            open_engine.assert_not_called()
            fetch.assert_not_called()

    def test_database_url_precedence_and_pool_settings(self):
        with (
            patch.dict(
                "os.environ", {"DATABASE_URL": "postgres://test:fake@localhost/test"}, clear=True
            ),
            patch.object(storage, "create_engine") as factory,
        ):
            storage.open_engine()
        self.assertEqual(factory.call_args.args[0], "postgresql://test:fake@localhost/test")
        self.assertEqual(factory.call_args.kwargs["pool_size"], 4)
        self.assertEqual(factory.call_args.kwargs["max_overflow"], 0)
        self.assertTrue(factory.call_args.kwargs["pool_pre_ping"])


class WorkerIntegrationTests(DatabaseCase):
    def test_fast_institute_commits_while_another_fetch_hangs(self):
        entered, release = threading.Event(), threading.Event()

        async def fetch(institute):
            if institute == "Jyske":
                entered.set()
                if not await asyncio.to_thread(release.wait, 5):
                    raise AssertionError("Test did not release source")
            return payload(institute)

        with patch.object(scraper.transport, "fetch", fetch), ThreadPoolExecutor(2) as pool:
            slow = pool.submit(scraper.run_institute, self.engine, "Jyske", STAMP)
            try:
                self.assertTrue(entered.wait(2))
                fast = pool.submit(scraper.run_institute, self.engine, "Nordea", STAMP)
                self.assertEqual(fast.result(timeout=3)["inserted"]["spot_prices"], 1)
                self.assertFalse(slow.done())
                self.assertEqual([r["isin"] for r in self.rows("spot_prices")], [NORDEA])
            finally:
                release.set()
            self.assertEqual(slow.result(timeout=3)["inserted"]["spot_prices"], 1)

    def test_constraint_failure_does_not_roll_back_another_institute(self):
        self.sql(f"ALTER TABLE spot_prices ADD CONSTRAINT reject_jyske CHECK (isin <> '{ISIN}')")

        async def fetch(institute):
            return payload(institute)

        with (
            patch.object(scraper.transport, "fetch", fetch),
            self.assertLogs(level="ERROR"),
            ThreadPoolExecutor(2) as pool,
        ):
            failed = pool.submit(scraper.run_institute, self.engine, "Jyske", STAMP)
            healthy = pool.submit(scraper.run_institute, self.engine, "Nordea", STAMP)
            self.assertEqual(healthy.result(timeout=3)["inserted"]["spot_prices"], 1)
            with self.assertRaises(IntegrityError):
                failed.result(timeout=3)
        self.assertEqual([r["isin"] for r in self.rows("spot_prices")], [NORDEA])
        self.assertEqual([r["institute"] for r in self.rows("master_data")], ["Nordea"])

    def test_scheduler_skips_overlap_and_waits_for_active_job_at_shutdown(self):
        entered, release, skipped = threading.Event(), threading.Event(), threading.Event()
        calls = []

        async def fetch(institute):
            calls.append(institute)
            entered.set()
            if not await asyncio.to_thread(release.wait, 5):
                raise AssertionError("Test did not release source")
            return payload(institute)

        scheduler = scraper.create_scheduler(self.engine)
        for job in scheduler.get_jobs():
            if job.id != "Jyske":
                scheduler.remove_job(job.id)
        scheduler.modify_job("Jyske", kwargs={"now": STAMP})
        scheduler.reschedule_job("Jyske", trigger=IntervalTrigger(seconds=0.02))
        scheduler.add_listener(lambda event: skipped.set(), EVENT_JOB_MAX_INSTANCES)
        with patch.object(scraper.transport, "fetch", fetch), self.assertLogs(level="WARNING"):
            thread = threading.Thread(target=scheduler.start)
            thread.start()
            try:
                self.assertTrue(entered.wait(2))
                self.assertTrue(skipped.wait(2))
                self.assertEqual(calls, ["Jyske"])
            finally:
                scheduler.pause()
                release.set()
                scheduler.shutdown(wait=True)
                thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual([r["isin"] for r in self.rows("spot_prices")], [ISIN])
        self.assertEqual(self.engine.pool.checkedout(), 0)

    def test_a_parser_bug_is_not_retried_and_is_audited(self):
        with (
            patch.object(scraper.transport, "fetch", AsyncMock(return_value=payload())) as fetch,
            patch.object(sources, "parse", side_effect=RuntimeError("parser bug")) as parser,
            self.assertLogs(level="ERROR"),
            self.assertRaisesRegex(RuntimeError, "parser bug"),
        ):
            scraper.run_institute(self.engine, "Jyske", STAMP)
        fetch.assert_awaited_once()
        parser.assert_called_once()
        self.assertEqual(self.rows("spot_prices"), [])
        self.assertEqual(json.loads(self.rows("scrape_logs")[0]["error"])["type"], "RuntimeError")

    def test_provider_programming_errors_keep_traceback_and_endpoint_in_failure_audit(self):
        for error_type in (TypeError, AttributeError, KeyError, ValueError):
            parser = MagicMock(side_effect=error_type("provider programming bug"))
            with (
                self.subTest(error=error_type.__name__),
                patch.dict(sources.PARSERS, {"Nordea": parser}),
                self.assertLogs(level="ERROR") as logs,
                self.assertRaises(error_type),
            ):
                self.cycle("Nordea")
            parser.assert_called_once()
            self.assertTrue(logs.records[0].exc_info)
            self.assertIn("slot=2026-09-14 07:00:00", logs.output[0])
            audit = json.loads(self.rows("scrape_logs")[-1]["error"])
            self.assertEqual(audit["type"], error_type.__name__)
            self.assertIn("parse.fixed", audit["stage"])
            self.assertIn(sources.ENDPOINTS["Nordea"][0], audit["stage"])
            self.assertIn("provider programming bug", audit["traceback"])
        self.assertEqual(self.rows("master_data"), [])
        self.assertEqual(self.rows("spot_prices"), [])

    def test_transport_programming_error_is_a_failed_job_with_original_traceback(self):
        request = AsyncMock(side_effect=TypeError("request programming bug"))
        with (
            patch.object(scraper.transport, "request_json", request),
            self.assertLogs(level="ERROR") as logs,
            self.assertRaises(ExceptionGroup),
        ):
            scraper.run_institute(self.engine, "Nordea", STAMP)
        request.assert_awaited_once()
        self.assertTrue(logs.records[0].exc_info)
        audit = json.loads(self.rows("scrape_logs")[0]["error"])
        self.assertEqual(audit["stage"], "fetch")
        self.assertIn("TypeError: request programming bug", audit["traceback"])
        self.assertIn(sources.ENDPOINTS["Nordea"][0], audit["traceback"])
        self.assertEqual(self.rows("spot_prices"), [])

    def test_daily_endpoint_failure_does_not_discard_fixed_quotes(self):
        data = payload("RealKreditDanmark")
        fixed_url, floating_url = sources.ENDPOINTS["RealKreditDanmark"]
        data[fixed_url] = data[fixed_url][:1]
        data[floating_url] = TimeoutError("daily endpoint unavailable")
        with self.assertLogs(level="WARNING"):
            first = self.cycle("RealKreditDanmark", data=data)
        self.assertGreater(first["issues"], 0)
        self.assertEqual(first["inserted"]["spot_prices"], 1)
        recovered = payload("RealKreditDanmark")
        recovered[fixed_url] = recovered[fixed_url][:1]
        self.assertEqual(
            self.cycle("RealKreditDanmark", now=STAMP.replace(minute=7), data=recovered)["issues"],
            0,
        )
        self.assertEqual(
            self.cycle("RealKreditDanmark", now=STAMP.replace(minute=12), data=data)["issues"], 0
        )

    def test_logs_distinguish_slot_from_actual_commit(self):
        with self.assertLogs(level="INFO") as logs:
            result = self.cycle()
        summary = next(
            json.loads(line.split(":", 2)[2])
            for line in logs.output
            if "institute_committed" in line
        )
        self.assertEqual(summary["slot"], "2026-09-14T07:00:00")
        self.assertEqual(summary["committed_at"], result["committed_at"])
        self.assertLessEqual(
            datetime.fromisoformat(summary["fetched_at"]),
            datetime.fromisoformat(summary["committed_at"]),
        )
        self.assertEqual(summary["inserted"]["spot_prices"], 1)
