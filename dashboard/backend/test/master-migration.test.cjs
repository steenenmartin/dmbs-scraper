const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { PGlite } = require('@electric-sql/pglite');
const migration = readFileSync(resolve(__dirname, '../../../migrations/001_master_data_keys.sql'), 'utf8');
const reviewed = [
 ['DK0002058502', 'Nordea', 4, 20, 0], ['DK0002059153', 'Nordea', 5, 20, 0],
 ['DK0002061134', 'Nordea', 3, 20, 0], ['DK0002066521', 'Nordea', 3.5, 20, 0],
 ['DK0009409336', 'Jyske', 5, 30, 30], ['DK0009409419', 'Jyske', 5, 30, 10],
 ['DK0009410508', 'Jyske', 6, 30, 10], ['DK0009413601', 'Jyske', 4, 30, 10],
 ['DK0009414419', 'Jyske', 4, 30, 30], ['DK0009416547', 'Jyske', 3.5, 30, 10],
 ['DK0009420143', 'Jyske', 4, 30, 10], ['DK0009420226', 'Jyske', 4, 30, 30],
];
async function fixture() {
 const db = new PGlite();
 await db.exec(`CREATE TABLE master_data (isin text, institute text, coupon_rate double precision, years_to_maturity bigint, max_interest_only_period double precision);
 CREATE TABLE master_data_float (institute text, fixed_rate_period bigint, max_interest_only_period text);
 INSERT INTO master_data_float VALUES ('Jyske',3,'0'),('Jyske',3,'0'),('Jyske',3,'0.0'),('TotalKredit',3,'10');`);
 for (const row of reviewed) {
  await db.query('INSERT INTO master_data VALUES ($1,$2,$3,$4,$5)', row);
  const variant = [...row];
  if (row[1] === 'Nordea') variant[3] = 15; else variant[4] = 0;
  await db.query('INSERT INTO master_data VALUES ($1,$2,$3,$4,$5)', variant);
 }
 await db.exec("INSERT INTO master_data VALUES ('DK0009420069','Jyske',4,30,0)");
 return db;
}
async function apply(db) {
 await db.exec('BEGIN');
 try { await db.exec(migration); await db.exec('COMMIT'); }
 catch (error) { await db.exec('ROLLBACK'); throw error; }
}
test('reviewed cleanup preserves table, retains unrelated data, and adds database keys', async () => {
 const db = await fixture();
 try {
  const oidBefore = (await db.query("SELECT 'master_data'::regclass::oid AS oid")).rows[0].oid;
  await apply(db);
  assert.equal((await db.query('SELECT count(*) AS count FROM master_data')).rows[0].count, 17);
  for (const row of reviewed.filter(row => row[1] === 'Nordea')) {
    const terms = (await db.query('SELECT years_to_maturity FROM master_data WHERE isin=$1 ORDER BY years_to_maturity', [row[0]])).rows;
    assert.deepEqual(terms.map(row => Number(row.years_to_maturity)), [15, 20]);
  }
  assert.equal((await db.query("SELECT 'master_data'::regclass::oid AS oid")).rows[0].oid, oidBefore);
  const filtered = await db.query("SELECT isin FROM master_data WHERE institute='Jyske' AND coupon_rate=4 AND years_to_maturity=30 AND max_interest_only_period=0");
  assert.deepEqual(filtered.rows.map(row => row.isin), ['DK0009420069']);
  // Replay the next scrape's bad IO=0 observation against the new partial key.
  await db.exec("INSERT INTO master_data VALUES ('DK0009420143','Jyske',4,30,0) ON CONFLICT (isin) WHERE institute='Jyske' DO NOTHING");
  const replayed = await db.query("SELECT max_interest_only_period FROM master_data WHERE isin='DK0009420143'");
  assert.deepEqual(replayed.rows.map(row => row.max_interest_only_period), [10]);
  for (const row of reviewed) {
   const actual = (await db.query('SELECT * FROM master_data WHERE isin=$1 AND years_to_maturity=$2', [row[0],row[3]])).rows[0];
   assert.equal(Number(actual.years_to_maturity), row[3]);
   assert.equal(Number(actual.max_interest_only_period), row[4]);
  }
  assert.equal((await db.query('SELECT count(*) AS count FROM master_data_float')).rows[0].count, 2);
  assert.equal((await db.query("SELECT pg_typeof(max_interest_only_period)::text AS type FROM master_data_float LIMIT 1")).rows[0].type, 'bigint');
  await assert.rejects(db.exec('INSERT INTO master_data SELECT * FROM master_data LIMIT 1'), /duplicate key/);
  await assert.rejects(db.exec('INSERT INTO master_data_float SELECT * FROM master_data_float LIMIT 1'), /duplicate key/);
  await db.exec("INSERT INTO master_data_float VALUES ('Jyske', 3, '0') ON CONFLICT (institute, fixed_rate_period, max_interest_only_period) DO NOTHING");
  assert.equal((await db.query('SELECT count(*) AS count FROM master_data_float')).rows[0].count, 2);
 } finally { await db.close(); }
});
test('a changed reviewed row aborts and preserves every original row', async () => {
 const db = await fixture();
 try {
  await db.exec("UPDATE master_data SET coupon_rate=99 WHERE isin='DK0009420143' AND max_interest_only_period=10");
  await assert.rejects(apply(db), /reviewed row is missing or changed/);
  assert.equal((await db.query('SELECT count(*) AS count FROM master_data')).rows[0].count, 25);
  assert.equal((await db.query('SELECT count(*) AS count FROM master_data_float')).rows[0].count, 4);
 } finally { await db.close(); }
});
test('unknown conflicting ISIN rolls back cleanup and type changes', async () => {
 const db = await fixture();
 try {
  await db.exec("INSERT INTO master_data VALUES ('DK0009420069','Jyske',9,30,0)");
  await assert.rejects(apply(db), /unique index|duplicat/);
  assert.equal((await db.query('SELECT count(*) AS count FROM master_data')).rows[0].count, 26);
  assert.equal((await db.query("SELECT pg_typeof(max_interest_only_period)::text AS type FROM master_data_float LIMIT 1")).rows[0].type, 'text');
 } finally { await db.close(); }
});
test('fractional periods are rejected rather than rounded', async () => {
 const db = await fixture();
 try {
  await db.exec("INSERT INTO master_data_float VALUES ('Jyske',3,'10.5')");
  await assert.rejects(apply(db), /Invalid floating master numeric values/);
  assert.equal((await db.query('SELECT count(*) AS count FROM master_data')).rows[0].count, 25);
 } finally { await db.close(); }
});
