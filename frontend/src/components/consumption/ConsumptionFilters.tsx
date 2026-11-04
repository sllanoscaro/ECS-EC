/** Friendly wall-time filters retain explicit IANA/offset validation, including DST ambiguity. */
"use client";
import { useState, type FormEvent } from 'react';
import type { Catalog, CategoryId, Period } from '../../lib/api/consumption';
import { CategorySelector } from './CategorySelector';
import { instantMicros } from './format';
import { wallCandidates, wallValue } from './wallTime';

/** Submit only existing wall instants; expose both offsets of repeated hours without discarding precision. */
export function ConsumptionFilters({ catalog, category, period, apply }: {
  catalog: Catalog; category: CategoryId; period: Period; apply: (category: CategoryId, value: Period) => void;
}) {
  const [draftCategory, setDraftCategory] = useState(category);
  const [start, setStart] = useState(wallValue(period.start).slice(0, 16));
  const [end, setEnd] = useState(wallValue(period.end).slice(0, 16));
  const [startChoice, setStartChoice] = useState(period.start);
  const [endChoice, setEndChoice] = useState(period.end);
  const [error, setError] = useState('');
  const starts = wallCandidates(start, period.timezone), ends = wallCandidates(end, period.timezone);
  /** Retain invalid drafts and the previous query; no implicit correction of nonexistent local times. */
  function submit(event: FormEvent) {
    event.preventDefault();
    // Untouched minute controls retain the original exact boundary, including fractional seconds.
    const lower = start === wallValue(period.start).slice(0, 16) && startChoice === period.start ? period.start : starts.length === 1 ? starts[0] : starts.find(v => v === startChoice);
    const upper = end === wallValue(period.end).slice(0, 16) && endChoice === period.end ? period.end : ends.length === 1 ? ends[0] : ends.find(v => v === endChoice);
    if (!lower || !upper || instantMicros(lower) >= instantMicros(upper)) { setError('Revise las fechas y horas. Desde debe ser anterior a Hasta; en una hora repetida elija el desfase.'); return; }
    setError(''); apply(draftCategory, { start: lower, end: upper, timezone: period.timezone });
  }
  return <><form className="consumption-filters panel" onSubmit={submit}>
    <CategorySelector categories={catalog.categories} value={draftCategory} onChange={setDraftCategory} />
    <label>Desde<input required type="datetime-local" step="60" value={start} onChange={e => { setStart(e.target.value); setStartChoice(''); }} />{starts.length > 1 && <select aria-label="Desfase de Desde" value={starts.find(value => value.slice(-6) === startChoice.slice(-6)) ?? ''} onChange={e => setStartChoice(e.target.value)}><option value="">Seleccione desfase</option>{starts.map(value => <option key={value} value={value}>{value.slice(-6)}</option>)}</select>}</label>
    <label>Hasta<input required type="datetime-local" step="60" value={end} onChange={e => { setEnd(e.target.value); setEndChoice(''); }} />{ends.length > 1 && <select aria-label="Desfase de Hasta" value={ends.find(value => value.slice(-6) === endChoice.slice(-6)) ?? ''} onChange={e => setEndChoice(e.target.value)}><option value="">Seleccione desfase</option>{ends.map(value => <option key={value} value={value}>{value.slice(-6)}</option>)}</select>}</label>
    <button className="primary-button" type="submit">Consultar</button>
  </form>{error && <p className="notice notice--error" role="alert">{error}</p>}</>;
}
