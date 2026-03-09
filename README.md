# DMBS Scraper

DMBS (Danish Mortgage Backed Securities) Scraper is a web-scraper and an application to extract and display price data for all currently active DMBS ISINs. 

* `scraper.py` collects data periodically every 5 minutes from the 4 main mortgage institutes in Denmark - Nordea Kredit, TotalKredit, Realkredit Danmark and Jyske Realkredit. DLR kredit unfortunately does not display intra-day offer prices, and as such they are not included.
* `app.py` is a dash application enabling the data to be displayed in your browser

## Reporting issues
Use the Github [issue tracker](https://github.com/steenenmartin/dmbs-scraper/issues) to file issues. Pull requests are very welcome

## Running DMBS scraper locally
To set up the repository locally, clone the repository and create a virtual environment with the packages specified in `requirements.txt`. The repository should work with both python 3.9 and 3.10.

Unfortunately, we cannot grant unrestricted access to the underlying PostgreSQL we use to store the data, but you can change the functions in the repository to use a local SQLite database with a few modifications:
Change the line `from ...database.postgres_conn import query_db` to `from ...database.sqlite_conn import query_db` in the following files
* `src/credit_institute_scraper_database/dashapp/callbacks/main_app.py`
* `src/credit_institute_scraper_database/dashapp/callbacks/ohlc_page.py`
* `src/credit_institute_scraper_database/dashapp/pages/ohlc_plots.py`

To run the server locally, execute `src/credit_institute_scraper/dashapp/local_server.py`

To run the scraper locally, execute `src/credit_institute_scraper/local_scraper.py`




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
