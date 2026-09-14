# Master-data migration 001

The old worker replaces both master tables on each update. That drops constraints,
changes column types through pandas inference, and restores previously removed
product variants. Stop the old worker before applying this migration, deploy the
new scraper code, then resume the worker. Database constraints alone cannot protect
against the old worker's DROP/CREATE under the table owner's credentials.

The new writer inserts new product keys with `ON CONFLICT DO NOTHING`; existing
manual corrections survive. Disagreements are warnings for manual review. Nordea
15/20-year variants remain separate filterable products. Jyske variants
with the same coupon and loan term collapse to maximum interest-only years.
Unexpected identity/coupon conflicts are logged and not added as new master rows.
A partial first observation can still need manual correction; uniqueness prevents
additional rows, not incorrect source data. We do not guess bond terms from ISINs.

Migration 001 keeps the eight reviewed Jyske variants and all Nordea loan terms, removes exact copies, makes floating
periods numeric, and adds a unique (ISIN, loan term, maximum IO) key plus a Jyske-only unique ISIN index. It aborts on missing/changed reviewed rows,
unreviewed conflicting Jyske ISINs, or non-integral floating periods. It preserves the
tables and unrelated rows. Prices and rates are not modified. `years_to_maturity`
retains its existing meaning as a loan-product term, not a computed bond maturity.

## Check and apply

From the repo root, with Python dependencies installed and credentials configured:

```bash
python -m migrations.master_data
```

This only reads the database and writes a local backup/report under `.local/`.
After stopping the old worker and preparing deployment of the updated scraper:

```bash
python -m migrations.master_data --apply
```

The apply command takes a new backup inside the transaction while both tables are
locked, runs the SQL atomically, and records a migration marker. Re-running it after
success is a no-op. If validation fails, all database changes are rolled back.
Deploy the new code before resuming scraping. Test commands:

```bash
TEST_POSTGRES_URL=postgresql://test:test@127.0.0.1:5432/test python -m unittest discover -s test
npm --prefix dashboard run test -w dmbs-backend
```

The PostgreSQL migration tests use PGlite and an isolated fixture. Python writer
regression tests use an isolated PostgreSQL schema with the production column types and keys.
Neither test suite uses real database credentials.
