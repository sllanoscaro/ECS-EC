/** One shared metric strip describes only the applied period and its available source values. */
import type { DetailResult, AggregateQueryResult } from '../../lib/api/consumption';
import { dashboardDecimal } from './dashboardFormat';
import { periodMetrics } from './periodMetrics';

/** Present five parallel metrics; missing data remains explicit and original values remain intact. */
export function PeriodMetrics({ data }: { data: DetailResult | AggregateQueryResult }) {
  const grouped = 'blocks' in data;
  const metrics = periodMetrics(grouped ? data.blocks : data.rows);
  const items = [
    { label: 'Consumo máximo', value: metrics.maximum },
    { label: 'Consumo mínimo', value: metrics.minimum },
    { label: grouped ? 'Media por bloque' : 'Media por intervalo', value: metrics.mean },
    { label: 'Consumo acumulado', value: metrics.sum },
  ];
  return <section className="panel period-metrics" aria-label="Métricas del período consultado">
    <dl>{items.map(item => <div key={item.label}><dt>{item.label}</dt><dd title={item.value ?? undefined}>{item.value === null ? '—' : <>{dashboardDecimal(item.value)} <span>kWh</span></>}</dd></div>)}
      <div><dt>{grouped ? 'Bloques con datos' : 'Intervalos con datos'}</dt><dd>{metrics.count.toLocaleString('es-CL')}</dd></div>
    </dl>
  </section>;
}
