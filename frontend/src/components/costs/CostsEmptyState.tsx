"use client";
import { useEffect, useState } from 'react';
import { costsApi, type CostsReadiness } from '../../lib/api/costs';
import { useSession } from '../identity/SessionProvider';

/** Read prerequisites only; opening this view never configures a source or creates a calculation. */
export function CostsEmptyState() {
  const { session } = useSession();
  const [data,setData] = useState<CostsReadiness | null>(null);
  const [error,setError] = useState(false);
  const [attempt,setAttempt] = useState(0);
  useEffect(()=>{
    let active=true; const controller=new AbortController(); setData(null); setError(false);
    void costsApi.readiness(controller.signal).then(value=>{if(active)setData(value);})
      .catch(()=>{if(active)setError(true);});
    return ()=>{active=false;controller.abort();};
  },[attempt]);
  const administrator=session?.permissions.includes('costs.calculations.create');
  const ready=data?.physical_general && data.supply_configured && data.profile_published;
  return <section className="panel cost-setup" aria-labelledby="cost-setup-title"><h2 id="cost-setup-title">Aún no hay cálculos de costos</h2>
    <p className="section-description">Esta vista muestra cálculos guardados del suministro general. Actualizar consulta los datos; no genera un cálculo nuevo.</p>
    {!data && !error && <p role="status">Comprobando la configuración de costos…</p>}
    {error && <p className="notice notice--error" role="alert">No se pudo comprobar la configuración.<button onClick={()=>setAttempt(value=>value+1)}>Reintentar configuración</button></p>}
    {data && <>
      <dl className="cost-setup-checks"><div><dt>Medidor general propio</dt><dd>{data.physical_general?'Configurado':'Pendiente: el total calculado de categorías no permite calcular BT4.3.'}</dd></div>
        <div><dt>Suministro de costos</dt><dd>{data.supply_configured?'Configurado':'Pendiente de configurar.'}</dd></div>
        <div><dt>Perfil tarifario publicado</dt><dd>{data.profile_published?'Disponible':'Pendiente: se necesitan cargos, precios y vigencias documentados.'}</dd></div></dl>
      <p>{ready?'La configuración está preparada. El primer cálculo debe usar un período con mediciones físicas completas del suministro general.':'Complete los requisitos pendientes antes de generar el primer cálculo.'}</p>
      {administrator ? <div className="cost-setup-actions">{!data.physical_general && <a href="/administracion/consumo/">Revisar fuentes de consumo</a>}<a href="/administracion/costos/">{ready?'Generar el primer cálculo':'Configurar costos'}</a></div>
        : <p className="section-description">El administrador técnico puede {ready?'generar el primer cálculo':'completar esta configuración'} en Administración.</p>}
    </>}
  </section>;
}
