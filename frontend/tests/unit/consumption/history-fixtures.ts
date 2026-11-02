/** Known002 grouped wire fixtures, shared by presentation/state regressions. */
import type { AggregateBlock } from "../../../src/lib/api/consumption";
/** Exact fixture deliberately includes null, measured zero and one missing microsecond. */
export const blocks: readonly AggregateBlock[] = [
  { start: '2026-01-01T00:00:00-03:00', end: '2026-01-01T01:00:00-03:00', timezone: 'America/Santiago',
    aggregate_id: 'block', revision: 1, duration_us: '3600000000', covered_duration_us: '3599999999',
    energy_kwh: '0', coverage_percent: '100', coverage_state: 'incomplete', temporal_state: 'finished',
    contribution_count: 1, source_mode: 'measured', provenance_segments: [], created_at: '2026-01-01T00:00:00Z',
    last_new_data_at: '2026-01-01T00:00:00Z', retain_until: '2027-01-01T00:00:00Z', warnings: [] },
  { start: '2026-01-01T01:00:00-03:00', end: '2026-01-01T02:00:00-03:00', timezone: 'America/Santiago',
    aggregate_id: null, revision: null, duration_us: '3600000000', covered_duration_us: '0',
    energy_kwh: null, coverage_percent: '0', coverage_state: 'no_data', temporal_state: 'not_started',
    contribution_count: 0, source_mode: 'unavailable', provenance_segments: [], created_at: null,
    last_new_data_at: null, retain_until: null, warnings: [] },
];
