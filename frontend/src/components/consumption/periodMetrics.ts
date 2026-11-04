/** Derived period statistics over the exact, already-authorized chart/table response. */
import Decimal from 'decimal.js';

/** Summarize available interval energies; null never counts as zero or enters the arithmetic mean.
 * Precision covers every source digit plus sum carry, including values above binary float limits.
 * Mean is arithmetic per returned interval/block, not time-weighted or extrapolated into gaps.
 */
export function periodMetrics(rows: readonly { energy_kwh: string | null }[]) {
  const values = rows.flatMap(row => row.energy_kwh === null ? [] : [row.energy_kwh]);
  if (!values.length) return { maximum: null, minimum: null, mean: null, sum: null, count: 0 };
  const precision = values.reduce((maximum, value) => Math.max(maximum, value.replace('.', '').length), 50) + String(values.length).length + 5;
  const Exact = Decimal.clone({ precision });
  let sum = new Exact(0), maximum = new Exact(values[0]), minimum = maximum;
  for (const value of values) {
    const energy = new Exact(value);
    sum = sum.plus(energy);
    maximum = Exact.max(maximum, energy);
    minimum = Exact.min(minimum, energy);
  }
  return { maximum: maximum.toFixed(), minimum: minimum.toFixed(), sum: sum.toFixed(), mean: sum.div(values.length).toFixed(), count: values.length };
}
