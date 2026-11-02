/** Exact visible labels plus private precision50 geometry; business values never pass through Number. */
import Decimal from "decimal.js";

const GeometryDecimal = Decimal.clone({ precision: 50 });

/** Append the energy unit without modifying the server's exact canonical decimal string. */
export function energyLabel(value: string): string { return `${value} kWh`; }

/** Retain textual microseconds and explicit building offset/zone, independent from the browser zone. */
export function instantLabel(value: string, timezone: string): string { return `${value} (${timezone})`; }

/** Convert only a clamped dimensionless geometric ratio to Number; zero scale never yields NaN. */
export function projectRatio(numerator: string, denominator: string): number {
  if (new GeometryDecimal(denominator).isZero()) return 0;
  return GeometryDecimal.max(0, GeometryDecimal.min(1, new GeometryDecimal(numerator).div(denominator))).toNumber();
}

/** Return the largest positive original string for a chart scale, or an explicit1 kWh all-zero scale. */
export function chartMaximum(values: readonly string[]): string {
  let maximum = "0";
  for (const value of values) if (new GeometryDecimal(value).gt(maximum)) maximum = value;
  return new GeometryDecimal(maximum).isZero() ? "1" : maximum;
}

/** Resolve exact textual microseconds to an integer for geometry; reject missing offsets/invalid instants. */
export function instantMicros(value: string): bigint {
  const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?(Z|[+-]\d{2}:\d{2})$/.exec(value);
  if (!match) throw new Error("Instante inválido.");
  const milliseconds = Date.parse(`${match[1]}${match[3]}`);
  if (!Number.isFinite(milliseconds)) throw new Error("Instante inválido.");
  return BigInt(milliseconds) * 1000n + BigInt((match[2] ?? "").padEnd(6, "0"));
}

/** Describe one exact half-open interval and value for SVG focus/tooltip using the table's formatters. */
export function intervalLabel(start: string, end: string, energy: string, timezone: string): string {
  return `[${instantLabel(start, timezone)}, ${instantLabel(end, timezone)}): ${energyLabel(energy)}`;
}
