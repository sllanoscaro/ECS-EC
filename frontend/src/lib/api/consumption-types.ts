/** Generated from spec-001 OpenAPI by scripts/generate_consumption_types.py; do not edit. */
/** Wire shape of OpenAPI Period; semantic constraints are checked by the server. */
export type Period = { readonly start: string; readonly end: string; readonly timezone: string; };
/** Wire shape of OpenAPI Category; semantic constraints are checked by the server. */
export type Category = { readonly id: "CAT-01" | "CAT-02" | "CAT-03" | "CAT-04" | "CAT-05" | "CAT-06" | "CAT-07"; readonly name: string; readonly scope: string; };
/** Wire shape of OpenAPI CategoryStatus; semantic constraints are checked by the server. */
export type CategoryStatus = { readonly id: "CAT-01" | "CAT-02" | "CAT-03" | "CAT-04" | "CAT-05" | "CAT-06" | "CAT-07"; readonly name: string; readonly scope: string; readonly has_meter: boolean; readonly source_mode: "measured" | "calculated" | "unavailable"; readonly base_categories: ReadonlyArray<"CAT-02" | "CAT-03" | "CAT-04" | "CAT-05" | "CAT-06" | "CAT-07">; readonly category_revision: (number | null); };
/** Wire shape of OpenAPI Catalog; semantic constraints are checked by the server. */
export type Catalog = { readonly building_id: string; readonly timezone: string; readonly cutoff_at: string; readonly default_period: Period; readonly categories: ReadonlyArray<CategoryStatus>; };
/** Wire shape of OpenAPI SourceEntry; semantic constraints are checked by the server. */
export type SourceEntry = { readonly category_id: "CAT-01" | "CAT-02" | "CAT-03" | "CAT-04" | "CAT-05" | "CAT-06" | "CAT-07"; readonly has_meter: boolean; readonly source_id: (string | null); readonly source_label: (string | null); };
/** Wire shape of OpenAPI ConfigurationInput; semantic constraints are checked by the server. */
export type ConfigurationInput = { readonly expected_revision: number; readonly effective_from: (string | null); readonly timezone: string; readonly categories: ReadonlyArray<SourceEntry>; };
/** Wire shape of OpenAPI Configuration; semantic constraints are checked by the server. */
export type Configuration = { readonly id: string; readonly building_id: string; readonly revision: number; readonly effective_from: string; readonly recorded_at: string; readonly timezone: string; readonly categories: ReadonlyArray<ConfiguredSourceEntry>; };
/** Wire shape of OpenAPI ConfigurationSegment; semantic constraints are checked by the server. */
export type ConfigurationSegment = { readonly start: string; readonly end: string; readonly configuration_revision: number; readonly source_mode: "measured" | "calculated" | "unavailable"; readonly base_categories: ReadonlyArray<"CAT-02" | "CAT-03" | "CAT-04" | "CAT-05" | "CAT-06" | "CAT-07">; readonly category_revision: number; readonly source_id: (string | null); readonly basis_sources: ReadonlyArray<BasisSource>; };
/** Wire shape of OpenAPI Contribution; semantic constraints are checked by the server. */
export type Contribution = { readonly measurement_id: string; readonly measurement_revision: number; readonly category_id: "CAT-02" | "CAT-03" | "CAT-04" | "CAT-05" | "CAT-06" | "CAT-07"; readonly source_id: string; readonly start: string; readonly end: string; readonly energy_kwh: MeasurementEnergyKwh; readonly category_revision: number; };
/** Wire shape of OpenAPI MeasuredOrigin; semantic constraints are checked by the server. */
export type MeasuredOrigin = { readonly kind: "measured"; readonly source_id: string; readonly original_value: OriginalEnergyValue; readonly original_unit: "Wh" | "kWh" | "MWh"; };
/** Wire shape of OpenAPI CalculatedOrigin; semantic constraints are checked by the server. */
export type CalculatedOrigin = { readonly kind: "calculated"; readonly base_categories: ReadonlyArray<"CAT-02" | "CAT-03" | "CAT-04" | "CAT-05" | "CAT-06" | "CAT-07">; readonly contributions: ReadonlyArray<Contribution>; };
/** Wire shape of OpenAPI DetailRow; semantic constraints are checked by the server. */
export type DetailRow = { readonly record_id: string; readonly revision: number; readonly start: string; readonly end: string; readonly energy_kwh: CalculatedEnergyKwh; readonly first_incorporated_at: string; readonly configuration_revision: number; readonly origin: (MeasuredOrigin | CalculatedOrigin); readonly category_revision: number; };
/** Wire shape of OpenAPI Diagnostic; semantic constraints are checked by the server. */
export type Diagnostic = { readonly start: string; readonly end: string; readonly configuration_revision: number; readonly reason_code: "missing_contributions" | "pending_incorporation" | "calculation_configuration_changed"; readonly missing_categories: ReadonlyArray<"CAT-02" | "CAT-03" | "CAT-04" | "CAT-05" | "CAT-06" | "CAT-07">; readonly next_admissible_at: (string | null); readonly category_revision: (number | null); readonly configuration_segments: ReadonlyArray<ConfigurationSegment>; };
/** Wire shape of OpenAPI Warning; semantic constraints are checked by the server. */
export type Warning = { readonly code: "crossing_intervals_excluded" | "observed_gaps" | "no_calculation_basis" | "partial_calculation_scope" | "source_unavailable_in_segment"; readonly count: number; readonly message: string; };
/** Wire shape of OpenAPI DetailResult; semantic constraints are checked by the server. */
export type DetailResult = { readonly request_ref: string; readonly building_id: string; readonly category: Category; readonly period: Period; readonly cutoff_at: string; readonly state: "available" | "no_meter" | "no_data" | "incomplete"; readonly source_mode: "measured" | "calculated" | "mixed" | "unavailable"; readonly configuration_segments: ReadonlyArray<ConfigurationSegment>; readonly rows: ReadonlyArray<DetailRow>; readonly diagnostics: ReadonlyArray<Diagnostic>; readonly warnings: ReadonlyArray<Warning>; };
/** Wire shape of OpenAPI FieldError; semantic constraints are checked by the server. */
export type FieldError = { readonly path: string; readonly code: string; readonly message: string; };
/** Wire shape of OpenAPI Problem; semantic constraints are checked by the server. */
export type Problem = { readonly code: string; readonly detail: string; readonly operation_ref: string; readonly field_errors: ReadonlyArray<FieldError>; };
/** Wire shape of OpenAPI MeasurementEnergyKwh; semantic constraints are checked by the server. */
export type MeasurementEnergyKwh = string;
/** Wire shape of OpenAPI CalculatedEnergyKwh; semantic constraints are checked by the server. */
export type CalculatedEnergyKwh = string;
/** Wire shape of OpenAPI OriginalEnergyValue; semantic constraints are checked by the server. */
export type OriginalEnergyValue = string;
/** Wire shape of OpenAPI BasisSource; semantic constraints are checked by the server. */
export type BasisSource = { readonly category_id: "CAT-02" | "CAT-03" | "CAT-04" | "CAT-05" | "CAT-06" | "CAT-07"; readonly source_id: string; };
/** Wire shape of OpenAPI ConfiguredSourceEntry; semantic constraints are checked by the server. */
export type ConfiguredSourceEntry = { readonly category_id: "CAT-01" | "CAT-02" | "CAT-03" | "CAT-04" | "CAT-05" | "CAT-06" | "CAT-07"; readonly has_meter: boolean; readonly source_id: (string | null); readonly source_label: (string | null); readonly category_revision: number; };
