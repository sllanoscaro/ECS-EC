/** Hand-maintained spec002 contracts/http.md wire types; keep decimal/duration/timestamp values textual. */
import type { ConfigurationSegment, Period } from './consumption-types';
export type Granularity = 'detail' | 'hour' | 'day' | 'month' | 'year';
export type SourceMode = 'measured' | 'calculated' | 'mixed' | 'unavailable';
/** A safe warning reports known evidence without leaking storage errors. */
export type HistoryWarning = { readonly code: string; readonly detail: string; readonly start?: string | null; readonly end?: string | null; readonly record_refs?: readonly string[] };
/** One persisted aggregate or a nullable empty projection; exact server classification precedes rounding. */
export type AggregateBlock = Period & {
  readonly aggregate_id: string | null; readonly revision: number | null;
  readonly duration_us: string; readonly covered_duration_us: string; readonly energy_kwh: string | null;
  readonly coverage_percent: string; readonly coverage_state: 'complete' | 'incomplete' | 'no_data';
  readonly temporal_state: 'not_started' | 'ongoing' | 'finished'; readonly contribution_count: number;
  readonly source_mode: SourceMode; readonly provenance_segments: readonly ConfigurationSegment[];
  readonly created_at: string | null; readonly last_new_data_at: string | null; readonly retain_until: string | null;
  readonly warnings: readonly HistoryWarning[];
};
/** Nonnumeric002 calculation evidence stays separate from incorporated blocks. */
export type HistoryDiagnostic = { readonly start: string; readonly end: string; readonly reason_code: string;
  readonly missing_categories: readonly string[]; readonly next_admissible_at: string | null;
  readonly configuration_segments: readonly ConfigurationSegment[] };
/** One captured selection feeds chart/table; consumers never compute sums in the browser. */
export type AggregateQueryResult = {
  readonly request_ref: string; readonly building_id: string; readonly category_id: string; readonly period: Period;
  readonly granularity: Exclude<Granularity, 'detail'>; readonly unit: 'kWh'; readonly cutoff_at: string;
  readonly state: 'available' | 'incomplete' | 'no_data' | 'no_meter'; readonly source_mode: SourceMode;
  readonly configuration_segments: readonly ConfigurationSegment[]; readonly blocks: readonly AggregateBlock[];
  readonly excluded_blocks: readonly { readonly start: string; readonly end: string; readonly reason_code: string }[];
  readonly diagnostics: readonly HistoryDiagnostic[]; readonly warnings: readonly HistoryWarning[]; readonly reason_code: string | null;
};
