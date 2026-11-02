/** Public synthetic wire fixtures; never import installation/measurement data from an application DB. */
import type { DetailRow } from "../../../src/lib/api/consumption-types";

/** Produce one physical row with an exact interval, value and opaque origin reference. */
export function row(energy = "1", start = "2026-01-01T00:00:00.000001-03:00", end = "2026-01-01T01:00:00.000001-03:00"): DetailRow {
  return { record_id: `synthetic-${start}-${energy}`, revision: 1, start, end, energy_kwh: energy,
    first_incorporated_at: "2026-01-02T00:00:00-03:00", configuration_revision: 1, category_revision: 1,
    origin: { kind: "measured", source_id: "10000000-0000-0000-0000-000000000005", original_value: energy, original_unit: "kWh" } };
}
