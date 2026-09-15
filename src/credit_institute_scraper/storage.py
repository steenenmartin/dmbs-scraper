"""PostgreSQL writes: preserve history and commit one institute at a time."""

import json
import logging
import os
import re
import traceback
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TypedDict

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Connection, Engine, RowMapping

from .sources import Bond, Issue, Rate, number

MASTER = {
    "master_data": (
        "isin",
        "institute",
        "years_to_maturity",
        "max_interest_only_period",
        "coupon_rate",
    ),
    "master_data_float": ("institute", "fixed_rate_period", "max_interest_only_period"),
}
VALUES = {
    "spot_prices": ("spot_price",),
    "offer_prices": ("offer_price",),
    "closing_prices": ("spot_price",),
    "rates": ("spot_rate",),
    "ohlc_prices": ("open_price", "high_price", "low_price", "close_price"),
}
RATE_KEY = ("timestamp", "institute", "fixed_rate_period", "max_interest_only_period")
type RowKey = tuple[Any, ...]
type ObservationRows = dict[RowKey, dict[str, Any]]


class SaveResult(TypedDict):
    inserted: dict[str, int]
    issues: int
    committed_at: str


def open_engine() -> Engine:
    url = next(
        (
            os.environ[k]
            for k in (
                "DATABASE_URL",
                "HEROKU_POSTGRESQL_BRONZE_URL",
                "HEROKU_POSTGRESQL_COBALT_URL",
                "HEROKU_POSTGRESQL_CRIMSON_URL",
            )
            if os.environ.get(k)
        ),
        None,
    )
    if url:
        url = url.replace("postgres://", "postgresql://", 1)
    else:
        credentials = json.loads((Path(__file__).parent / "database/credentials.json").read_text())
        ssl = os.environ.get("DATABASE_SSL", credentials.get("ssl"))
        url = URL.create(
            "postgresql",
            username=credentials["user"],
            password=credentials["password"],
            host=credentials["host"],
            port=int(credentials["port"]),
            database=credentials["database"],
            query={"sslmode": ssl} if ssl else {},
        )
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=4,
        max_overflow=0,
        pool_timeout=10,
        connect_args={"connect_timeout": 10, "options": "-c statement_timeout=30000"},
    )


def read(
    connection: Connection, sql: str, params: Mapping[str, Any] | None = None
) -> list[RowMapping]:
    return list(connection.execute(text(sql), params or {}).mappings())


def normalize_master(
    records: Iterable[Mapping[str, Any]], table: str, issues: list[Issue]
) -> list[dict[str, Any]]:
    groups = defaultdict(list)
    for raw in records:
        try:
            row = {k: raw[k] for k in MASTER[table]}
            if not isinstance(row["institute"], str) or not row["institute"].strip():
                raise ValueError("Missing institute")
            row["institute"] = row["institute"].strip()
            row["max_interest_only_period"] = number(row["max_interest_only_period"], integer=True)
            period = "years_to_maturity" if table == "master_data" else "fixed_rate_period"
            row[period] = number(row[period], integer=True)
            if row[period] == 0:
                raise ValueError("Missing product period")
            if table == "master_data":
                if not isinstance(row["isin"], str) or not re.fullmatch(
                    r"[A-Z]{2}[A-Z0-9]{9}[0-9]", row["isin"]
                ):
                    raise ValueError("Invalid ISIN")
                row["coupon_rate"] = number(row["coupon_rate"])
            groups[row.get("isin", tuple(row.values()))].append(row)
        except (KeyError, ValueError, TypeError, OverflowError) as error:
            issues.append(Issue("master", f"{error}; row={dict(raw)!r}", raw.get("isin")))
    result = []
    for key, rows in groups.items():
        rows = list({tuple(r.values()): r for r in rows}.values())
        if table == "master_data" and len(rows) > 1:
            if len({(r["institute"], r["coupon_rate"]) for r in rows}) != 1:
                issues.append(
                    Issue(
                        "master",
                        "Conflicting security identities; manual review required",
                        key,
                    )
                )
                continue
            if rows[0]["institute"] == "Jyske":
                if len({r["years_to_maturity"] for r in rows}) != 1 or not {
                    r["max_interest_only_period"] for r in rows
                } <= {0, 10, 30}:
                    issues.append(
                        Issue(
                            "master",
                            "Conflicting Jyske products; manual review required",
                            key,
                        )
                    )
                    continue
                rows = [max(rows, key=lambda r: r["max_interest_only_period"])]
                issues.append(
                    Issue(
                        "master",
                        "Conflicting Jyske interest-only periods; retained observed maximum",
                        key,
                    )
                )
        result.extend(rows)
    return result


