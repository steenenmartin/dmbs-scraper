"""Normalize scraper products and insert new master records without replacing curated data."""
from __future__ import annotations

import logging
import math
import re
import sqlite3
from collections import defaultdict

import pandas as pd
from sqlalchemy import text

FIXED_COLUMNS = ('isin', 'institute', 'years_to_maturity', 'max_interest_only_period', 'coupon_rate')
FLOAT_COLUMNS = ('institute', 'fixed_rate_period', 'max_interest_only_period')
TABLES = {
    'master_data': (FIXED_COLUMNS, ('isin', 'years_to_maturity', 'max_interest_only_period')),
    'master_data_float': (FLOAT_COLUMNS, FLOAT_COLUMNS),
}


def _number(value, field, integer=False):
    if isinstance(value, bool):
        raise ValueError(f'{field} must be a number')
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise ValueError(f'{field} must be a number') from None
    if not math.isfinite(number) or (integer and (number < 0 or not number.is_integer())):
        raise ValueError(f'Invalid {field}: {value!r}')
    return int(number) if integer else number


def normalize_master_data(frame: pd.DataFrame, table_name: str) -> pd.DataFrame:
    columns, _keys = TABLES[table_name]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    groups = defaultdict(list)
    for record in frame.to_dict('records'):
        try:
            row = {column: record[column] for column in columns}
            if not isinstance(row['institute'], str) or not row['institute'].strip():
                raise ValueError('Missing institute')
            row['institute'] = row['institute'].strip()
            row['max_interest_only_period'] = _number(row['max_interest_only_period'], 'max_interest_only_period', True)
            if table_name == 'master_data':
                if not isinstance(row['isin'], str) or not re.fullmatch(r'[A-Z]{2}[A-Z0-9]{9}[0-9]', row['isin']):
                    raise ValueError('Invalid ISIN')
                row['coupon_rate'] = _number(row['coupon_rate'], 'coupon_rate')
                row['years_to_maturity'] = _number(row['years_to_maturity'], 'years_to_maturity', True)
                if row['years_to_maturity'] == 0:
                    raise ValueError('Loan term must be positive')
                groups[row['isin']].append(row)
            else:
                row['fixed_rate_period'] = _number(row['fixed_rate_period'], 'fixed_rate_period', True)
                if row['fixed_rate_period'] == 0:
                    raise ValueError('Fixed rate period must be positive')
                groups[tuple(row[column] for column in columns)].append(row)
        except (KeyError, ValueError) as error:
            logging.warning('Skipping invalid %s observation (%s): %s', table_name, record.get('isin', record.get('institute')), error)

    normalized = []
    for key, rows in groups.items():
        unique = {tuple(row[column] for column in columns): row for row in rows}
        rows = list(unique.values())
        if table_name == 'master_data' and len(rows) > 1:
            institutes = {row['institute'] for row in rows}
            coupons = {row['coupon_rate'] for row in rows}
            terms = {row['years_to_maturity'] for row in rows}
            freedoms = {row['max_interest_only_period'] for row in rows}
            if len(institutes) != 1 or len(coupons) != 1:
                logging.warning('Conflicting master data for %s; leaving it for manual review: %s', key, rows)
                continue
            if institutes == {'Jyske'}:
                # Jyske's IO=0 copies of OA/OA30 bonds must not enter the IO=0 filter.
                # Retain the observed maximum for this bond; do not combine terms.
                if len(terms) != 1 or not freedoms <= {0, 10, 30}:
                    logging.warning('Conflicting Jyske master data for %s: %s', key, rows)
                    continue
                selected = max(rows, key=lambda row: row['max_interest_only_period'])
                logging.warning('Conflicting Jyske interest-only observations for %s; retaining maximum observed period: selected=%s observations=%s', key, selected, rows)
                rows = [selected]
            # Other institutes may use one ISIN for several legitimate products.
            # In particular, Nordea's 15- and 20-year rows must both remain filterable.
        normalized.extend(rows)
    return pd.DataFrame(normalized, columns=columns)


