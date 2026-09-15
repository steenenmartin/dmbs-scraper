const { test, before, beforeEach, after } = require('node:test');
const assert = require('node:assert/strict');
const { PGlite } = require('@electric-sql/pglite');

process.env.DATABASE_URL = 'postgresql://test:test@127.0.0.1:1/test';
const pg = require('pg');
const db = new PGlite();
let failQuery = false;
pg.Pool = class {
  on() {}
  query(sql, params) {
    if (failQuery) return Promise.reject(new Error('Test database unavailable'));
    return db.query(sql, params);
  }
  async end() {}
};
const { getStatus, INSTITUTES } = require('../src/routes/status.ts');
const { app } = require('../src/app.ts');
const server = app.listen(0, '127.0.0.1');
const ready = new Promise(resolve => server.on('listening', resolve));
const ISIN = 'DK0009420069', OTHER = 'DK0009420143', RD = 'DK0004635232';
const read = async (sql, params) => (await db.query(sql, params)).rows;
const at = time => new Date(`2026-09-14T${time}Z`);
const statusAt = async time => getStatus(at(time), read);
const institute = (response, name = 'Jyske') => response.institutes.find(row => row.institute === name);

before(async () => {
  // There is deliberately no status, rates, offers, OHLC or audit table.
  await db.exec(`CREATE TABLE master_data (isin text, institute text, years_to_maturity bigint);
    CREATE TABLE spot_prices (timestamp timestamp, isin text, spot_price double precision);`);
});
beforeEach(async () => {
  failQuery = false;
  await db.exec('TRUNCATE master_data, spot_prices');
  await db.query('INSERT INTO master_data VALUES ($1, $2, 30), ($3, $2, 30)', [ISIN, 'Jyske', OTHER]);
});
after(async () => {
  await new Promise(resolve => server.close(resolve));
  await db.close();
});
async function quote(time, isin = ISIN, price = 98) {
  await db.query('INSERT INTO spot_prices VALUES ($1, $2, $3)', [`2026-09-14 ${time}`, isin, price]);
}
async function fullDay(day, end = '14:55', isins = [ISIN]) {
  await db.query(`INSERT INTO spot_prices
    SELECT stamp, isin, 98 FROM generate_series($1::timestamp, $2::timestamp, interval '5 minutes') stamp
    CROSS JOIN unnest($3::text[]) isin`, [`${day} 07:00`, `${day} ${end}`, isins]);
}

test('all configured institutes are present: waiting before first deadline, NotOK after it', async () => {
  const waiting = await statusAt('07:02:59');
  assert.deepEqual(waiting.institutes.map(row => row.institute), [...INSTITUTES]);
  assert.ok(waiting.institutes.every(row => row.status === 'Waiting' && row.last_data_time === null));
  assert.ok((await statusAt('07:03:00')).institutes.every(row => row.status === 'NotOK'));
  await quote('07:00');
  assert.equal(institute(await statusAt('07:02:30')).status, 'OK');
});

test('unquoted RD bond and historical master records do not manufacture missing quotes', async () => {
  await db.query('INSERT INTO master_data VALUES ($1, $2, 30), ($3, $2, 30)', [RD, 'RealKreditDanmark', 'DK0004635075']);
  await quote('07:00', RD);
  await quote('07:05', RD);
  const row = institute(await statusAt('07:06:00'), 'RealKreditDanmark');
  assert.equal(row.status, 'OK');
  assert.equal(row.last_data_time, '2026-09-14T07:05:00.000Z');
});

test('a disappearing bond creates a historical gap which remains after recovery', async () => {
  for (const isin of [ISIN, OTHER]) await quote('07:00', isin);
  await quote('07:05');
  assert.equal(institute(await statusAt('07:06:00')).status, 'SomeDataMissing');
  for (const isin of [ISIN, OTHER]) await quote('07:10', isin);
  assert.equal(institute(await statusAt('07:11:00')).status, 'SomeDataMissing');
  assert.equal(institute(await statusAt('07:16:00')).status, 'NotOK');
  for (const isin of [ISIN, OTHER]) await quote('07:20', isin);
  assert.equal(institute(await statusAt('07:21:00')).status, 'SomeDataMissing');
});

test('legitimately delayed original commits can fill gaps without a sticky error flag', async () => {
  await quote('07:00');
  await quote('07:10');
  assert.equal(institute(await statusAt('07:11:00')).status, 'SomeDataMissing');
  await quote('07:05');
  assert.equal(institute(await statusAt('07:11:00')).status, 'OK');
});

test('newly quoted bonds have no expectations before their first valid daily quote', async () => {
  for (const time of ['07:00', '07:05', '07:10']) await quote(time);
  await quote('07:10', OTHER);
  assert.equal(institute(await statusAt('07:11:00')).status, 'OK');
});

