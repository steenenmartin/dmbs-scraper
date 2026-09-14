# Scraper ingestion and recovery

The worker fetches provider data before opening a write transaction. Source
adapters parse individual products; shared validation rejects malformed metadata,
zero/non-finite floating rates and invalid prices. A bad product does not discard
valid siblings. Fixed products without a price can still contribute master data.
Negative floating rates and zero-coupon fixed bonds remain valid.

## Failure handling

- HTTP requests verify TLS, reject unsuccessful HTTP statuses, and have connection
  and read timeouts. Jyske retains its browser transport with bounded timeouts.
- Each provider has at most three attempts, with 1- and 2-second retry delays.
  Empty/all-invalid responses count as failure. A failed source does not prevent
  successful sources from being collected. Reusing a scraper resets its state.
- A run's master data, prices, rates, status and quality audit commit in one
  transaction. A database error rolls them all back. The failure is logged and
  re-raised; a separate transaction attempts to persist its audit record.
- All framework writers share a PostgreSQL transaction advisory lock. Writes have
  a 5-second lock timeout and 30-second statement timeout. This serializes
  overlapping write transactions without holding a lock during HTTP requests.
- `status.last_data_time` only advances when the source has usable spot prices.
  Failed or partial responses are visible as `NotOK` / `SomeDataMissing`.

## Data integrity

Master records use migration 001's database keys and insert-only ingestion.
Known ISINs cannot acquire a different issuer or coupon through a new product
variant. Jyske's rule chooses the greatest observed interest-only period when
otherwise matching observations conflict, and logs that decision. Nordea's
legitimate 15/20-year product variants remain separate. Quotes whose issuer/ISIN/
coupon identity was rejected from master data are not ingested as orphan prices.

Observation keys are `(timestamp, isin)` for fixed prices/OHLC and
`(timestamp, institute, fixed_rate_period, max_interest_only_period)` for rates.
Identical duplicates collapse. Conflicting observations in one response are
rejected and logged. Existing observations are retained on replay; incoming
changes are logged, not silently overwritten. Missing/zero/non-finite prices,
zero/non-finite floating rates and inconsistent OHLC bounds are rejected.
Tables must already exist: ingestion never creates or replaces them.

OHLC uses sorted, valid observations, including the current closing snapshot.
The open and close are the first and last valid prices of the day. Historical
OHLC values are not automatically recalculated or overwritten by this change.

## Schedule and daily recovery

The scheduler uses `Europe/Copenhagen`, including DST. On working days, only the
opening collection is delayed to 09:02; subsequent collections run every five
minutes from 09:05 through 17:00. Intraday
observations are assigned to the preceding five-minute slot (09:02 -> 09:00),
so retries within that slot do not create extra samples. This retains the
application's existing 09:00-17:00 collection window.

Holiday rules include weekends, fixed closures and Easter-relative closures,
checked against the [Nasdaq Copenhagen fixed-income calendars for 2026 and
2027](https://www.nasdaq.com/european-market-activity/trading-hours).
Review these rules when exchange calendars change.

The first valid daily offer quote is retained. Floating sources are retried
throughout the day while known products are missing, instead of only being
attempted at exactly 09:00. If a provider permanently removes a product, its old
master row can therefore cause repeated attempts; the audit makes this visible.
A provider's first valid daily response discovers new floating products. The
framework cannot detect an unknown product omitted from that response.

## Auditing

Warnings are written to the worker log and to the existing `scrape_logs` table as
JSON with `event="scrape_quality"`, `warning_count` and `messages`. A bounded
summary retains the first 100 messages (up to 2,000 characters each) per cycle.
Failure records use `event="scrape_failed"`. If the database is unavailable,
the worker log remains the fallback. Existing older text log rows are preserved.
No external notifications are configured.

A plausible but wrong value for a new product can still pass validation. The
framework does not independently check issuer terms or source publication dates.
Observation replay protection applies to cooperating framework writers; external
writers are not covered by its advisory lock. Master uniqueness is additionally
enforced by database constraints. The old deployed worker must be stopped before
migration, because its table replacement bypasses all these protections.

## Verification

Install the pinned worker dependencies and run the isolated tests:

```sh
python -m pip install -r requirements-scraper.txt
PYTHONPATH=src python -m unittest discover -s test
```

The ordinary tests use temporary SQLite databases and recorded/synthetic source
responses. PostgreSQL integration tests are enabled only with an explicit
loopback `TEST_POSTGRES_URL`; they create and remove a randomly named test schema.
They never use the application's credentials file or `DATABASE_URL`.

```sh
TEST_POSTGRES_URL=postgresql://test:test@127.0.0.1:5432/test \
  PYTHONPATH=src python -m unittest test.test_postgres_ingestion
```

The GitHub Actions workflow runs both test groups against a disposable PostgreSQL
17 service. It covers transactional rollback, replay, missing migration keys,
parser isolation, retries, zero rates, preserved corrections, OHLC and scheduling.
Update dependencies deliberately by editing `requirements-scraper.in`, running
`uv pip compile requirements-scraper.in -o requirements-scraper.txt`, and rerunning
these checks. Browser installation must match the pinned Playwright release.

## Deployment

1. Stop the old worker and let any running scrape finish.
2. Follow [migration 001](../migrations/README.md), including its backup and review.
3. Deploy the new worker code. In this project a push to `main` triggers Heroku.
4. Resume the worker and inspect status plus `scrape_logs` after the first run.

This refactor does not itself apply production migrations or deploy the worker.
Do not resume the old worker after migration: it can drop the new constraints.
