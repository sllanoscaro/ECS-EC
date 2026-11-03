/** Responsive exact-interval SVG; geometry never changes the underlying decimal or joins gaps. */
"use client";
import { useEffect, useId, useRef, useState } from 'react';
import Decimal from 'decimal.js';
import type { DetailRow, AggregateBlock, CategoryId, Period } from '../../lib/api/consumption';
import { blockLabel } from './historyFormat';
import { chartMaximum, energyLabel, instantMicros, intervalLabel, projectRatio } from './format';
import { categoryColors, shortInstant } from '../../lib/visual';
const AxisDecimal = Decimal.clone({ precision: 50 });
/** Render shared source values at actual container width; each datum has keyboard-accessible exact evidence. */
export function EnergyChart({ rows: detailRows, blocks, points, timezone, categoryId = 'CAT-01', period }: { points?: readonly { start: string; end: string; energy_kwh: string | null }[]; blocks?: readonly AggregateBlock[]; rows: readonly DetailRow[]; timezone: string; categoryId?: CategoryId; period?: Period }) {
  const [active, setActive] = useState<string | null>(null);
  const [width, setWidth] = useState(800);
  const container = useRef<HTMLElement>(null);
  const description = useId(), tooltip = useId();
  useEffect(() => {
    if (!container.current || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(entries => setWidth(Math.max(260, entries[0].contentRect.width)));
    observer.observe(container.current); return () => observer.disconnect();
  }, []);
  const rows = points ? points.map(point => ({...point, record_id: point.start})) : blocks ? blocks.map(block => ({ start: block.start, end: block.end, energy_kwh: block.energy_kwh, record_id: block.aggregate_id ?? block.start })) : detailRows;
  const times = rows.map(row => ({ start: instantMicros(row.start), end: instantMicros(row.end) }));
  const lower = period ? instantMicros(period.start) : times[0]?.start ?? 0n;
  const upper = period ? instantMicros(period.end) : times.reduce((maximum, t) => t.end > maximum ? t.end : maximum, lower + 1n);
  const span = (upper - lower).toString();
  const maximum = chartMaximum(rows.flatMap(row => row.energy_kwh === null ? [] : [row.energy_kwh]));
  const left = width < 500 ? 52 : 64, right = width - 18, plot = right - left, top = 26, baseline = 226;
  const color = categoryColors[categoryId];
  return <figure ref={container} className="energy-chart">
    <svg role="img" aria-label={blocks ? 'Energía eléctrica por bloque (kWh)' : 'Energía eléctrica por intervalo (kWh)'} aria-describedby={description} viewBox={`0 0 ${width} 288`} style={{ width: '100%', display: 'block' }}>
      <desc id={description}>Barras independientes. Círculo: cero medido. Rombo: positivo inferior a un píxel. No se unen huecos. Cada dato admite foco y conserva su cifra exacta.</desc>
      {[0, 1, 2, 3, 4].map(i => <g key={i}><line x1={left} x2={right} y1={baseline - i * 50} y2={baseline - i * 50} stroke="var(--rule)" /><text x={left - 10} y={baseline - i * 50 + 5} textAnchor="end" fontSize="13" fill="var(--muted)">{`${new AxisDecimal(maximum).mul(i).div(4).toSignificantDigits(4).toString()}${i === 4 ? ' kWh' : ''}`}</text></g>)}
      <text x={left} y="14" fontSize="13" fill="var(--muted)">kWh</text>
      {rows.map((row, index) => {
        /** Only dimensionless geometry is approximate; textual evidence stays exact. */
        const x = left + plot * projectRatio((times[index].start - lower).toString(), span);
        const end = left + plot * projectRatio((times[index].end - lower).toString(), span);
        const height = (baseline - top) * projectRatio(row.energy_kwh ?? '0', maximum);
        const zero = /^0(?:\.0+)?$/.test(row.energy_kwh ?? '');
        const kind = row.energy_kwh === null ? 'gap' : zero ? 'zero' : height < 1 ? 'subpixel-positive' : 'bar';
        const label = blocks ? blockLabel(blocks[index], timezone) : row.energy_kwh === null ? `${row.start} → ${row.end}: Sin datos` : intervalLabel(row.start, row.end, row.energy_kwh, timezone);
        return <g key={row.record_id} role="graphics-symbol" tabIndex={0} aria-label={label} aria-describedby={active === label ? tooltip : undefined} data-kind={kind} data-x={x} data-x-end={end} onFocus={() => setActive(label)} onBlur={() => setActive(null)} onMouseEnter={() => setActive(label)} onMouseLeave={() => setActive(null)}>
          <title>{label}</title>{kind === 'bar' ? <rect x={x + .5} y={baseline - height} width={Math.max(.5, end - x - 1)} height={height} fill={color} /> : kind === 'zero' ? <circle cx={(x + end) / 2} cy={baseline} r="4" fill="white" stroke={color} strokeWidth="2" /> : kind === 'subpixel-positive' ? <polygon points={`${(x+end)/2},${baseline-7} ${(x+end)/2+4},${baseline-3} ${(x+end)/2},${baseline+1} ${(x+end)/2-4},${baseline-3}`} fill={color} /> : <line x1={x} x2={end} y1={baseline+7} y2={baseline+7} stroke="var(--muted)" strokeDasharray="2 3" />}
        </g>;
      })}
      {[0, 1, 2, 3, 4].filter(i => width >= 500 || i % 2 === 0).map(i => {
        const instant = new Date(Number(lower / 1000n) + Number((upper - lower) / 1000n) * i / 4).toISOString();
        return <text key={i} x={left + plot * i / 4} y="253" textAnchor={i === 0 ? 'start' : i === 4 ? 'end' : 'middle'} fontSize="13" fill="var(--muted)">{shortInstant(instant, timezone, upper - lower <= 86400000000n)}</text>;
      })}
    </svg>
    {!rows.length && <p className="chart-empty">Sin intervalos incorporados.</p>}
    <figcaption className="chart-legend"><span><i className="zero-key" style={{ borderColor: color }} /> Cero medido</span><span>— Sin datos: intervalo vacío</span></figcaption>
    {active && <p id={tooltip} role="tooltip" className="chart-tooltip">{active}</p>}
  </figure>;
}
