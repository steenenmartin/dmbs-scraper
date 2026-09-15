const { test } = require('node:test');
const assert = require('node:assert/strict');
const { existsSync } = require('node:fs');
const { resolve } = require('node:path');
const { spawnSync } = require('node:child_process');
const { getMarketWindow, getActiveTimeRange, isTradingDay, MARKET_CALENDAR } = require('../src/utils/dateHelper.ts');

test('opening, closing and delivery deadlines are separate', () => {
  for (const [time, day, open, slot, refresh] of [
    ['06:59:30', '2026-09-14', false, '2026-09-14T15:00:00.000Z', '07:00:00'],
    ['07:00:00', '2026-09-15', true, null, '07:01:00'],
    ['07:02:30', '2026-09-15', true, null, '07:03:00'],
    ['07:03:00', '2026-09-15', true, '2026-09-15T07:00:00.000Z', '07:04:00'],
    ['07:05:30', '2026-09-15', true, '2026-09-15T07:00:00.000Z', '07:06:00'],
    ['07:06:00', '2026-09-15', true, '2026-09-15T07:05:00.000Z', '07:07:00'],
    ['14:59:30', '2026-09-15', true, '2026-09-15T14:55:00.000Z', '15:00:00'],
    ['15:00:00', '2026-09-15', false, '2026-09-15T14:55:00.000Z', '15:01:00'],
    ['15:00:30', '2026-09-15', false, '2026-09-15T14:55:00.000Z', '15:01:00'],
    ['15:01:00', '2026-09-15', false, '2026-09-15T15:00:00.000Z', '15:02:00'],
  ]) {
    const now = new Date(`2026-09-15T${time}Z`);
    const window = getMarketWindow(now);
    assert.equal(window.tradingDate, day, time);
    assert.equal(window.marketOpen, open, time);
    assert.equal(window.requiredSlot?.toISOString() ?? null, slot, time);
    assert.equal(window.refreshAt.toISOString(), `2026-09-15T${refresh}.000Z`, time);
    assert.deepEqual(getActiveTimeRange(now), [window.open, window.close]);
  }
});

test('closed days retain the previous trading day in its own DST season', () => {
  for (const [now, day, utcOpen] of [
    ['2026-03-29T12:00:00Z', '2026-03-27', 8],
    ['2026-03-30T06:59:00Z', '2026-03-27', 8],
    ['2026-10-25T12:00:00Z', '2026-10-23', 7],
    ['2026-04-06T12:00:00Z', '2026-04-01', 7],
    ['2026-05-25T12:00:00Z', '2026-05-22', 7],
    ['2027-01-01T12:00:00Z', '2026-12-30', 8],
    ['2023-05-05T12:00:00Z', '2023-05-04', 7],
  ]) {
    const window = getMarketWindow(new Date(now));
    assert.equal(window.tradingDate, day, now);
    assert.equal(window.open.getUTCHours(), utcOpen, now);
    assert.equal(window.close.getUTCHours(), utcOpen + 8, now);
    assert.equal(window.marketOpen, false, now);
    assert.deepEqual(window.requiredSlot, window.close, now);
  }
  assert.equal(isTradingDay('2026-05-01'), true, 'Store Bededag is no longer a holiday');
  assert.equal(getMarketWindow(new Date('2026-03-30T07:00:00Z')).tradingDate, '2026-03-30');
});

test('Python scheduler and backend agree on six years of holidays and every daily deadline', () => {
  const root = resolve(__dirname, '../../..');
  const python = process.env.PYTHON || [
    resolve(root, '.venv/Scripts/python.exe'), resolve(root, '.venv/bin/python'),
  ].find(existsSync) || 'python';
  const script = `
import json
from datetime import date, datetime, timedelta
import scraper
day, holidays = date(2023, 1, 1), []
while day < date(2029, 1, 1):
    holidays.append([day.isoformat(), scraper.is_holiday(day)])
    day += timedelta(days=1)
schedules = []
for day in ('2023-05-04', '2026-01-14', '2026-09-14', '2027-01-14'):
    now = datetime.fromisoformat(day).replace(tzinfo=scraper.COPENHAGEN)
    trigger, previous, ticks = scraper.market_trigger(), None, []
    while True:
        tick = trigger.get_next_fire_time(previous, now)
        if tick.date().isoformat() != day:
            break
        ticks.append(tick.isoformat())
        previous, now = tick, tick + timedelta(microseconds=1)
    schedules.append(ticks)
print(json.dumps(dict(holidays=holidays, schedules=schedules)))
`;
  const result = spawnSync(python, ['-c', script], { cwd: root, encoding: 'utf8', timeout: 30_000 });
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stderr);
  const { holidays, schedules } = JSON.parse(result.stdout);
  for (const [day, holiday] of holidays) assert.equal(isTradingDay(day), !holiday, day);
  for (const ticks of schedules) {
    assert.equal(ticks.length, 97);
    const open = getMarketWindow(new Date(ticks[0])).open.getTime();
    for (const [index, tick] of ticks.entries()) {
      const deadline = new Date(Date.parse(tick) + MARKET_CALENDAR.deliveryGraceSeconds * 1000);
      const slot = open + index * MARKET_CALENDAR.intervalMinutes * 60_000;
      assert.equal(getMarketWindow(deadline).requiredSlot.getTime(), slot, tick);
      assert.equal(getMarketWindow(new Date(deadline.getTime() - 1)).requiredSlot?.getTime() ?? null,
        index ? slot - MARKET_CALENDAR.intervalMinutes * 60_000 : null, tick);
    }
  }
});
