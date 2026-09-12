# DMBS Scraper

DMBS (Danish Mortgage Backed Securities) Scraper is a web-scraper and an application to extract and display price data for all currently active DMBS ISINs. 

* `scraper.py` collects data periodically every 5 minutes from the 4 main mortgage institutes in Denmark - Nordea Kredit, TotalKredit, Realkredit Danmark and Jyske Realkredit. DLR kredit unfortunately does not display intra-day offer prices, and as such they are not included.
* `app.py` is a dash application enabling the data to be displayed in your browser

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
whether the database connection works. The bundled `database.db` is an old SQLite
archive and is not used by this dashboard.

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
records are preserved; differences are logged for review. Before deploying this
writer against an old database, follow [migration 001](migrations/README.md): stop
the old worker, back up and migrate the tables, deploy the new code, then resume.
The old worker's `to_sql(if_exists="replace")` would otherwise remove the keys.

## Scraper reliability

See [scraper ingestion and recovery](docs/scraper-safety.md) for validation,
transactional writes, replay protection, quality logs, tests and deployment order.
Worker dependencies are pinned in `requirements-scraper.txt`; `requirements.txt`
includes them alongside the legacy Python dashboard dependencies.

## Deploying on Heroku (single app: TypeScript dashboard + Python scraper)
This repository runs as **one Heroku app**:
- `web` dyno: Node/TypeScript dashboard server (serves API + built frontend)
- `worker` dyno: Python scraper that uploads to the same PostgreSQL database

### Required buildpacks (in this order)
```bash
heroku buildpacks:clear -a <your-app>
heroku buildpacks:add heroku-community/apt -a <your-app>
heroku buildpacks:add heroku/nodejs -a <your-app>
heroku buildpacks:add heroku/python -a <your-app>
heroku buildpacks:add https://github.com/Thomas-Boi/heroku-playwright-python-browsers -a <your-app>
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


### Troubleshooting: `node: command not found` on `web`
If logs show Python buildpack output and then `/bin/bash: node: command not found`, the Node runtime is not present in the slug.

Run the following exactly (single-app setup):
```bash
heroku buildpacks:clear -a <your-app>
heroku buildpacks:add heroku-community/apt -a <your-app>
heroku buildpacks:add heroku/nodejs -a <your-app>
heroku buildpacks:add heroku/python -a <your-app>
heroku buildpacks:add https://github.com/Thomas-Boi/heroku-playwright-python-browsers -a <your-app>
heroku buildpacks -a <your-app>
```

Then clear cache and force a fresh rebuild:
```bash
heroku repo:purge_cache -a <your-app>
git commit --allow-empty -m "force heroku rebuild"
git push heroku main
```

Finally verify dynos:
```bash
heroku ps:scale web=1 worker=1 -a <your-app>
heroku logs --tail -a <your-app>
```


### Troubleshooting: `tsc: not found` during `heroku-postbuild`
If Heroku logs show `sh: 1: tsc: not found`, your workspace dev dependencies (including TypeScript) were not installed.

Use `npm ci --include=dev` in postbuild (already configured in root `package.json`), then redeploy:
```bash
heroku repo:purge_cache -a <your-app>
git commit --allow-empty -m "force heroku rebuild after include=dev"
git push heroku main
```


### Troubleshooting: `TS1470 import.meta` during Heroku build
If Heroku still shows:
`src/index.ts(...): error TS1470: The 'import.meta' meta-property is not allowed in files which will build into CommonJS output`,
you are likely deploying an older commit (or cached slug) that still had `import.meta` in `dashboard/backend/src/index.ts`.

Verify locally before push:
```bash
rg -n "import.meta" dashboard/backend/src || echo "no import.meta in backend"
```

Then force Heroku to rebuild the latest commit:
```bash
heroku repo:purge_cache -a <your-app>
git push heroku main
heroku releases -a <your-app>
```
