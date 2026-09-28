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
408/429/500/502/503/504 are retried. Other institutes allow at most three attempts
with 1- and 2-second delays. Jyske allows an initial attempt plus up to ten retries,
with five seconds between attempts. The 90-second total budget includes these
pauses and can stop the job before all eleven attempts run. Certificate and malformed JSON errors are
reported without retrying.
Unexpected programming errors propagate with their traceback and fail the job;
they are not converted into ordinary quality issues or retried.
Successful endpoints survive another endpoint's timeout. Browser resources have
bounded cleanup; the 90-second network budget can be followed by that cleanup.

Jyske first uses `curl_cffi` with a Chrome TLS/HTTP profile and matching default
browser headers, without starting Firefox or Playwright's Node process. The request
uses JSON/CORS headers, a ten-second timeout, and at most three redirects. Its HTTP
session closes after the request. Its own cookies are retained separately as an
in-memory JSON snapshot, capped at 256 KiB and expiring after 30 minutes without
an update. Domain, path, Secure, HttpOnly and cookie expiry are preserved; expired
and non-Jyske cookies are excluded. Completed error responses also update the jar,
including server-side cookie deletion. No HTTP client or event-loop objects persist
between jobs. It does not borrow Firefox's cookies or identity.
The HTTP request uses the bank origin as Referer, matching its strict-origin policy,
and requests JSON. Logs show `session_restored=True/False`, never cookie contents.
Other institutes still use aiohttp. This changes the connection fingerprint, not
the outbound IP, and does not guarantee Cloudflare acceptance.
An HTTP failure or connection timeout falls back to Firefox. A certificate error
is reported without browser fallback. Every browser attempt first captures the
price page's own API response, including headers supplied by the site's scripts.
Navigation,
waiting for that response and reading its body share a 20-second limit. If that
fails or returns invalid JSON, in-page fetch and context-request remain as
fallbacks, each with a 10-second request limit. There is no network-idle wait.
The in-page limit includes body reading. Final HTTP failures retain the in-page
status/error for diagnosis; Jyske's 403 retry behavior is described below.
Cancellation unwinds owned browser contexts. Successful retries and fallbacks
do not create quality warnings. Pure parsers do not fetch, log or write.

Expected fetch errors retain their type/message for reporting, but their traceback
frames and exception chains are released after logging so closed request/browser
objects are not kept alive by failed jobs. Unexpected programming errors still
propagate with full tracebacks. Raw endpoint payloads are released after parsing,
before waiting for database connections or locks. Firefox and its Playwright driver
remain scoped to one browser attempt and are closed afterward; they are not kept
running between five-minute jobs.

The Firefox fallback uses its native user agent and platform, with Danish locale
and Copenhagen timezone. It no longer overrides `navigator.webdriver`, platform
or languages. The lightweight HTTP client uses its own consistent Chrome profile.
After a browser fetch returns non-empty fixed or floating products, the worker
may retain that browser's cookies/local storage as serialized Playwright storage
state. This is the scraper's own session, never a user's browser profile. The
snapshot stays in worker memory only, is capped at 256 KiB of ASCII JSON and expires
30 minutes after capture. It is restored on the next first browser attempt; retries
use fresh state, and a failed fetch attempt discards the saved snapshot. Session
contents are never logged, written to disk or copied to the direct HTTP client.
Capturing full state has a one-second limit. If it fails or exceeds the size cap,
the worker spends at most two additional seconds reading cookies scoped to the
bank page and API. This fallback omits local storage and uses the same size/expiry
limits. Logs identify `mode=cookies` without exposing cookie contents. A capture
error does not discard fetched quotes. Browser/context processes still close after every attempt. A dyno restart
loses the snapshot. Session reuse does not guarantee acceptance by Jyske/Cloudflare.

To compare worker memory before and after deployment, inspect `worker.1` separately
from `web.1`, both during Jyske's browser fallback and between scrapes. Heroku's
[runtime metrics](https://devcenter.heroku.com/articles/log-runtime-metrics) report
RSS, disk cache and swap separately; `memory_total` includes all three. Compare
equivalent workloads rather than treating a lower idle reading as a lower browser
peak. These changes do not put a hard cap on Firefox's memory usage.

The browser loads the quote application on the first attempt, and blocks the
embedded `jyskebank.tv` video player on all attempts. Image/media/font/stylesheet
and tracker blocking stays in place. Each retry closes the previous context/browser
and starts a fresh session. In-page logs identify `profile=native`. Failed in-page HTTP responses
include at most 300 characters of their body in a separate `fetch_response` log;
successful payloads and request cookies/headers are not logged.
If the bank page itself returns a Cloudflare challenge (`cf-mitigated: challenge`),
the job reports the navigation status and diagnostic headers and closes Firefox.
It does not inject fetches into the challenge page. A fresh attempt is allowed
after the normal backoff, within the eleven-attempt/90-second limits: an initial
403 must not discard a slot that a subsequent attempt could recover.
Other unsuccessful navigation responses also skip synthetic calls; transient HTTP
statuses remain retryable. This limits wasted work; it does not solve the challenge
or impose a hard cap on Firefox RAM usage.
After successful navigation, Jyske's browser fetch errors, transient statuses and 403 responses remain retryable
even if the final HTTP fallback returns a non-transient status. The final error
retains the in-page failure as well as the fallback status. Browser crashes/closed
targets and an execution context destroyed by navigation are also retried.
The shared 90-second limit still applies; other institutes retain their
three-attempt limit and their 403 responses remain non-retryable.

Jyske path logs include the response content type, `cf-mitigated` and `cf-ray`,
including the initial page navigation. The final fallback error retains those
fields in the database audit; cookies and authorization headers are excluded.
`cf_mitigated=challenge` identifies a Cloudflare challenge rather than an API JSON
response ([Cloudflare documentation](https://developers.cloudflare.com/cloudflare-challenges/challenge-types/challenge-pages/detect-response/)).
A CORS failure may prevent the in-page fetch from reading these headers, so inspect
the context-request and navigation paths too. A fetch-budget timeout now retains
the last completed attempt's type/message as `last_error`, without retaining its
traceback or changing the result into a success. These diagnostics do not resolve
provider-side challenges or establish that every HTTP 400/403 has the same cause.

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
  Nordea's starred prices (including `*&nbsp;100,150`) are previous closing averages,
  [not current quotes](https://www.nordea.dk/privat/produkter/boliglaan/Kurser-realkreditlaan-kredit.html).
  They retain product identity with no spot observation or malformed-value warning.
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
