# Scraper operation and data guarantees

The worker has four non-empty Python modules: the root `scraper.py` entrypoint,
and `sources.py`, `transport.py`, `storage.py` under `src/credit_institute_scraper`.
They handle scheduling, pure field translation, bounded network access and
PostgreSQL persistence. There are no adapter, repository or result-handler layers.
The TypeScript dashboard is a separate process. Legacy Python/Dash, SQLite and old
internal Python interfaces are removed. The database schema remains unchanged.

## One flow per institute

On Danish business days, APScheduler runs four independent jobs at 09:02, then
09:05, 09:10 and every five minutes through 17:00. Each institute has one combined
trigger, `max_instances=1`, coalescing and a 60-second misfire grace period. A slow
source can skip its next run without holding up another source's fetch.
`market-calendar.json` is the shared definition of the collection window, schedule,
timezone, weekends and fixed/Easter-relative holidays. Python and TypeScript use
the same rules, with cross-language calendar and schedule tests. The browser uses
the API's calendar result rather than maintaining a third calendar.

Each job fixes its UTC five-minute slot when it starts (09:02 maps to 09:00),
fetches both prices and floating rates, parses them, then opens a write transaction.
Requests only retrieve the data available at request time. Missed historical quotes
cannot be fetched later; neither scheduling nor the inspection command backfills them.
Jyske's shared endpoint is fetched once per job. Re-fetching daily rates makes
recovery and discovery of new products automatic; only the first valid daily rate
and offer price are stored for each product. RD and Totalkredit each make one
additional endpoint request every five minutes compared with the previous pipeline.

HTTP uses aiohttp with a 20-second total request timeout and 5-second connection
timeout. The entire network phase shares a 90-second budget including retries and
Jyske's browser fallback. Only transient connection failures, timeouts and HTTP
408/429/500/502/503/504 are retried, at most three attempts with 1- and 2-second
delays. Certificate and malformed JSON errors are reported without retrying.
Unexpected programming errors propagate with their traceback and fail the job;
they are not converted into ordinary quality issues or retried.
Successful endpoints survive another endpoint's timeout. Browser resources have
bounded cleanup; the 90-second network budget can be followed by that cleanup.

Jyske retains direct APIRequestContext, in-page fetch and context-request fallback.
There is no network-idle wait. The in-page request aborts after 30 seconds including
body reading. Cancellation unwinds owned browser contexts. Successful retries and
fallbacks do not create quality warnings. Pure parsers do not fetch, log or write.

## Validation and persistence

- Numeric validation precedes conversion: boolean prices are invalid; fractional
  product periods are rejected rather than truncated. Missing, non-positive or
  non-finite fixed prices become `None` without discarding valid master data or
  another valid price. Floating rates must be finite and nonzero; negative rates
  and zero fixed coupons are valid. A missing floating rate also retains its valid
  master identity, so a newly discovered product cannot disappear from coverage.
  Expected invalid input becomes a contextual issue without discarding valid siblings.
  RD's explicit `-1` quote sentinel means unavailable and does not create a parser
  warning. A previously quoted bond still leaves a coverage gap when its quote disappears.
  Parsers catch only explicit source-validation errors; programming errors propagate.
- Existing master products and manual corrections are insert-only. Security issuer
  and coupon conflicts are rejected across product keys. Jyske retains the greatest
  observed interest-only period for otherwise matching variants. Nordea 15/20-year
  variants remain independently filterable. Existing migration 001 keys are required.
- Master data, observations and quality audit commit together per institute.
  A database error rolls back that institute and attempts a separate failure audit.
  One pooled SQLAlchemy engine lives for the worker lifetime. Connections belong to
  individual transactions; jobs never dispose the pool.
- Writers retain the shared PostgreSQL transaction advisory lock, 5-second lock
  timeout and 30-second statement timeout. Network work happens before that lock.
  Database transactions are briefly serialized; external writers bypassing this
  lock are not covered by application-level duplicate-write protection.
- Exact duplicates collapse; conflicting incoming observations are rejected.
  Existing observations, including invalid historical keys, are never overwritten
  or repaired by inserting duplicates. Daily values retain their first valid value.
  Tables are never created, replaced or migrated by the worker.
- Nordea does not provide offer prices. Failed optional daily
  retrieval after today's products are covered is informational.
  A missing rate is harmless only when that exact product already has a valid daily
  rate. Malformed product identities and response formats remain visible even after
  known daily products are covered.
- At close, validated stored spot observations produce OHLC and closing prices.
  A rejected incoming quote cannot become a closing price. OHLC is sorted and
  scoped by institute without multiplying quotes for product variants. Existing
  OHLC/closing history remains unchanged on conflicting duplicate writes.

Known floating products missing from today's rates continue to produce quality diagnostics.
If a provider permanently removes a product, its retained master row needs review.
Unknown products absent from the feed and plausible but incorrect new values cannot
be independently detected by this scraper.

## Spot status

`GET /api/status` computes coverage directly from stored spot observations. The
worker no longer reads or writes the legacy `status` table; existing rows are left
untouched and are not used by the dashboard. No migration is required.

The response contains `trading_date`, `market_open`, `checked_at`, `refresh_at` and
`institutes`. All four institutes are present, each with `status`, nullable
`last_data_time` and a short `detail`. Offers, rates, OHLC and quality-log warnings
do not determine this badge. The route disables HTTP caching.

