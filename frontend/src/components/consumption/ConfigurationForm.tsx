/** Consumption-only installation form; its route must be mounted under006's current administrative permission. */
"use client";

import { useState, type FormEvent } from "react";
import { consumptionApi, type Category, type CategoryId, type Configuration, type ConfigurationInput, type SourceEntry } from "../../lib/api/consumption";
import { Problem } from "../../lib/api/session";

/** Predict source changes for explanation only; the server derives and validates all actual revisions. */
function signature(entries: readonly SourceEntry[], category: CategoryId): string {
  const entry = entries.find(item => item.category_id === category);
  if (entry?.has_meter) return `measured:${entry.source_id}`;
  if (category !== "CAT-01") return "unavailable";
  const basis = entries.filter(item => item.category_id !== "CAT-01" && item.has_meter)
    .map(item => `${item.category_id}:${item.source_id}`).sort();
  return basis.length ? `calculated:${basis.join(",")}` : "unavailable";
}

/** Edit seven physical sources while preserving drafts on conflict/dependency errors; callbacks perform authorized IO. */
export function ConfigurationForm({ configuration, timezone, categories, save = consumptionApi.configure, reload = consumptionApi.configuration }: {
  configuration: Configuration | null; timezone: string; categories: readonly Category[];
  save?: (input: ConfigurationInput) => Promise<Configuration>; reload?: () => Promise<Configuration>;
}) {
  const [current, setCurrent] = useState(configuration);
  const [zone, setZone] = useState(configuration?.timezone ?? timezone);
  const [effective, setEffective] = useState("");
  const [entries, setEntries] = useState<SourceEntry[]>(categories.map(category => {
    /** Select only writable fields so server-derived metadata never becomes editable state. */
    const entry = configuration?.categories.find(item => item.category_id === category.id);
    return { category_id: category.id, has_meter: entry?.has_meter ?? false,
      source_id: entry?.source_id ?? null, source_label: entry?.source_label ?? null };
  }));
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);
  const changed = categories.filter(category => !current || signature(current.categories, category.id) !== signature(entries, category.id)).map(category => category.id);
  const basis = entries.filter(entry => entry.category_id !== "CAT-01" && entry.has_meter).map(entry => entry.category_id);

  /** Update a single writable entry; removing a meter clears both source fields rather than inventing defaults. */
  function edit(category: CategoryId, update: Partial<SourceEntry>) {
    setEntries(previous => previous.map(entry => entry.category_id === category ? { ...entry, ...update } : entry));
  }
  /** Apply a confirmed response, clearing only stale status while preserving the server's current revision. */
  function accept(value: Configuration) {
    setCurrent(value); setZone(value.timezone); setEffective("");
    setEntries(value.categories.map(({ category_id, has_meter, source_id, source_label }) => ({ category_id, has_meter, source_id, source_label })));
    setConflict(false); setError(null);
  }
  /** Submit full explicit configuration; errors retain all edits and never pretend a503 means empty history. */
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null); setMessage(null); setConflict(false);
    try {
      const value = await save({ expected_revision: current?.revision ?? 0,
        effective_from: current ? null : effective, timezone: zone, categories: entries });
      accept(value); setMessage(`Configuración guardada. Revisión ${value.revision}.`);
    } catch (failure) {
      setError(failure instanceof Problem ? failure.message : "No se pudo guardar la configuración.");
      setConflict(failure instanceof Problem && failure.status === 409);
    } finally { setBusy(false); }
  }
  /** Reload only on explicit conflict action, retaining edits if that authorized read also fails. */
  async function refresh() {
    setBusy(true);
    try { accept(await reload()); setMessage("Configuración actual recargada."); }
    catch { setError("No se pudo recargar la configuración."); }
    finally { setBusy(false); }
  }
  return <form onSubmit={submit}>
    <h2>Configuración de consumo</h2>
    {current && <p>Revisión actual: {current.revision}. Los cambios rigen al aplicar; se conserva la historia.</p>}
    <fieldset disabled={busy}>
      <legend>Contexto y fuentes</legend>
      <label>Zona IANA del edificio<input required value={zone} onChange={event => { setZone(event.target.value); }} /></label>
      {!current && <label>Vigencia inicial (ISO 8601 con offset)<input required value={effective} onChange={event => { setEffective(event.target.value); }} placeholder="2026-01-01T00:00:00-03:00" /></label>}
      {categories.map(category => {
        /** Keep every category configurable, including an absent total and an entirely empty basis. */
        const entry = entries.find(item => item.category_id === category.id)!;
        return <fieldset key={category.id}><legend>{category.id} · {category.name}</legend>
          <label><input type="checkbox" checked={entry.has_meter} onChange={event => { edit(category.id, event.target.checked ? { has_meter: true } : { has_meter: false, source_id: null, source_label: null }); }} />Con medidor {category.id}</label>
          {entry.has_meter && <>
            <label>Fuente UUID {category.id}<input required pattern="[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}" value={entry.source_id ?? ""} onChange={event => { edit(category.id, { source_id: event.target.value }); }} /></label>
            <label>Etiqueta {category.id}<input required maxLength={200} value={entry.source_label ?? ""} onChange={event => { edit(category.id, { source_label: event.target.value }); }} /></label>
          </>}
        </fieldset>;
      })}
      <p>{entries.find(entry => entry.category_id === "CAT-01")?.has_meter ? "Total medido: se usa exclusivamente su fuente." : basis.length ? `Total calculado de las categorías presentes. Base: ${basis.join(", ")}` : "Sin datos: no hay categorías presentes para calcular el total."}</p>
      <p>{changed.length ? `Cambios de fuente previstos: ${changed.join(", ")}` : "Sin cambios de fuente previstos."}</p>
      <p>Las revisiones de categoría y la base efectiva las confirma el servidor. Una etiqueta no cambia la fuente.</p>
      <button type="submit">Guardar configuración</button>
    </fieldset>
    {message && <p role="status">{message}</p>}{error && <p role="alert">{error}</p>}
    {conflict && <button type="button" disabled={busy} onClick={() => { void refresh(); }}>Recargar configuración actual</button>}
  </form>;
}
