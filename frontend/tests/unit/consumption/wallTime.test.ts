/** Calendar input regression: missing/repeated hours and exact microseconds remain explicit. */
import { expect, it } from 'vitest';
import { wallCandidates, wallValue } from '../../../src/components/consumption/wallTime';
it('returns both offsets of the repeated Santiago hour and none for the missing hour', () => {
  expect(wallCandidates('2026-04-04T23:30:00', 'America/Santiago')).toEqual(['2026-04-04T23:30:00-03:00', '2026-04-04T23:30:00-04:00']);
  expect(wallCandidates('2026-09-06T00:30:00', 'America/Santiago')).toEqual([]);
});
it('retains microseconds and does not follow the browser timezone', () => {
  expect(wallCandidates(wallValue('2026-01-01T09:00:00.000001-03:00'), 'America/Santiago')).toEqual(['2026-01-01T09:00:00.000001-03:00']);
  expect(wallCandidates('2026-01-01T09:00', 'Etc/UTC')).toEqual(['2026-01-01T09:00:00+00:00']);
});