def insert_master(
    connection: Connection,
    products: Sequence[Bond | Rate],
    institute: str,
    issues: list[Issue],
) -> dict[str, set[tuple[str, float]]]:
    required = {
        "master_data_product_key",
        "master_data_jyske_isin_key",
        "master_data_float_product_key",
    }
    found = read(
        connection,
        "SELECT indexname FROM pg_indexes WHERE schemaname=current_schema() AND tablename IN ('master_data','master_data_float')",
    )
    if not required <= {r["indexname"] for r in found}:
        raise RuntimeError("Master-data migration 001 is missing")
    identities = defaultdict(set)
    for table, columns in MASTER.items():
        incoming = normalize_master(
            [asdict(p) for p in products if isinstance(p, Bond) == (table == "master_data")],
            table,
            issues,
        )
        scope = "isin = ANY(:ids)" if table == "master_data" else "institute = :institute"
        ids = [p.isin for p in products if isinstance(p, Bond)]
        stored = read(
            connection,
            f"SELECT {', '.join(columns)} FROM {table} WHERE {scope}",
            {"ids": ids, "institute": institute},
        )
        if table == "master_data":
            for row in stored:
                identities[row["isin"]].add((row["institute"], row["coupon_rate"]))
        existing = normalize_master(stored, table, issues)
        for row in incoming:
            key = (
                ("isin",)
                if row["institute"] == "Jyske" and table == "master_data"
                else (
                    ("isin", "years_to_maturity", "max_interest_only_period")
                    if table == "master_data"
                    else columns
                )
            )
            if (
                table == "master_data"
                and identities[row["isin"]]
                and identities[row["isin"]] != {(row["institute"], row["coupon_rate"])}
            ):
                issues.append(
                    Issue(
                        "master",
                        f"Preserving stored identity {sorted(identities[row['isin']])!r}; "
                        f"incoming={(row['institute'], row['coupon_rate'])!r}; manual review required",
                        row["isin"],
                    )
                )
                continue
            previous = next((r for r in existing if all(r[k] == row[k] for k in key)), None)
            if previous is not None and previous != row:
                issues.append(
                    Issue(
                        "master",
                        f"Preserving corrected master product; stored={dict(previous)!r}; incoming={row!r}",
                        row.get("isin"),
                    )
                )
            conflict = (
                "(isin) WHERE institute = 'Jyske'"
                if key == ("isin",)
                else "(" + ", ".join(key) + ")"
            )
            connection.execute(
                text(
                    f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(':' + c for c in columns)}) ON CONFLICT {conflict} DO NOTHING"
                ),
                row,
            )
            if table == "master_data":
                identities[row["isin"]].add((row["institute"], row["coupon_rate"]))
    return identities


def clean(records: Iterable[Mapping[str, Any]], table: str, issues: list[Issue]) -> ObservationRows:
    keys = RATE_KEY if table == "rates" else ("timestamp", "isin")
    result, conflicts = {}, set()
    for raw in records:
        try:
            row = {k: raw[k] for k in (*keys, *VALUES[table])}
            if not isinstance(row["timestamp"], datetime):
                raise ValueError("Invalid timestamp")
            if row["timestamp"].tzinfo:
                row["timestamp"] = row["timestamp"].astimezone(timezone.utc).replace(tzinfo=None)
            if table == "rates":
                if not isinstance(row["institute"], str) or not row["institute"].strip():
                    raise ValueError("Missing institute")
                for k in keys[2:]:
                    row[k] = number(row[k], integer=True)
                if not row["fixed_rate_period"]:
                    raise ValueError("Missing fixed-rate period")
            elif not isinstance(row["isin"], str) or not re.fullmatch(
                r"[A-Z]{2}[A-Z0-9]{9}[0-9]", row["isin"]
            ):
                raise ValueError("Invalid ISIN")
            for k in VALUES[table]:
                row[k] = number(row[k])
                if row[k] == 0 or (table != "rates" and row[k] < 0):
                    raise ValueError(f"Invalid {k}")
            if table == "ohlc_prices" and not (
                row["low_price"]
                <= min(row["open_price"], row["close_price"])
                <= max(row["open_price"], row["close_price"])
                <= row["high_price"]
            ):
                raise ValueError("Inconsistent OHLC bounds")
            key = tuple(row[k] for k in keys)
            if key in result and result[key] != row:
                conflicts.add(key)
                issues.append(
                    Issue(
                        table,
                        f"Conflicting observations rejected; first={result[key]!r}; next={row!r}",
                        str(key),
                    )
                )
            result[key] = row
        except (KeyError, ValueError, TypeError, OverflowError) as error:
            issues.append(
                Issue(
                    table,
                    f"{error}; row={dict(raw)!r}",
                    raw.get("isin", raw.get("institute")),
                )
            )
    return {k: row for k, row in result.items() if k not in conflicts}


