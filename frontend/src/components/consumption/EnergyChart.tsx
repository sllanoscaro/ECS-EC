/** Independent SVG intervals, never interpolated/downsampled, backed by exactly the table's response rows. */
"use client";

import { useId, useState } from "react";
import type { DetailRow } from "../../lib/api/consumption";
import { chartMaximum, energyLabel, instantMicros, intervalLabel, projectRatio } from "./format";

/** Render all incorporated rows with focusable exact evidence; only SVG coordinates are approximate. */
export function EnergyChart({ rows, timezone }: { rows: readonly DetailRow[]; timezone: string }) {
  const [active, setActive] = useState<string | null>(null);
  const description = useId();
  const tooltip = useId();
  if (!rows.length) return <p>Sin intervalos incorporados.</p>;
  const times = rows.map(row => ({ start: instantMicros(row.start), end: instantMicros(row.end) }));
  const lower = times.reduce((minimum, t) => t.start < minimum ? t.start : minimum, times[0].start);
  const upper = times.reduce((maximum, t) => t.end > maximum ? t.end : maximum, times[0].end);
  const span = (upper - lower).toString();
  const maximum = chartMaximum(rows.map(row => row.energy_kwh));
  return <figure>
    <svg role="img" aria-label="Energía eléctrica por intervalo (kWh)" aria-describedby={description} viewBox="0 0 800 290" style={{ width: "100%", minHeight: "16rem" }}>
      <desc id={description}>Barras independientes por intervalo. Círculo: cero. Rombo: positivo inferior a un píxel. Cada dato admite foco y muestra su cifra exacta. No se unen huecos.</desc>
      <text x="4" y="18" fontSize="10">{energyLabel(maximum)}</text>
      <text x="4" y="244" fontSize="10">0 kWh</text>
      <line x1="60" x2="780" y1="240" y2="240" stroke="currentColor" />
      {rows.map((row, index) => {
        /** Project one interval; its source string and textual evidence stay untouched. */
        const x = 60 + 720 * projectRatio((times[index].start - lower).toString(), span);
        const right = 60 + 720 * projectRatio((times[index].end - lower).toString(), span);
        const height = 200 * projectRatio(row.energy_kwh, maximum);
        const zero = /^0(?:\.0+)?$/.test(row.energy_kwh);
        const kind = zero ? "zero" : height < 1 ? "subpixel-positive" : "bar";
        const label = intervalLabel(row.start, row.end, row.energy_kwh, timezone);
        return <g key={row.record_id} role="graphics-symbol" tabIndex={0} aria-label={label} aria-describedby={active === label ? tooltip : undefined}
          data-kind={kind} data-x={x} data-x-end={right}
          onFocus={() => { setActive(label); }} onBlur={() => { setActive(null); }}
          onMouseEnter={() => { setActive(label); }} onMouseLeave={() => { setActive(null); }}>
          <title>{label}</title>
          {kind === "bar" ? <rect x={x} y={240-height} width={Math.max(0.5, right-x)} height={height} fill="#176996" />
            : kind === "zero" ? <circle cx={(x+right)/2} cy="240" r="4" fill="white" stroke="currentColor" />
            : <polygon points={`${(x+right)/2},232 ${(x+right)/2+4},236 ${(x+right)/2},240 ${(x+right)/2-4},236`} fill="#176996" />}
        </g>;
      })}
      <text x="60" y="266" fontSize="9">{rows[0].start}</text>
      <text x="780" y="283" fontSize="9" textAnchor="end">{rows[rows.length-1].end}</text>
    </svg>
    <figcaption>Energía eléctrica (kWh) · {timezone}. Intervalos [inicio, fin).</figcaption>
    {active && <p id={tooltip} role="tooltip">{active}</p>}
  </figure>;
}
