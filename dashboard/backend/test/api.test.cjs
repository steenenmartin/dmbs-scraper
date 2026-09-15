const { test, after } = require('node:test');
const assert = require('node:assert/strict');
process.env.DATABASE_URL = 'postgresql://test:test@127.0.0.1:1/test';
process.env.DYNO = 'web.test';
const pg = require('pg');
let poolOptions;
pg.Pool = class {
  constructor(options) { poolOptions = options; }
  on() {}
  async query() { return { rows: [{ ok: 1 }] }; }
  async end() {}
};
const { app } = require('../src/app.ts');
const server = app.listen(0, '127.0.0.1');
const ready = new Promise(resolve => server.on('listening', resolve));
after(() => new Promise(resolve => server.close(resolve)));
async function request(path, method = 'GET') {
  await ready;
  return fetch(`http://127.0.0.1:${server.address().port}${path}`, { method });
}
test('health reports database availability without editing capabilities', async () => {
  const response = await request('/api/health');
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { connected: true, database: 'postgres' });
  assert.deepEqual(poolOptions.ssl, { rejectUnauthorized: false });
});
test('database timestamps retain precision and parse to the same UTC instant across offsets', () => {
  assert.equal(pg.types.getTypeParser(1114)('2026-09-14 15:00:00.123456'), '2026-09-14T15:00:00.123456Z');
  for (const stamp of ['2026-09-14 15:00:00+00', '2026-09-14 05:00:00-10', '2026-09-14 20:30:00+05:30']) {
    assert.equal(new Date(pg.types.getTypeParser(1184)(stamp)).toISOString(), '2026-09-14T15:00:00.000Z');
  }
});
test('API has no data editing endpoints', async () => {
  for (const [path, method] of [['/api/admin/tables', 'GET'], ['/api/admin/master_data', 'PATCH'], ['/api/master-data', 'POST']]) {
    const response = await request(path, method);
    assert.equal(response.status, 404);
    assert.deepEqual(await response.json(), { error: 'Unknown API endpoint' });
  }
});