def write(
    connection: Connection,
    table: str,
    incoming: Iterable[Mapping[str, Any]],
    start: datetime,
    end: datetime,
    ids: Sequence[str],
    issues: list[Issue],
) -> tuple[int, ObservationRows]:
    keys = RATE_KEY if table == "rates" else ("timestamp", "isin")
    identity = "institute" if table == "rates" else "isin"
    columns = (*keys, *VALUES[table])
    existing = read(
        connection,
        f"SELECT {', '.join(columns)} FROM {table} WHERE timestamp BETWEEN :start AND :end AND {identity} = ANY(:ids)",
        {"start": start, "end": end, "ids": ids},
    )
    previous = clean(existing, table, issues)
    occupied = set(previous)
    # Reserve even invalid historical keys: never add another row to repair one.
    for row in existing:
        try:
            occupied.add(
                tuple(number(row[k], integer=True) if k in RATE_KEY[2:] else row[k] for k in keys)
            )
        except (ValueError, TypeError, OverflowError):
            continue
    inserts = []
    for key, row in clean(incoming, table, issues).items():
        if key not in occupied:
            inserts.append(row)
            previous[key] = row
        elif previous.get(key) == row or (table in {"rates", "offer_prices"} and key in previous):
            continue
        else:
            issues.append(
                Issue(
                    table,
                    f"Preserving existing observation; stored={previous.get(key)!r}; incoming={row!r}",
                    str(key),
                )
            )
    if inserts:
        connection.execute(
            text(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(':' + c for c in columns)})"
            ),
            inserts,
        )
    return len(inserts), previous


def close_prices(
    connection: Connection,
    institute: str,
    day: datetime,
    slot: datetime,
    issues: list[Issue],
) -> dict[str, int]:
    raw = read(
        connection,
        "SELECT timestamp, isin, spot_price FROM spot_prices p WHERE timestamp >= :day AND timestamp < :end AND EXISTS (SELECT 1 FROM master_data m WHERE m.isin=p.isin AND m.institute=:institute) ORDER BY timestamp",
        {"day": day, "end": day + timedelta(days=1), "institute": institute},
    )
    groups = defaultdict(list)
    for row in sorted(clean(raw, "spot_prices", issues).values(), key=lambda r: r["timestamp"]):
        groups[row["isin"]].append(row)
    candles, closing = [], []
    for isin, rows in groups.items():
        values = [r["spot_price"] for r in rows]
        candles.append(
            dict(
                timestamp=day,
                isin=isin,
                open_price=values[0],
                high_price=max(values),
                low_price=min(values),
                close_price=values[-1],
            )
        )
        closing.extend(r for r in rows if r["timestamp"] == slot)
    return {
        "ohlc_prices": write(connection, "ohlc_prices", candles, day, day, list(groups), issues)[0],
        "closing_prices": write(
            connection, "closing_prices", closing, slot, slot, list(groups), issues
        )[0],
    }


