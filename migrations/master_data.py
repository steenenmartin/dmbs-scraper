"""Read-only preflight by default; --apply runs reviewed migration 001 atomically."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from credit_institute_scraper.database import postgres_conn
from credit_institute_scraper.database.master_data import normalize_master_data
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
VERSION = '001_master_data_keys'


def run(apply=False):
    engine = postgres_conn.client_factory()
    try:
        with engine.begin() as conn:
            if not apply:
                conn.execute(text('SET TRANSACTION READ ONLY'))
            else:
                conn.execute(text("SET LOCAL lock_timeout = '5s'"))
                conn.execute(text('LOCK TABLE master_data, master_data_float IN ACCESS EXCLUSIVE MODE'))
            exists = conn.execute(text("SELECT to_regclass('public.dmbs_schema_migrations')")).scalar()
            if exists and conn.execute(text('SELECT 1 FROM dmbs_schema_migrations WHERE version=:version'), {'version': VERSION}).first():
                print('Migration 001 is already applied.')
                return
            backup = {}
            for table in ('master_data', 'master_data_float'):
                rows = [dict(row) for row in conn.execute(text(f'SELECT * FROM {table}')).mappings()]
                backup[table] = rows
                expected = normalize_master_data(pd.DataFrame(rows), table)
                print(f'{table}: {len(rows)} current rows; {len(expected)} normalized keys')
            destination = ROOT / '.local' / ('master-data-backup-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
            destination.parent.mkdir(exist_ok=True)
            destination.write_text(json.dumps(backup, indent=2, default=str) + '\n')
            destination.chmod(0o600)
            print(f'Backup: {destination}')
            if not apply:
                print('Read-only check complete. No database changes. Stop the old worker before --apply.')
                return
            conn.exec_driver_sql((ROOT / 'migrations/001_master_data_keys.sql').read_text())
            conn.execute(text('CREATE TABLE IF NOT EXISTS dmbs_schema_migrations (version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())'))
            conn.execute(text('INSERT INTO dmbs_schema_migrations (version) VALUES (:version)'), {'version': VERSION})
            for table in backup:
                count = conn.execute(text(f'SELECT count(*) FROM {table}')).scalar()
                print(f'{table}: {count} rows after migration')
        print('Migration committed. Deploy the updated scraper before resuming the worker.')
    finally:
        engine.dispose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    run(args.apply)
