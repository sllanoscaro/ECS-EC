/** Full-calendar004 profile editor: immutable revisions, explicit documentary rules and saved/publication distinction. */
"use client";
import { useEffect, useState, type FormEvent } from "react";
import { financialApi, type SupplyDetail, type ProfileInput, type ProfileSegment, type Charge, type ProfilePage, type ProfileDetail } from "../../lib/api/costs";
import { useFinancialOperation } from "./useFinancialOperation";

const kinds: Charge['kind'][] = ["energia", "transmision", "servicio_publico", "fijo", "potencia_suministrada", "demanda_punta", "impuesto", "otro_documentado"];

/** Start an explicitly incomplete draft, with no fictional source, price, initial date or normative calendar. */
function emptyProfile(supply: SupplyDetail): ProfileInput {
  return { supply_id: supply.id, expected_previous_version_id: null, tariff: "BT4.3", currency: "CLP", publication_state: "draft",
    timezone: "America/Santiago", source_refs: [], territory_conditions: "", required_kinds: ["energia"], segments: [] };
}

/** Return a blank structured segment; a user must confirm actual validity, sources, prices and policies. */
function emptySegment(): ProfileSegment {
  return { valid_from: "", valid_to: null, source_refs: [], historical_rule: "two_monthly_maxima_12_months_v1",
    peak_calendar: { version: "", months: [], weekdays: [], start_time: "18:00", end_time: "22:00", excluded_dates: [] },
    billing_month_policy: { version: "", mode: "explicit_evidence", source_refs: [], rule_id: null },
    rounding_policy: { precision: 50, quantum: "1", mode: "ROUND_HALF_UP", stage: "component" }, charges: [] };
}

