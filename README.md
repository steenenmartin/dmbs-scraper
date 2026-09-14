# DMBS Scraper

DMBS (Danish Mortgage Backed Securities) Scraper is a web-scraper and an application to extract and display price data for all currently active DMBS ISINs. 

* `scraper.py` collects data periodically every 5 minutes from the 4 main mortgage institutes in Denmark - Nordea Kredit, TotalKredit, Realkredit Danmark and Jyske Realkredit. DLR kredit unfortunately does not display intra-day offer prices, and as such they are not included.
* `dashboard/` contains the TypeScript API and browser dashboard.

## Reporting issues
Use the Github [issue tracker](https://github.com/steenenmartin/dmbs-scraper/issues) to file issues. Pull requests are very welcome

## Run the dashboard locally

Use Node.js 24 and npm 11. Python dependencies are only needed for the scraper.

```bash
npm --prefix dashboard ci --include=dev
```

Configure PostgreSQL using either:

- `DATABASE_URL` in the environment or the root `.env.dashboard.local` file; or
- `src/credit_institute_scraper/database/credentials.json` with your local connection settings.

The credentials file is ignored by Git and is shared with the Python scraper.
`DATABASE_URL` takes precedence. For a hosted database that requires TLS, set
`DATABASE_SSL=require` or `"ssl": "require"` in the JSON file. This encrypts the
connection without verifying the server certificate. Use `disable` for a local
PostgreSQL server without TLS. Without an override, URL/driver SSL settings apply.

```bash
npm run dev
```

Open http://127.0.0.1:5173. Vite proxies `/api` to the backend at
http://127.0.0.1:3001. Set `PORT` in `.env.dashboard.local` to change the backend
port; restart both processes after configuration changes. `/api/health` reports
whether the PostgreSQL connection works.

Build, test, and serve the built application:

```bash
npm test
npm run build
npm start
```

`npm test` uses an isolated in-memory PostgreSQL engine and does not connect to
the configured database. `npm start` serves both API and frontend on port 3001.
The optional Python command wrappers (`pip install -e .`, then `dmbs-backend` and
`dmbs-frontend`) remain available.

## Master-data ingestion

Scraping inserts new fixed master products by ISIN, loan term and maximum
interest-only period, while Jyske has one canonical row per ISIN. Nordea
15/20-year variants remain independently filterable. Floating products are keyed
by institute, fixed rate period and maximum interest-only period. Existing master
records are preserved; differences are logged for review. The writer requires the
three unique indexes from [migration 001](migrations/README.md). Databases with these
indexes already in place need no new migration for the scraper refactor. For an
older database, follow the migration's check, backup and worker shutdown procedure.

## Scraper reliability

See [scraper operation and debugging](docs/scraper-safety.md) for validation,
transactional writes, duplicate protection, quality logs, tests and deployment order.
Four Python modules handle scheduling, source parsing, bounded network access,
and PostgreSQL writes. Each institute fetches both prices and daily rates, then
commits its own data, status and audit. Only the opening collection is delayed to
09:02; subsequent jobs run at five-minute boundaries through 17:00 in Danish time.
Worker dependencies are pinned in `requirements-scraper.txt` and included by
`requirements.txt`. The worker requires PostgreSQL; SQLite and the legacy Python
dashboard are no longer supported.

To debug parsing of a saved endpoint response without network or database access:

```bash
python scraper.py --inspect response.json --institute Nordea --kind fixed
```

The command prints products and validation issues. It only inspects saved JSON;
missed historical quotes cannot be retrieved by running a new scrape.

## Deploying on Heroku (single app: TypeScript dashboard + Python scraper)
This repository runs as **one Heroku app**:
- `web` dyno: Node/TypeScript dashboard server (serves API + built frontend)
- `worker` dyno: Python scraper that uploads to the same PostgreSQL database

The `Aptfile` targets **Heroku-26 / Ubuntu 26.04** and the pinned Playwright
Firefox runtime. `.python-version` selects the latest supported Python 3.12 patch.
The Python buildpack must precede the browser buildpack; Node.js runs last to
build and serve the dashboard. `app.json` declares the same stack and order for
new apps. Existing apps keep their own settings; inspect those with `heroku stack`
and `heroku buildpacks` before changing them.

### Required buildpacks (in this order)
```bash
heroku buildpacks:clear -a <your-app>
heroku buildpacks:add heroku-community/apt -a <your-app>
heroku buildpacks:add heroku/python -a <your-app>
heroku buildpacks:add https://github.com/Thomas-Boi/heroku-playwright-python-browsers -a <your-app>
heroku buildpacks:add heroku/nodejs -a <your-app>
```

### Required config vars
```bash
heroku config:set DATABASE_URL=<your-postgres-url> -a <your-app>
```

### Deploy and run
```bash
git push heroku main
heroku ps:scale web=1 worker=1 -a <your-app>
heroku logs --tail -a <your-app>
```

Notes:
- `Procfile` defines `web: node dashboard/backend/dist/index.js` and `worker: python -u scraper.py`.
- Root `package.json` includes `heroku-postbuild` that installs/builds the dashboard workspace during slug compilation.
- Keep both dynos enabled in production so scraping continues while the dashboard is served.

### Troubleshooting

Inspect the release, buildpacks and logs for the deployed app:

```bash
heroku releases -a <your-app>
heroku buildpacks -a <your-app>
heroku logs --tail -a <your-app>
```

The build must install dashboard dev dependencies (`npm ci --include=dev`) and
complete both TypeScript builds. For scraper errors, follow the stage and source
context described in [scraper operation and debugging](docs/scraper-safety.md).
