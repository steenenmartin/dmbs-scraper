const { test } = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { InstituteStatusPanel } = require('../src/components/InstituteStatusPanel.tsx');
const { useInstituteStatus } = require('../src/hooks/useInstituteStatus.ts');

const snapshot = (overrides = {}) => ({
  trading_date: '2026-09-15',
  market_open: true,
  checked_at: '2026-09-15T14:59:50Z',
  refresh_at: '2026-09-15T15:00:00Z',
  institutes: [{
    institute: 'RealKreditDanmark',
    status: 'SomeDataMissing',
    last_data_time: '2026-09-15T14:55:00Z',
    detail: 'Missing observations earlier today.',
  }],
  ...overrides,
});

function markup(data, options = {}) {
  return renderToStaticMarkup(React.createElement(InstituteStatusPanel, {
    snapshot: data, loading: false, error: '', ...options,
  }));
}

test('closed badges stay neutral while tooltips retain the trading day and missing history', () => {
  for (const inSidebar of [true, false]) {
    for (const status of ['SomeDataMissing', 'NotOK', 'OK', 'Waiting']) {
      const data = snapshot({ market_open: false });
      data.institutes[0].status = status;
      const html = markup(data, { inSidebar });
      assert.match(html, /Market closed\. 2026-09-15:/);
      assert.match(html, /Missing observations earlier today\./);
      assert.doesNotMatch(html, /Last scrape/);
      assert.match(html.replace(/<[^>]+>/g, ''), /Closed/);
      assert.doesNotMatch(html, /bg-amber|bg-rose|bg-emerald/);
    }
  }
});

test('live outcomes, absent data and Copenhagen timestamps render without overflow-prone labels', () => {
  for (const [status, label] of [['OK', 'OK'], ['SomeDataMissing', 'Partial'], ['NotOK', 'Not OK'], ['Waiting', 'Waiting']]) {
    const data = snapshot();
    data.institutes[0].status = status;
    data.institutes[0].last_data_time = null;
    const html = markup(data, { inSidebar: true });
    assert.ok(html.replace(/<[^>]+>/g, '').includes(label));
    assert.match(html, /No data/);
    assert.match(html, /minmax\(0,1fr\)/);
    assert.match(html, /whitespace-nowrap/);
  }
  assert.match(markup(snapshot(), { inSidebar: true }), /16:55 CEST/);
  const winter = snapshot();
  winter.institutes[0].last_data_time = '2026-01-15T15:55:00Z';
  assert.match(markup(winter, { inSidebar: true }), /16:55 CET/);
});

test('failed or expired status never displays cached green badges', () => {
  const data = snapshot();
  data.institutes[0].status = 'OK';
  const html = markup(data, { error: 'Status request timed out.' });
  assert.match(html, /Status unavailable/);
  assert.match(html, /Last confirmed 2026-09-15: OK/);
  assert.doesNotMatch(html, /bg-emerald|text-emerald/);
  assert.match(html.replace(/<[^>]+>/g, ''), /Unknown/);
  assert.match(markup(null, { error: 'Offline' }), /Status unavailable/);
  assert.match(markup(null, { loading: true }), /Loading status/);
});

// Run the hook's actual effects and state updates without adding a DOM test dependency.
function mountHook(t) {
  const states = [];
  let index = 0;
  let effect;
  t.mock.method(React, 'useState', (initial) => {
    const slot = index++;
    if (slot === states.length) states.push(initial);
    return [states[slot], (value) => { states[slot] = typeof value === 'function' ? value(states[slot]) : value; }];
  });
  t.mock.method(React, 'useEffect', (callback) => { effect = callback; });
  const oldWindow = globalThis.window;
  const oldDocument = globalThis.document;
  globalThis.window = new EventTarget();
  globalThis.document = Object.assign(new EventTarget(), { visibilityState: 'visible' });
  const read = () => { index = 0; return useInstituteStatus(); };
  read();
  const cleanup = effect();
  t.after(() => {
    cleanup();
    globalThis.window = oldWindow;
    globalThis.document = oldDocument;
  });
  return { read, cleanup };
}