/** Edit a complete copied calendar and append it against the latest saved revision, including drafts. */
export function ProfileEditor({ supply }: { supply: SupplyDetail }) {
  const [page, setPage] = useState<ProfilePage | null>(null);
  const [body, setBody] = useState<ProfileInput>(emptyProfile(supply));
  const [error, setError] = useState(false);
  const operation = useFinancialOperation();
  async function reload() {
    /** Explicit review replaces the draft only after a successful administrative read of current metadata. */
    try {
      const value = await financialApi.profiles(); setPage(value); setError(false);
      const latest = value.latest_version ?? value.items.find(item => item.id === value.latest_version_id);
      if (latest) {
        const { supply_id, tariff, currency, publication_state, timezone, source_refs, territory_conditions, required_kinds, segments } = latest;
        setBody({ supply_id, tariff, currency, publication_state, timezone, source_refs, territory_conditions, required_kinds, segments,
          expected_previous_version_id: value.latest_version_id });
      } else setBody(emptyProfile(supply));
    } catch { setError(true); }
  }
  useEffect(() => {
    /** Initial private load is scoped to this supply; no read publishes or recalculates a profile. */
    let active = true; const controller = new AbortController();
    void financialApi.profiles(controller.signal).then(value => {
      if (!active) return;
      setPage(value);
      const latest = value.latest_version ?? value.items.find(item => item.id === value.latest_version_id);
      if (latest) {
        const { supply_id, tariff, currency, publication_state, timezone, source_refs, territory_conditions, required_kinds, segments } = latest;
        setBody({ supply_id, tariff, currency, publication_state, timezone, source_refs, territory_conditions, required_kinds, segments,
          expected_previous_version_id: value.latest_version_id });
      }
    }).catch(() => { if (active) setError(true); });
    return () => { active = false; controller.abort(); };
  }, [supply.id]);
  function copy(value: ProfileDetail) {
    /** Copy the complete historical calendar while keeping the latest saved predecessor for optimistic publication. */
    const { supply_id, tariff, currency, publication_state, timezone, source_refs, territory_conditions, required_kinds, segments } = value;
    setBody({ supply_id, tariff, currency, publication_state, timezone, source_refs, territory_conditions, required_kinds, segments,
      expected_previous_version_id: page?.latest_version_id ?? null });
  }
  async function moreProfiles() {
    /** Read the next signed historical page without changing the currently edited calendar or reviewed predecessor. */
    if (!page?.next_cursor) return;
    try { const next = await financialApi.profiles(undefined, page.next_cursor); setPage(old => old ? { ...old, items: [...old.items, ...next.items], next_cursor: next.next_cursor } : old); }
    catch { setError(true); }
  }
  function patch(value: Partial<ProfileInput>) { /** Retain the rest of the copied full-calendar draft. */ setBody(old => ({ ...old, ...value })); }
  function segment(index: number, value: Partial<ProfileSegment>) { /** Modify only the draft segment; published revisions stay immutable. */ patch({ segments: body.segments.map((item, i) => i === index ? { ...item, ...value } : item) }); }
  function charge(si: number, ci: number, value: Partial<Charge>) { /** Replace one draft charge without applying any financial calculation. */ segment(si, { charges: body.segments[si].charges.map((item, i) => i === ci ? { ...item, ...value } : item) }); }
  function references(value: string) { /** Parse documentary reference lines, preserving values rather than interpreting source text. */ return value.split("\n").filter(Boolean); }
  function submit(event: FormEvent) {
    /** Saving a draft or publication always appends a new complete revision with the reviewed predecessor. */
    event.preventDefault(); const input = { ...body, expected_previous_version_id: page?.latest_version_id ?? null };
    void operation.run(input, key => financialApi.saveProfile(input, key), () => { void reload(); });
  }
  if (!page) return <p role={error ? "alert" : "status"}>{error ? "No se pudo cargar el perfil." : "Cargando perfiles…"}<button onClick={() => { void reload(); }}>Reintentar perfiles</button></p>;
  return <form onSubmit={submit}><h2>Perfil BT4.3 · Nueva revisión completa</h2>
    <p>Última guardada: {page.latest_version_id ?? "Ninguna"} · Publicada seleccionada: {page.selected_published_version_id ?? "Ninguna"}</p>
    <p>Cerrar vigencias abiertas o corregir el pasado exige copiar y guardar el calendario completo. Los cálculos previos no cambian.</p>
    <ul aria-label="Calendarios guardados">{page.items.map(value => <li key={value.id}>Revisión {value.revision} · {value.publication_state === "published" ? "Publicada" : "Borrador"} <button type="button" onClick={() => { copy(value); }}>Copiar calendario revisión {value.revision}</button></li>)}</ul>
    {page.next_cursor && <button type="button" onClick={() => { void moreProfiles(); }}>Más calendarios</button>}
    <fieldset disabled={operation.busy}>
      <label>Estado de la nueva revisión<select value={body.publication_state} onChange={e => { patch({ publication_state: e.target.value as ProfileInput['publication_state'] }); }}><option value="draft">Borrador</option><option value="published">Publicada</option></select></label>
      <label>Zona IANA del perfil<input required value={body.timezone} onChange={e => { patch({ timezone: e.target.value }); }} /></label>
      <label>Condiciones territoriales<input required value={body.territory_conditions} onChange={e => { patch({ territory_conditions: e.target.value }); }} /></label>
      <label>Fuentes del perfil<textarea value={body.source_refs.join("\n")} onChange={e => { patch({ source_refs: references(e.target.value) }); }} /></label>
      <fieldset><legend>Cargos aplicables según el pliego documentado</legend>{kinds.map(kind => <label key={kind}><input type="checkbox" checked={body.required_kinds.includes(kind)} onChange={e => { patch({ required_kinds: e.target.checked ? [...body.required_kinds, kind] : body.required_kinds.filter(value => value !== kind) }); }} />{kind}</label>)}</fieldset>
      {body.segments.map((item, si) => <fieldset key={si}><legend>Segmento {si + 1}</legend>
        <label>Inicio de vigencia {si + 1}<input required value={item.valid_from} onChange={e => { segment(si, { valid_from: e.target.value }); }} /></label>
        <label>Fin de vigencia {si + 1} (vacío significa abierto)<input value={item.valid_to ?? ""} onChange={e => { segment(si, { valid_to: e.target.value || null }); }} /></label>
        <label>Fuentes del segmento {si + 1}<textarea value={item.source_refs.join("\n")} onChange={e => { segment(si, { source_refs: references(e.target.value) }); }} /></label>
        <label>Versión del calendario de punta {si + 1}<input required value={item.peak_calendar.version} onChange={e => { segment(si, { peak_calendar: { ...item.peak_calendar, version: e.target.value } }); }} /></label>
        <label>Meses de punta {si + 1} (1–12 separados por coma)<input value={item.peak_calendar.months.join(",")} onChange={e => { segment(si, { peak_calendar: { ...item.peak_calendar, months: e.target.value ? e.target.value.split(",").map(Number) : [] } }); }} /></label>
        <label>Días de punta {si + 1} (lunes=0, domingo=6)<input value={item.peak_calendar.weekdays.join(",")} onChange={e => { segment(si, { peak_calendar: { ...item.peak_calendar, weekdays: e.target.value ? e.target.value.split(",").map(Number) : [] } }); }} /></label>
        <label>Inicio de punta {si + 1}<input required type="time" value={item.peak_calendar.start_time} onChange={e => { segment(si, { peak_calendar: { ...item.peak_calendar, start_time: e.target.value } }); }} /></label>
        <label>Fin de punta {si + 1}<input required type="time" value={item.peak_calendar.end_time} onChange={e => { segment(si, { peak_calendar: { ...item.peak_calendar, end_time: e.target.value } }); }} /></label>
        <label>Fechas excluidas {si + 1} (YYYY-MM-DD, una por línea)<textarea value={item.peak_calendar.excluded_dates.join("\n")} onChange={e => { segment(si, { peak_calendar: { ...item.peak_calendar, excluded_dates: references(e.target.value) } }); }} /></label>
        <label>Versión de política mensual {si + 1}<input required value={item.billing_month_policy.version} onChange={e => { segment(si, { billing_month_policy: { ...item.billing_month_policy, version: e.target.value } }); }} /></label>
        <label>Modo mensual {si + 1}<select value={item.billing_month_policy.mode} onChange={e => { segment(si, { billing_month_policy: { ...item.billing_month_policy, mode: e.target.value as "explicit_evidence" | "documented_rule", rule_id: null } }); }}><option value="explicit_evidence">Evidencia explícita</option><option value="documented_rule">Regla documentada</option></select></label>
        {item.billing_month_policy.mode === "documented_rule" && <label>Regla documentada {si + 1}<select value={item.billing_month_policy.rule_id ?? ""} onChange={e => { segment(si, { billing_month_policy: { ...item.billing_month_policy, rule_id: e.target.value || null } }); }}><option value="">Sin resolver</option><option value="cycle_start_month_v1">Mes local del inicio documentado</option><option value="cycle_end_month_v1">Mes local del último instante del ciclo documentado</option></select></label>}
        <label>Fuentes de política mensual {si + 1}<textarea value={item.billing_month_policy.source_refs.join("\n")} onChange={e => { segment(si, { billing_month_policy: { ...item.billing_month_policy, source_refs: references(e.target.value) } }); }} /></label>
        <p>Histórico soportado: promedio de dos máximos mensuales distintos en doce meses.</p>
        <label>Quantum CLP {si + 1}<input required value={item.rounding_policy.quantum} onChange={e => { segment(si, { rounding_policy: { ...item.rounding_policy, quantum: e.target.value } }); }} /></label>
        <label>Precisión {si + 1}<input required type="number" min="50" max="128" value={item.rounding_policy.precision} onChange={e => { segment(si, { rounding_policy: { ...item.rounding_policy, precision: Number(e.target.value) } }); }} /></label>
        <label>Modo de redondeo {si + 1}<select value={item.rounding_policy.mode} onChange={e => { segment(si, { rounding_policy: { ...item.rounding_policy, mode: e.target.value as ProfileSegment['rounding_policy']['mode'] } }); }}>{["ROUND_HALF_UP", "ROUND_HALF_EVEN", "ROUND_DOWN", "ROUND_UP"].map(mode => <option key={mode}>{mode}</option>)}</select></label>
        <label>Etapa de redondeo {si + 1}<select value={item.rounding_policy.stage} onChange={e => { segment(si, { rounding_policy: { ...item.rounding_policy, stage: e.target.value as "component" | "total" } }); }}><option value="component">Por componente</option><option value="total">Al total, con ajuste visible</option></select></label>
        {item.charges.map((fee, ci) => <fieldset key={ci}><legend>Cargo {si + 1}.{ci + 1}</legend>
          <label>Código cargo {si + 1}.{ci + 1}<input required value={fee.code} onChange={e => { charge(si, ci, { code: e.target.value }); }} /></label>
          <label>Tipo cargo {si + 1}.{ci + 1}<select value={fee.kind} onChange={e => { charge(si, ci, { kind: e.target.value as Charge['kind'] }); }}>{kinds.map(kind => <option key={kind}>{kind}</option>)}</select></label>
          <label>Unidad cargo {si + 1}.{ci + 1}<select value={fee.quantity_unit} onChange={e => { charge(si, ci, { quantity_unit: e.target.value as Charge['quantity_unit'] }); }}>{["kWh", "kW", "cycle", "CLP"].map(unit => <option key={unit}>{unit}</option>)}</select></label>
          <label>Precio cargo {si + 1}.{ci + 1}<input value={fee.unit_price ?? ""} onChange={e => { charge(si, ci, { unit_price: e.target.value || null }); }} /></label>
          <label>Tributación cargo {si + 1}.{ci + 1}<select value={fee.tax_basis} onChange={e => { charge(si, ci, { tax_basis: e.target.value as Charge['tax_basis'] }); }}>{["neto", "impuesto_incluido", "impuesto_separado"].map(basis => <option key={basis}>{basis}</option>)}</select></label>
          <label>Vigencia cargo {si + 1}.{ci + 1}<select value={fee.vigency_strategy} onChange={e => { charge(si, ci, { vigency_strategy: e.target.value }); }}><option value="exact_intervals">Intervalos exactos</option><option value="cycle_once">Una vez por ciclo documentado</option></select></label>
          <label>Fuentes cargo {si + 1}.{ci + 1}<textarea value={fee.source_refs.join("\n")} onChange={e => { charge(si, ci, { source_refs: references(e.target.value) }); }} /></label>
          {fee.kind === "impuesto" && <label>Códigos netos gravados {si + 1}.{ci + 1}<input value={fee.tax_codes.join(",")} onChange={e => { charge(si, ci, { tax_codes: e.target.value.split(",").filter(Boolean) }); }} /></label>}
          <button type="button" onClick={() => { segment(si, { charges: item.charges.filter((_, i) => i !== ci) }); }}>Quitar cargo {si + 1}.{ci + 1}</button>
        </fieldset>)}
        <button type="button" onClick={() => { segment(si, { charges: [...item.charges, { code: "", kind: "energia", quantity_unit: "kWh", unit_price: null, tax_basis: "neto", applicability: "always", vigency_strategy: "exact_intervals", source_refs: [], tax_codes: [] }] }); }}>Añadir cargo al segmento {si + 1}</button>
        <button type="button" onClick={() => { patch({ segments: [...body.segments, structuredClone(item)] }); }}>Copiar segmento {si + 1}</button>
        <button type="button" onClick={() => { patch({ segments: body.segments.filter((_, i) => i !== si) }); }}>Quitar segmento {si + 1}</button>
      </fieldset>)}
      <button type="button" onClick={() => { patch({ segments: [...body.segments, emptySegment()] }); }}>Añadir segmento</button>
      <button type="submit">Confirmar nueva revisión de perfil</button>
    </fieldset>
    {operation.error && <p role="alert">{operation.error}</p>}
    {operation.conflict && <button type="button" onClick={() => { void reload(); }}>Revisar último calendario</button>}
    {error && <p role="alert">No se pudo revisar el perfil; se conserva el borrador.</p>}
  </form>;
}
