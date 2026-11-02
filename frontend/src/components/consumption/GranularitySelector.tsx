/** Calendar grouping changes only scale; the container retains category, zone and the exact filter. */
import type { Granularity } from '../../lib/api/consumption';

/** Emit one closed scale selection; detail remains the initial001 representation. */
export function GranularitySelector({ value, onChange }: { value: Granularity; onChange: (value: Granularity) => void }) {
  return <label>Agrupación<select value={value} onChange={event => onChange(event.target.value as Granularity)}>
    <option value="detail">Detalle</option><option value="hour">Hora</option><option value="day">Día</option>
    <option value="month">Mes</option><option value="year">Año</option>
  </select></label>;
}