The institute must have quotes for every elapsed five-minute slot from 09:00.
Individual ISINs are required only from their first valid quote on that trading
day. Unquoted master records do not manufacture missing products. Identical
duplicates count once, conflicting valid quotes do not count, and invalid,
non-finite, future or off-grid observations cannot fill a gap. Product variants
sharing an ISIN do not multiply coverage.

There is a 60-second delivery tolerance, separate from the worker schedule:
09:00 data are first required at 09:03 (the job starts at 09:02); 09:05 data at
09:06; the final 17:00 data at 17:01. Only observations up to the required slot
contribute to coverage; newer observations cannot hide older missing slots.

| Data status | Meaning |
| --- | --- |
| `Waiting` | No quotes yet, and the first delivery deadline has not passed. |
| `OK` | All expected spot observations through the required slot are present. |
| `SomeDataMissing` / Partial | The latest slot has quotes, but the day's history has gaps. |
| `NotOK` / Error | The required latest slot has no valid quotes for this institute. |

Recovery changes `Error` to `Partial` while older gaps remain. A legitimate late
commit of its original slot can fill a gap; a new scrape cannot fetch past data.
The next trading day starts a new coverage history.

At 17:00 the display becomes neutral `Closed` regardless of worker success. Its
tooltip retains that trading day's data status; a missing final scrape becomes
`Error` after 17:01 and stays visible through the evening, weekend or holidays.
Before the next opening the API continues to assess the previous trading day.
The frontend refreshes at calendar/deadline boundaries and at least every minute;
unavailable or expired responses cannot leave a verified green status behind.

## Logs, tests and rollout

Each commit emits an `institute_committed` JSON log with institute, slot, actual
start/fetch/commit times, fetch/parse/database/total durations, inserted counts and
issue count. `scrape_logs` retains `scrape_quality` and `scrape_failed` JSON events;
quality events include typed issues and compatible message strings. Reports retain
at most 100 issues of 2,000 message characters each. Historical log rows stay readable.
Failure events include the slot, stage and a bounded traceback, including underlying
errors from concurrent requests. Retry logs identify institute, endpoint, attempt,
elapsed time and the exception message; Jyske logs also identify the fallback path.
Product validation messages include a product identity where available and the
offending field/value. The worker adds the source endpoint to quality messages.
Display time is separate from database commit.

To locate a failure, follow its stage directly to the responsible module:

| Stage | Module | Responsibility |
| --- | --- | --- |
| Scheduling/job | `scraper.py` | Market times, orchestration and commit/failure logs |
| `fetch` | `transport.py` | HTTP, retry, timeout and browser fallback |
| `parse.fixed` / `parse.floating` | `sources.py` | Source fields, product identity and validation |
| `database` | `storage.py` | Transactions, preserved observations and quality audit |
| Dashboard status | `dashboard/backend/src/routes/status.ts` | Spot-history coverage and current data availability |

Within `storage.py`, `save()` coordinates one transaction. `write()` validates and
preserves observations, and `daily_issues()` filters daily diagnostics already
covered by valid stored data. Quality issues are audited in the same transaction.
Dashboard status is derived separately from the actual spot history, never from
the number of parser warnings.

Inspect a saved raw JSON response from one endpoint without fetching or writing:

```sh
python scraper.py --inspect response.json --institute Nordea --kind fixed
```

This works outside market hours and needs no database credentials. It prints parsed
products and issues as JSON. Exit codes are 0 for no issues, 1 for validation issues
and 2 for invalid arguments or an unreadable/invalid JSON file. Unexpected bugs retain
their traceback. The input is the endpoint's raw response, not the combined fixture
catalogue. Inspection reproduces parsing of a saved response; it cannot recover a
missed historical quote. Running `python scraper.py` without arguments starts the worker.

Install `requirements-scraper.txt`, then from the repository root:

```sh
TEST_POSTGRES_URL=postgresql://test:test@127.0.0.1:5432/test python -m unittest discover -s test
npm test
npm run build
```

Database tests require an explicit loopback URL and use a randomly named disposable
PostgreSQL schema. They never read application credentials or `DATABASE_URL`.
Without `TEST_POSTGRES_URL`, only pure/parser/network/worker unit tests run; database
tests are visibly skipped. CI supplies PostgreSQL 17. Provider fixtures include
recorded public fields and synthetic edge cases; network tests use mocks and a local
HTTP server, and execute the actual in-page JavaScript with a hanging response body.

Tests keep the runtime within four non-empty modules. There is no hard class,
function or line-count ceiling: explicit validation, useful types and diagnostics
take priority over saving lines. The simplified worker keeps the direct four-module
flow without the earlier adapter, repository and compatibility layers. Regression
tests inject real provider/transport programming errors and verify missing-product
coverage, recovery and failure diagnostics against PostgreSQL.

Recompile dependencies deliberately with
`uv pip compile requirements-scraper.in -o requirements-scraper.txt --python-version 3.12`.
The installed browser must match the pinned Playwright version.

This change needs no new database migration. Existing migration 001 is still required;
its [preflight tool](../migrations/README.md) is preserved. Drain the previous worker
before replacement. SIGTERM/keyboard shutdown drains jobs before disposing the pool;
an external hard termination may interrupt that drain and PostgreSQL rolls back any
uncommitted transaction. After an authorized deployment, check per-institute commit
times, status and opening/closing observations. Commit/push/deployment are separate
actions; this refactor does not itself change production data.
