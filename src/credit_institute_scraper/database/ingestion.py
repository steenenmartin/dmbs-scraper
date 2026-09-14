"""Validated, idempotent writes to existing tables. Never recreate a table."""
from contextlib import contextmanager
import logging
import math
import re
import sqlite3
from datetime import datetime, date

import pandas as pd
from sqlalchemy import text

PRICE_COLUMNS = {
    'spot_prices': ('spot_price',), 'offer_prices': ('offer_price',),
    'closing_prices': ('spot_price',),
    'ohlc_prices': ('open_price', 'high_price', 'low_price', 'close_price'),
}
RATE_KEYS = ('timestamp', 'institute', 'fixed_rate_period', 'max_interest_only_period')


def execute(connection, sql, params=None):
    if isinstance(connection, sqlite3.Connection) or connection.dialect.name == 'sqlite':
        def adapt(record):
            return {key: value.isoformat(sep=' ') if isinstance(value, datetime)
                    else value.isoformat() if isinstance(value, date) else value
                    for key, value in record.items()}
        params = [adapt(record) for record in params] if isinstance(params, list) else adapt(params or {})
    if isinstance(connection, sqlite3.Connection):
        if isinstance(params, list):
            return connection.executemany(sql, params)
        return connection.execute(sql, params or {})
    return connection.execute(text(sql), params or {})


@contextmanager
def transaction(conn_module):
    resource = conn_module.client_factory()
    try:
        if isinstance(resource, sqlite3.Connection):
            resource.execute('BEGIN IMMEDIATE')
            with resource:
                yield resource
        else:
            with resource.begin() as connection:
                if connection.dialect.name == 'postgresql':
                    execute(connection, "SET LOCAL lock_timeout='5s'")
                    execute(connection, "SET LOCAL statement_timeout='30s'")
                    # Shared by every framework writer; prevents races between dynos.
                    execute(connection, 'SELECT pg_advisory_xact_lock(163447, 1)')
                yield connection
    finally:
        if isinstance(resource, sqlite3.Connection):
            resource.close()
        else:
            resource.dispose()


def prepare_observations(frame, table):
    if table not in PRICE_COLUMNS and table != 'rates':
        raise ValueError(f'Unsupported observation table: {table}')
    keys = RATE_KEYS if table == 'rates' else ('timestamp', 'isin')
    values = ('spot_rate',) if table == 'rates' else PRICE_COLUMNS[table]
    columns = keys + values
    if frame.empty:
        return pd.DataFrame(columns=columns)
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f'Missing {table} columns: {sorted(missing)}')
    records = []
    for raw in frame.to_dict('records'):
        try:
            row = {column: raw[column] for column in columns}
            stamp = pd.Timestamp(row['timestamp'])
            if pd.isna(stamp):
                raise ValueError('Missing timestamp')
            if stamp.tzinfo is not None:
                stamp = stamp.tz_convert('UTC').tz_localize(None)
            row['timestamp'] = stamp.to_pydatetime()
            if table == 'rates':
                if not isinstance(row['institute'], str) or not row['institute'].strip():
                    raise ValueError('Missing institute')
                for column in RATE_KEYS[2:]:
                    number = float(row[column])
                    if not math.isfinite(number) or not number.is_integer() or number < 0:
                        raise ValueError(f'Invalid {column}')
                    row[column] = int(number)
                if row['fixed_rate_period'] == 0:
                    raise ValueError('Missing fixed rate period')
            elif not isinstance(row['isin'], str) or not re.fullmatch(r'[A-Z]{2}[A-Z0-9]{9}[0-9]', row['isin']):
                raise ValueError('Invalid ISIN')
            for column in values:
                if isinstance(row[column], bool):
                    raise ValueError(f'Invalid {column}')
                number = float(row[column])
                if not math.isfinite(number) or number == 0 or (table != 'rates' and number < 0):
                    raise ValueError(f'Missing or invalid {column}')
                row[column] = number
            if table == 'ohlc_prices' and not (
                row['low_price'] <= min(row['open_price'], row['close_price'])
                <= max(row['open_price'], row['close_price']) <= row['high_price']
            ):
                raise ValueError('Inconsistent OHLC bounds')
            records.append(row)
        except (TypeError, ValueError, OverflowError) as error:
            logging.warning('Rejected %s observation %s: %s', table, raw.get('isin', raw.get('institute')), error)
    clean = pd.DataFrame(records, columns=columns).drop_duplicates()
    conflicts = clean.duplicated(subset=list(keys), keep=False)
    if conflicts.any():
        logging.warning('Conflicting %s observations rejected: %s', table, clean.loc[conflicts].to_dict('records'))
    return clean.loc[~conflicts]


def write_observations(connection, frame, table):
    clean = prepare_observations(frame, table)
    if clean.empty:
        return 0
    columns = tuple(clean.columns)
    keys = RATE_KEYS if table == 'rates' else ('timestamp', 'isin')
    projection = ', '.join(f'"{column}"' for column in columns)
    rows = clean.to_dict('records')
    for row in rows:
        row['timestamp'] = pd.Timestamp(row['timestamp']).to_pydatetime()
    # Only read the relevant interval; old prices remain untouched. The SELECT
    # also makes a missing/misconfigured schema fail rather than auto-create it.
    existing_rows = execute(connection, f'SELECT {projection} FROM "{table}" WHERE timestamp >= :start AND timestamp <= :end',
                            {'start': min(row['timestamp'] for row in rows), 'end': max(row['timestamp'] for row in rows)}).fetchall()
    existing = prepare_observations(pd.DataFrame(existing_rows, columns=columns), table)
    existing_keys = {tuple(row[key] for key in keys): row for row in existing.to_dict('records')}
    # Include conflicting existing keys too: never add more observations to them.
    for row in existing_rows:
        row = dict(zip(columns, row))
        row['timestamp'] = pd.Timestamp(row['timestamp']).to_pydatetime()
        if table == 'rates':
            for key in RATE_KEYS[2:]:
                try:
                    row[key] = int(float(row[key]))
                except (TypeError, ValueError, OverflowError):
                    # Malformed historical keys cannot match a validated new key.
                    # Preserve the row without aborting unrelated observations.
                    pass
        existing_keys.setdefault(tuple(row[key] for key in keys), row)
    inserts = []
    for row in rows:
        key = tuple(row[column] for column in keys)
        previous = existing_keys.get(key)
        if previous is not None:
            if previous != row:
                logging.warning('Preserving existing %s observation %s; incoming value differs', table, key)
        else:
            inserts.append(row)
    if inserts:
        sql = f'INSERT INTO "{table}" ({projection}) VALUES ({", ".join(":" + column for column in columns)})'
        execute(connection, sql, inserts)
    logging.info('Inserted %d observations into %s', len(inserts), table)
    return len(inserts)


def write_status(connection, rows):
    for row in rows:
        row = dict(row)
        if row['timestamp'] is None:
            row['timestamp'] = execute(connection, 'SELECT max(last_data_time) FROM status WHERE institute=:institute',
                                       {'institute': row['institute']}).fetchone()[0]
        # Existing deployments have no status key. The transaction lock serializes
        # this small replacement and preserves the table, permissions and indexes.
        execute(connection, 'DELETE FROM status WHERE institute=:institute', {'institute': row['institute']})
        execute(connection, 'INSERT INTO status (institute, last_data_time, status) VALUES (:institute, :timestamp, :status)', row)


def write_log(connection, timestamp, message):
    execute(connection, 'INSERT INTO scrape_logs (time, error) VALUES (:time, :error)', {'time': timestamp, 'error': message})