test('late institute startup leaves the missing opening slot visible', async () => {
  await quote('07:05');
  assert.equal(institute(await statusAt('07:06:00')).status, 'SomeDataMissing');
});

test('new observations during grace never compensate for earlier missing slots', async () => {
  await quote('07:00');
  assert.equal(institute(await statusAt('07:05:59')).status, 'OK');
  await quote('07:10');
  assert.equal(institute(await statusAt('07:10:30')).status, 'NotOK');
  assert.equal(institute(await statusAt('07:11:00')).status, 'SomeDataMissing');
});

test('identical duplicates and Nordea maturity variants count once; conflicts do not count', async () => {
  await db.exec("UPDATE master_data SET institute='Nordea'");
  await db.query('INSERT INTO master_data VALUES ($1, $2, 15)', [ISIN, 'Nordea']);
  for (const time of ['07:00', '07:05']) {
    await quote(time);
    await quote(time);
  }
  assert.equal(institute(await statusAt('07:06:00'), 'Nordea').status, 'OK');
  await quote('07:05', ISIN, 99);
  assert.equal(institute(await statusAt('07:06:00'), 'Nordea').status, 'NotOK');
  await quote('07:10');
  assert.equal(institute(await statusAt('07:11:00'), 'Nordea').status, 'SomeDataMissing');
});

test('invalid, off-grid, future and old-day values cannot establish coverage', async () => {
  await quote('07:00');
  await quote('07:00', ISIN, null); // A valid sibling remains valid, like storage.clean().
  for (const value of [null, 0, -1, 'NaN', 'Infinity', '-Infinity']) await quote('07:05', ISIN, value);
  await quote('07:05:01');
  await quote('07:10');
  await db.query('INSERT INTO spot_prices VALUES ($1,$2,98)', ['2026-09-11 07:05', ISIN]);
  await db.exec(`INSERT INTO master_data VALUES ('bad-isin', 'Jyske', 30);
    INSERT INTO spot_prices VALUES ('2026-09-14 07:05','bad-isin',98)`);
  assert.equal(institute(await statusAt('07:06:00')).status, 'NotOK');
});

test('market closes independently of a missing final scrape, after a sixty-second grace', async () => {
  await fullDay('2026-09-14', '14:55', [ISIN, OTHER]);
  const justClosed = await statusAt('15:00:00');
  assert.equal(justClosed.market_open, false);
  assert.equal(institute(justClosed).status, 'OK');
  assert.equal(justClosed.refresh_at, '2026-09-14T15:01:00.000Z');
  const missed = await statusAt('15:01:00');
  assert.equal(missed.market_open, false);
  assert.equal(institute(missed).status, 'NotOK');
  assert.match(institute(missed).detail, /17:00/);
  await quote('15:00');
  assert.equal(institute(await statusAt('15:02:00')).status, 'SomeDataMissing');
  await quote('15:00', OTHER);
  assert.equal(institute(await statusAt('18:00:00')).status, 'OK');
});

test('final gaps remain through weekends, then the next trading day starts a new history', async () => {
  await fullDay('2026-09-18');
  const weekend = await getStatus(new Date('2026-09-19T12:00:00Z'), read);
  assert.equal(weekend.trading_date, '2026-09-18');
  assert.equal(weekend.market_open, false);
  assert.equal(institute(weekend).status, 'NotOK');
  const open = await getStatus(new Date('2026-09-21T07:00:00Z'), read);
  assert.equal(open.trading_date, '2026-09-21');
  assert.equal(open.market_open, true);
  assert.equal(institute(open).status, 'Waiting');
  await db.query('INSERT INTO spot_prices VALUES ($1,$2,98)', ['2026-09-21 07:00', ISIN]);
  assert.equal(institute(await getStatus(new Date('2026-09-21T07:03:00Z'), read)).status, 'OK');
});

test('HTTP status uses the coverage envelope and never caches a database failure', async t => {
  await ready;
  const url = `http://127.0.0.1:${server.address().port}/api/status`;
  const response = await fetch(url);
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  const data = await response.json();
  assert.equal(data.institutes.length, 4);
  assert.match(data.trading_date, /^\d{4}-\d{2}-\d{2}$/);
  assert.equal(typeof data.market_open, 'boolean');
  assert.ok(Date.parse(data.refresh_at) > Date.parse(data.checked_at));
  failQuery = true;
  t.mock.method(console, 'error', () => {});
  const failed = await fetch(url);
  assert.equal(failed.status, 500);
  assert.equal(failed.headers.get('cache-control'), 'no-store');
  assert.deepEqual(await failed.json(), { error: 'Failed to fetch status' });
});
