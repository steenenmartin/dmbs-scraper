"""Four independent jobs: fetch, parse, commit. Importing this module starts nothing."""

import argparse
import asyncio
import json
import logging
import signal
import time
from collections.abc import Sequence
from dataclasses import asdict, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import FrameType
from typing import Any
from zoneinfo import ZoneInfo

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.combining import OrTrigger
from apscheduler.triggers.cron import CronTrigger
from dateutil.easter import easter
from sqlalchemy.engine import Engine

from src.credit_institute_scraper import sources, storage, transport

COPENHAGEN = ZoneInfo("Europe/Copenhagen")


def is_holiday(day: date) -> bool:
    day = day.date() if isinstance(day, datetime) else day
    fixed = {(1, 1), (6, 5), (12, 24), (12, 25), (12, 26), (12, 31)}
    offsets = (-3, -2, 1, 39, 40, 50, *([26] if day.year <= 2023 else []))
    return (
        day.weekday() >= 5
        or (day.month, day.day) in fixed
        or day in {easter(day.year) + timedelta(days=d) for d in offsets}
    )


def run_institute(
    engine: Engine, institute: str, now: datetime | None = None
) -> dict[str, Any] | None:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Scrape time must include a timezone")
    local = now.astimezone(COPENHAGEN)
    if is_holiday(local) or not (9 <= local.hour < 17 or (local.hour == 17 and local.minute < 5)):
        return None
    utc = now.astimezone(timezone.utc)
    slot = utc.replace(tzinfo=None, minute=utc.minute - utc.minute % 5, second=0, microsecond=0)
    day = datetime(local.year, local.month, local.day)
    started = time.monotonic()
    stage = "fetch"
    try:
        payloads = asyncio.run(transport.fetch(institute))
        fetched_at = datetime.now(timezone.utc).isoformat()
        fetched = time.monotonic()
        products, issues = [], []
        for kind, url in zip(("fixed", "floating"), sources.ENDPOINTS[institute]):
            stage = f"parse.{kind} url={url}"
            payload = payloads[url]
            if isinstance(payload, Exception):
                issues.append(
                    sources.Issue(kind + ".fetch", f"url={url} {type(payload).__name__}: {payload}")
                )
            else:
                entries, errors = sources.parse(institute, kind, payload)
                products.extend(entries)
                issues.extend(replace(i, message=f"url={url} {i.message}") for i in errors)
        parsed = time.monotonic()
        stage = "database"
        result: dict[str, Any] = dict(
            storage.save(
                engine,
                institute=institute,
                slot=slot,
                day=day,
                closing=local.hour == 17,
                products=products,
                issues=issues,
            )
        )
        result.update(
            event="institute_committed",
            institute=institute,
            slot=slot.isoformat(),
            started_at=utc.isoformat(),
            fetched_at=fetched_at,
            fetch_seconds=round(fetched - started, 3),
            parse_seconds=round(parsed - fetched, 3),
            database_seconds=round(time.monotonic() - parsed, 3),
            total_seconds=round(time.monotonic() - started, 3),
        )
        logging.info("%s", json.dumps(result))
        return result
    except Exception as error:
        logging.exception("Institute job failed: %s slot=%s stage=%s", institute, slot, stage)
        storage.record_failure(engine, institute, slot, error, stage=stage)
        raise


def market_trigger() -> OrTrigger:
    return OrTrigger(
        [
            CronTrigger(day_of_week="mon-fri", hour=9, minute="2,5-55/5", timezone=COPENHAGEN),
            CronTrigger(day_of_week="mon-fri", hour="10-16", minute="*/5", timezone=COPENHAGEN),
            CronTrigger(day_of_week="mon-fri", hour=17, minute=0, timezone=COPENHAGEN),
        ]
    )


def create_scheduler(engine: Engine) -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone=COPENHAGEN, executors={"default": ThreadPoolExecutor(4)})
    for institute in sources.ENDPOINTS:
        scheduler.add_job(
            run_institute,
            market_trigger(),
            args=[engine, institute],
            id=institute,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60,
        )
    return scheduler


def stop_worker(signum: int, frame: FrameType | None) -> None:
    raise SystemExit(0)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inspect",
        type=Path,
        metavar="JSON",
        help="Parse a saved endpoint response offline; never fetch or write data",
    )
    parser.add_argument("--institute", choices=sources.ENDPOINTS)
    parser.add_argument("--kind", choices=("fixed", "floating"))
    args = parser.parse_args(argv)
    if args.inspect:
        if not args.institute or not args.kind:
            parser.error("--inspect requires --institute and --kind")
        if args.institute == "Nordea" and args.kind == "floating":
            parser.error("Nordea has no floating endpoint")
        try:
            payload = json.loads(args.inspect.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, ValueError) as error:
            parser.error(str(error))
        products, issues = sources.parse(args.institute, args.kind, payload)
        print(
            json.dumps(
                dict(
                    institute=args.institute,
                    kind=args.kind,
                    input=str(args.inspect),
                    products=[asdict(p) for p in products],
                    issues=[asdict(i) for i in issues],
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return int(bool(issues))
    if args.institute or args.kind:
        parser.error("--institute and --kind require --inspect")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    engine = storage.open_engine()
    scheduler = create_scheduler(engine)
    signal.signal(signal.SIGTERM, stop_worker)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=True)
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
