/** Monotone cubic interpolation for chart geometry only; exact readings remain separate. */
export type ChartPoint = { x: number; y: number };

/** Preserve sampled extrema: flat or reversing secants have a zero tangent, avoiding overshoot. */
export function smoothLine(points: readonly ChartPoint[]): string {
  if (!points.length) return '';
  const slopes = points.slice(1).map((p, i) => (p.y - points[i].y) / (p.x - points[i].x));
  const tangents = points.map((_, i) => {
    if (!i) return slopes[0] ?? 0;
    if (i === points.length - 1) return slopes[i - 1];
    const a = slopes[i - 1], b = slopes[i];
    return a * b <= 0 ? 0 : 2 * a * b / (a + b);
  });
  return `M ${points[0].x} ${points[0].y}` + points.slice(1).map((p, j) => {
    const previous = points[j], third = (p.x - previous.x) / 3;
    return ` C ${previous.x + third} ${previous.y + third * tangents[j]} ${p.x - third} ${p.y - third * tangents[j + 1]} ${p.x} ${p.y}`;
  }).join('');
}
