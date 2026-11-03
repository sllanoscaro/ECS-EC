/** Friendly wall-time filters retain explicit IANA/offset validation, including DST ambiguity. */
"use client";
import { useState, type FormEvent } from 'react';
import type { Catalog, CategoryId, Period } from '../../lib/api/consumption';
import { CategorySelector } from './CategorySelector';
import { instantMicros } from './format';
import { wallCandidates, wallValue } from './wallTime';

/** Submit only existing wall instants; expose both offsets of repeated hours without discarding precision. */
export function ConsumptionFilters({ catalog, category, period, choose, apply }: {
  catalog: Catalog; category: CategoryId; period: Period; choose: (value: CategoryId) => void; apply: (value: Period) => void;
}) {
  const [start, setStart] = useState(wallValue(period.start));
  const [end, setEnd] = useState(wallValue(period.end));
  const [startChoice, setStartChoice] = useState(period.start);
  const [endChoice, setEndChoice] = useState(period.end);
  const [error, setError] = useState('');
  const starts = wallCandidates(start, period.timezone), ends = wallCandidates(end, period.timezone);
  /** Retain invalid drafts and the previous query; no implicit correction of nonexistent local times. */
  function submit(event: FormEvent) {
    event.preventDefault();
    const lower = starts.length === 1 ? starts[0] : starts.find(v => v === startChoice);
    const upper = ends.length === 1 ? ends[0] : ends.find(v => v === endChoice);
    if (!lower || !upper || instantMicros(lower) >= instantMicros(upper)) { setError('Revise las fechas y horas. Desde debe ser anterior a Hasta; en una hora repetida elija el desfase.'); return; }
    setError(''); apply({ start: lower, end: upper, timezone: period.timezone });
  }
  return <><form className="consumption-filters panel" onSubmit={submit}>
    <CategorySelector categories={catalog.categories} value={category} onChange={choose} />
    <label>Desde<input required type="datetime-local" step="0.000001" value={start} onChange={e => { setStart(e.target.value); setStartChoice(''); }} />{starts.length > 1 && <select aria-label="Desfase de Desde" value={startChoice} onChange={e => setStartChoice(e.target.value)}><option value="">Seleccione desfase</option>{starts.map(value => <option key={value} value={value}>{value.slice(-6)}</option>)}</select>}</label>
    <label>Hasta<input required type="datetime-local" step="0.000001" value={end} onChange={e => { setEnd(e.target.value); setEndChoice(''); }} />{ends.length > 1 && <select aria-label="Desfase de Hasta" value={endChoice} onChange={e => setEndChoice(e.target.value)}><option value="">Seleccione desfase</option>{ends.map(value => <option key={value} value={value}>{value.slice(-6)}</option>)}</select>}</label>
    <button className="primary-button" type="submit">Consultar</button>
  </form>{error && <p className="notice notice--error" role="alert">{error}</p>}</>;
}