def daily_issues(
    issues: Sequence[Issue],
    *,
    institute: str,
    known_rates: set[tuple[int, int]],
    covered_rates: set[tuple[int, int]],
    covered_offers: set[str],
) -> list[Issue]:
    """Keep problems not covered by valid daily observations, without changing input."""
    missing = known_rates - covered_rates
    complete = bool(covered_rates) and not missing
    remaining = list(issues)
    if institute != "Nordea" and not complete:
        remaining.append(Issue("floating.missing", f"Missing daily rates: {sorted(missing)}"))
    covered_products = {f"F{period}/IO{freedom}" for period, freedom in covered_rates}
    return [
        issue
        for issue in remaining
        if not (issue.code == "floating.fetch" and complete)
        and not (issue.code == "floating.spot_rate" and issue.product in covered_products)
        and not (issue.code == "fixed.offer_price" and issue.product in covered_offers)
    ]


def save(
    engine: Engine,
    *,
    institute: str,
    slot: datetime,
    day: datetime,
    closing: bool,
    products: Sequence[Bond | Rate],
    issues: Sequence[Issue],
) -> SaveResult:
    issues = list(issues)
    with engine.begin() as connection:
        connection.execute(text("SET LOCAL lock_timeout='5s'"))
        connection.execute(text("SET LOCAL statement_timeout='30s'"))
        connection.execute(text("SELECT pg_advisory_xact_lock(163447, 1)"))
        identities = insert_master(connection, products, institute, issues)
        fixed = [
            p
            for p in products
            if isinstance(p, Bond) and identities[p.isin] == {(p.institute, p.coupon_rate)}
        ]
        floating = [p for p in products if isinstance(p, Rate)]
        ids = list({p.isin for p in fixed})
        spots = [
            dict(timestamp=slot, isin=p.isin, spot_price=p.spot_price)
            for p in fixed
            if p.spot_price is not None
        ]
        offers = [
            dict(timestamp=day, isin=p.isin, offer_price=p.offer_price)
            for p in fixed
            if p.offer_price is not None
        ]
        rates = [dict(timestamp=day, **asdict(p)) for p in floating if p.spot_rate is not None]
        count, _ = write(connection, "spot_prices", spots, slot, slot, ids, issues)
        inserted = {"spot_prices": count}
        inserted["offer_prices"], daily_offers = write(
            connection, "offer_prices", offers, day, day, ids, issues
        )
        inserted["rates"], daily_rates = write(
            connection, "rates", rates, day, day, [institute], issues
        )
        known = read(
            connection,
            "SELECT fixed_rate_period, max_interest_only_period FROM master_data_float WHERE institute=:institute",
            {"institute": institute},
        )
        relevant = daily_issues(
            issues,
            institute=institute,
            known_rates={(r["fixed_rate_period"], r["max_interest_only_period"]) for r in known},
            covered_rates={key[2:] for key in daily_rates},
            covered_offers={key[1] for key in daily_offers if key[0] == day},
        )
        for issue in set(issues) - set(relevant):
            logging.info(
                "%s: daily data already covered; %s %s %s",
                institute,
                issue.code,
                issue.product or "",
                issue.message,
            )
        issues = relevant
        if closing:
            inserted.update(close_prices(connection, institute, day, slot, issues))
        issues = list(dict.fromkeys(issues))
        if issues:
            audit = dict(
                event="scrape_quality",
                institute=institute,
                warning_count=len(issues),
                issues=[asdict(i) | {"message": i.message[:2000]} for i in issues[:100]],
                messages=[i.message[:2000] for i in issues[:100]],
            )
            connection.execute(
                text("INSERT INTO scrape_logs (time,error) VALUES (:time,:error)"),
                {"time": slot, "error": json.dumps(audit)},
            )
    committed_at = datetime.now(timezone.utc).isoformat()
    for issue in issues:
        logging.warning("%s: %s %s %s", institute, issue.code, issue.product or "", issue.message)
    return dict(
        inserted=inserted,
        issues=len(issues),
        committed_at=committed_at,
    )


def record_failure(
    engine: Engine,
    institute: str,
    slot: datetime,
    error: Exception,
    *,
    stage: str | None = None,
) -> None:
    try:
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO scrape_logs (time,error) VALUES (:time,:error)"),
                {
                    "time": slot,
                    "error": json.dumps(
                        dict(
                            event="scrape_failed",
                            institute=institute,
                            slot=slot.isoformat(),
                            stage=stage,
                            type=type(error).__name__,
                            error=str(error)[:4000],
                            traceback="".join(traceback.format_exception(error))[-12000:],
                        )
                    ),
                },
            )
    except Exception:
        logging.exception("Could not persist failure audit for %s", institute)
