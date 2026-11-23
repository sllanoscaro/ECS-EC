/** Accessible circular chart and exact table for the same server-owned proportional estimate. */
import Decimal from 'decimal.js';
import type { EnergyDistribution as Distribution, CategoryEstimate } from '../../lib/api/costs';
import { categoryColors, readableDecimal, shortInstant } from '../../lib/visual';
import { money } from './presentation';

const reasons: Record<NonNullable<Distribution['reason_code']>, string> = {
  energy_charge_unavailable: 'El cargo neto de energía no está disponible para estimar el reparto.',
  general_evidence_changed: 'Las mediciones generales disponibles no coinciden con la captura del cálculo. No es posible conciliar el reparto.',
  category_coverage_incomplete: 'Faltan datos de una o más categorías para completar el reparto del ciclo.',
  zero_energy_basis: 'El consumo general es cero. No hay una base para calcular porcentajes.',
  categories_exceed_general: 'La suma de las categorías supera el consumo del medidor general. Revise las mediciones antes de distribuir el cargo.',
};
const stateLabel: Record<CategoryEstimate['state'], string> = { available: 'No disponible', no_meter: 'Sin medidor', no_data: 'Sin datos', incomplete: 'Datos incompletos' };

export function EnergyDistribution({ data, busy, error, retry, timezone }: { data: Distribution | null; busy: boolean; error: boolean; retry: () => void; timezone: string }) {
  const available = data?.state === 'available';
  const categories = [...(data?.categories ?? [])].sort((a, b) => new Decimal(b.percent ?? '-1').cmp(a.percent ?? '-1'));
  const residual = available && (new Decimal(data.unassigned_percent ?? '0').gt(0) || new Decimal(data.unassigned_amount ?? '0').gt(0));
  const slices = available ? [
    ...categories.filter(row => row.percent !== null).map(row => ({ id: row.id, label: row.name, percent: row.percent!, amount: row.estimated_amount, color: categoryColors[row.id] })),
    ...(residual ? [{ id: 'unassigned', label: 'Sin asignar a categorías', percent: data.unassigned_percent!, amount: data.unassigned_amount, color: '#8B9690' }] : []),
  ] : [];
  let offset = 0;
  return <section className="panel cost-distribution" aria-labelledby="distribution-title" aria-busy={busy}>
    <div className="cost-panel-heading"><div><h2 id="distribution-title">Costo de energía por categoría</h2><p className="section-description">Distribución estimada del cargo de energía según participación del consumo</p></div><span className="cost-estimate-label">Estimación proporcional</span></div>
    {busy && <p role="status" className="loading-state">Consultando el consumo del ciclo…</p>}
    {error && <p role="alert" className="notice notice--error">No se pudo consultar el reparto.<button onClick={retry}>Reintentar reparto</button></p>}
    {!busy && !error && data?.reason_code && <p className="notice notice--warning" role="status">{reasons[data.reason_code]}</p>}
    {!busy && !error && <div className="cost-distribution-grid">
      <figure className="cost-donut">
        <svg viewBox="0 0 320 320" role="img" aria-labelledby="donut-title">
          <title id="donut-title">{available ? 'Distribución estimada del cargo neto de energía en pesos chilenos. Valores y porcentajes en la tabla.' : 'Distribución no disponible: faltan datos conciliados del ciclo.'}</title>
          <circle cx="160" cy="160" r="115" fill="none" stroke="#e6eae7" strokeWidth="48" />
          {slices.map(slice => {
            const ratio = new Decimal(slice.percent).toNumber();
            const start = offset; offset += ratio;
            const angle = ((start + ratio / 2) / 100 * 360 - 90) * Math.PI / 180;
            return ratio > 0 ? <g key={slice.id}><circle cx="160" cy="160" r="115" fill="none" stroke={slice.color} strokeWidth="48" pathLength="100"
              strokeDasharray={`${ratio} ${100 - ratio}`} strokeDashoffset={-start} transform="rotate(-90 160 160)" />
              {ratio >= 5 && <text x={160 + 115 * Math.cos(angle)} y={160 + 115 * Math.sin(angle)} textAnchor="middle" dominantBaseline="central" fill="white" fontSize="19" fontWeight="700">{new Decimal(slice.percent).toDecimalPlaces(0,Decimal.ROUND_HALF_UP).toFixed(0)} %</text>}
            </g> : null;
          })}
          <text x="160" y="154" textAnchor="middle" className="cost-donut-value" style={{ fontSize: Math.min(25, 300 / money(data?.energy_amount).length) }}>{available ? money(data.energy_amount) : 'Sin reparto'}</text>
          <text x="160" y="178" textAnchor="middle" className="cost-donut-unit">{available ? 'CLP · Energía neta' : 'Datos no disponibles'}</text>
        </svg>
      </figure>
      <div className="table-scroll"><table className="cost-category-table"><thead><tr><th>Categoría</th><th className="numeric">Participación</th><th className="numeric">Costo estimado</th></tr></thead>
        <tbody>{categories.map(row => <tr key={row.id}><th scope="row"><span className="cost-category-name"><i style={{ background: categoryColors[row.id] }} aria-hidden="true" />{row.name}</span></th>
          <td className="numeric">{row.percent === null ? '—' : `${readableDecimal(row.percent)} %`}</td><td className="numeric">{row.estimated_amount === null ? stateLabel[row.state] : money(row.estimated_amount)}</td></tr>)}
          {residual && <tr><th scope="row"><span className="cost-category-name"><i style={{ background: '#8B9690' }} aria-hidden="true" />Sin asignar a categorías</span></th><td className="numeric">{readableDecimal(data.unassigned_percent!)} %</td><td className="numeric">{money(data.unassigned_amount)}</td></tr>}
        </tbody>{available && <tfoot><tr><th scope="row">Total distribuido{residual ? ' y sin asignar' : ''}</th><td className="numeric">100 %</td><td className="numeric">{money(data.energy_amount)}</td></tr></tfoot>}</table></div>
    </div>}
    <p className="cost-footnote">Reparto proporcional al consumo del mismo ciclo. No incluye demanda, transmisión, cargo fijo ni impuestos. Es una estimación, no un cargo facturado por categoría.</p>
    {available && <p className="cost-footnote">Las etiquetas del gráfico se redondean al entero. La tabla conserva los porcentajes del reparto.</p>}
    {residual && <p className="cost-footnote">El consumo general sin categoría medida se conserva como «Sin asignar».</p>}
    {data && <p className="cost-footnote">Consulta de consumo: {shortInstant(data.cutoff_at, timezone)}. La estimación usa las mediciones disponibles y puede cambiar al actualizar; el cálculo guardado conserva su revisión.</p>}
  </section>;
}