def insert_master_data(connection, frame: pd.DataFrame, table_name: str) -> int:
    """Caller owns the transaction. Requires the unique keys from migration 001.

    Existing product keys are deliberately never updated by scraping. Differences are logged
    so manual corrections survive subsequent scrapes and concurrent admin edits.
    """
    columns, keys = TABLES[table_name]
    normalized = normalize_master_data(frame, table_name)
    if normalized.empty:
        return 0

    # Verify migration by key names on PostgreSQL; the old worker can DROP the table
    # and silently remove indexes, in which case ON CONFLICT alone offers no safety.
    if not isinstance(connection, sqlite3.Connection) and connection.dialect.name == 'postgresql':
        required = ('master_data_product_key', 'master_data_jyske_isin_key') if table_name == 'master_data' else ('master_data_float_product_key',)
        found = set(connection.execute(text(
            "SELECT indexname FROM pg_indexes WHERE schemaname=current_schema() AND tablename=:table"
        ), {'table': table_name}).scalars())
        if not set(required) <= found:
            raise RuntimeError('Master-data migration 001 is missing; stop the old worker and apply it first')

    def execute(sql, params=None):
        if isinstance(connection, sqlite3.Connection):
            return connection.execute(sql, params or {})
        return connection.execute(text(sql), params or {})

    projection = ', '.join(f'"{column}"' for column in columns)
    existing_rows = execute(f'SELECT {projection} FROM "{table_name}"').fetchall()
    # Coupon and issuer belong to the security, regardless of which loan product
    # exposed it. Compare across scrapes and product keys, not only within a batch.
    identities = defaultdict(set)
    if table_name == 'master_data':
        for stored in existing_rows:
            stored = dict(zip(columns, stored))
            identities[stored['isin']].add((stored['institute'], stored['coupon_rate']))
    existing = normalize_master_data(pd.DataFrame(existing_rows, columns=columns), table_name)
    def record_key(row):
        if table_name == 'master_data' and row['institute'] == 'Jyske':
            return ('Jyske', row['isin'])
        return tuple(row[key] for key in keys)

    by_key = {record_key(row): row for row in existing.to_dict('records')}
    sql = (
        f'INSERT INTO "{table_name}" ({projection}) '
        f'VALUES ({", ".join(":" + column for column in columns)}) '
    )
    inserted = 0
    for row in normalized.to_dict('records'):
        if table_name == 'master_data':
            observed_identity = (row['institute'], row['coupon_rate'])
            stored_identities = identities.get(row['isin'])
            if stored_identities and stored_identities != {observed_identity}:
                logging.warning('Conflicting master data for %s; skipping observation for manual review: stored identities=%s scraped=%s', row['isin'], stored_identities, row)
                continue
        key = record_key(row)
        previous = by_key.get(key)
        if previous is not None and previous != row:
            logging.warning('Preserving existing %s %s; scraper differs: stored=%s scraped=%s', table_name, key, previous, row)
        # Always use the database constraint, including when another writer inserts
        # the same key after our SELECT. No read/replace or application-only dedupe.
        if table_name == 'master_data' and row['institute'] == 'Jyske':
            conflict = "(isin) WHERE institute = 'Jyske'"
        else:
            conflict = '(' + ', '.join(keys) + ')'
        inserted += execute(sql + f'ON CONFLICT {conflict} DO NOTHING RETURNING {keys[0]}', row).fetchone() is not None
    logging.info('Inserted %d new rows into %s; existing master records retained', inserted, table_name)
    return inserted


def save_master_data(conn_module, frame: pd.DataFrame, table_name: str) -> int:
    resource = conn_module.client_factory()
    try:
        if isinstance(resource, sqlite3.Connection):
            with resource:
                return insert_master_data(resource, frame, table_name)
        with resource.begin() as connection:
            return insert_master_data(connection, frame, table_name)
    finally:
        if isinstance(resource, sqlite3.Connection):
            resource.close()
        else:
            resource.dispose()