async function settle() {
  for (let i = 0; i < 8; i++) await Promise.resolve();
}

const response = (data) => ({ ok: true, json: async () => data });

test('server deadline expires cached status independently of a hung refresh and client clock skew', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout', 'Date'], now: new Date('2036-01-01T00:00:00Z') });
  let signal;
  let calls = 0;
  const fetch = t.mock.method(globalThis, 'fetch', async (_url, options) => {
    if (++calls === 1) return response(snapshot());
    signal = options.signal;
    return new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new Error('aborted'))));
  });
  const hook = mountHook(t);
  await settle();
  assert.equal(hook.read().error, '');
  assert.equal(hook.read().snapshot.market_open, true);
  t.mock.timers.tick(9_999);
  assert.equal(fetch.mock.callCount(), 1);
  t.mock.timers.tick(1);
  assert.equal(fetch.mock.callCount(), 2);
  assert.match(hook.read().error, /unavailable/);
  t.mock.timers.tick(10_000);
  await settle();
  assert.equal(signal.aborted, true);
  assert.match(hook.read().error, /timed out/);
  assert.equal(hook.read().loading, false);
});

test('polling retries within a minute, refreshes on focus and cleans up active requests', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout', 'Date'], now: new Date('2026-09-15T14:00:00Z') });
  let signal;
  let hanging = false;
  let failing = true;
  const fetch = t.mock.method(globalThis, 'fetch', async (_url, options) => {
    if (failing) return { ok: false, status: 503 };
    if (hanging) {
      signal = options.signal;
      return new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new Error('aborted'))));
    }
    return response(snapshot({ refresh_at: '2026-09-16T08:00:00Z' }));
  });
  const hook = mountHook(t);
  await settle();
  assert.match(hook.read().error, /503/);
  t.mock.timers.tick(60_000);
  await settle();
  assert.equal(fetch.mock.callCount(), 2);
  failing = false;
  window.dispatchEvent(new Event('focus'));
  await settle();
  assert.equal(hook.read().error, '');
  t.mock.timers.tick(60_000);
  await settle();
  assert.equal(fetch.mock.callCount(), 4);
  hanging = true;
  document.dispatchEvent(new Event('visibilitychange'));
  await settle();
  assert.equal(fetch.mock.callCount(), 5);
  window.dispatchEvent(new Event('focus'));
  assert.equal(fetch.mock.callCount(), 5, 'active requests do not overlap');
  hook.cleanup();
  await settle();
  assert.equal(signal.aborted, true);
  window.dispatchEvent(new Event('focus'));
  t.mock.timers.tick(120_000);
  await settle();
  assert.equal(fetch.mock.callCount(), 5, 'unmounted hooks stop polling and listening');
});

test('a response arriving after its deadline cannot replace cached status or restart a tight retry loop', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout', 'Date'], now: new Date('2026-09-15T14:59:50Z') });
  const original = snapshot();
  let finish;
  let calls = 0;
  const fetch = t.mock.method(globalThis, 'fetch', async () => {
    if (++calls !== 2) return response(original);
    return new Promise((resolve) => { finish = resolve; });
  });
  const hook = mountHook(t);
  await settle();
  t.mock.timers.tick(9_000);
  window.dispatchEvent(new Event('focus'));
  t.mock.timers.tick(2_000);
  assert.match(hook.read().error, /unavailable/);
  const expired = snapshot({ checked_at: '2026-09-15T14:59:59Z' });
  expired.institutes[0].status = 'OK';
  finish(response(expired));
  await settle();
  assert.equal(hook.read().snapshot, original);
  assert.match(hook.read().error, /expired/);
  t.mock.timers.tick(57_999);
  assert.equal(fetch.mock.callCount(), 2);
  t.mock.timers.tick(1);
  await settle();
  assert.equal(fetch.mock.callCount(), 3);
});
