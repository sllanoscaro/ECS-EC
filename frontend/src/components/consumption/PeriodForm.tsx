/** Explicit local timestamps with offsets; invalid drafts never overwrite the last valid selection. */
"use client";
import { useState, type FormEvent } from "react";
import type { Period } from "../../lib/api/consumption";
import { instantMicros } from "./format";

/** Check local wall fields against the building IANA zone, independently of the browser's current zone. */
function validOffset(value: string, timezone: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(value)) return false;
  try {
    const parts = new Intl.DateTimeFormat("en-CA", { timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" }).formatToParts(new Date(value));
    const field = (name: string) => parts.find(part => part.type === name)?.value;
    return `${field("year")}-${field("month")}-${field("day")}T${field("hour")}:${field("minute")}:${field("second")}` === value.slice(0, 19);
  } catch { return false; }
}

/** Submit a valid explicit interval, retaining the user's draft and an explanation when invalid. */
export function PeriodForm({ period, onSubmit }: { period: Period; onSubmit: (period: Period) => void }) {
  const [start, setStart] = useState(period.start);
  const [end, setEnd] = useState(period.end);
  const [error, setError] = useState<string | null>(null);
  function submit(event: FormEvent) {
    /** Validate exact microsecond ordering; the authoritative server repeats all checks. */
    event.preventDefault();
    if (!validOffset(start, period.timezone) || !validOffset(end, period.timezone) || instantMicros(start) >= instantMicros(end)) {
      setError("Revise inicio y fin: use una hora existente con el offset del edificio e inicio anterior al fin."); return;
    }
    setError(null); onSubmit({ start, end, timezone: period.timezone });
  }
  return <form onSubmit={submit}><fieldset><legend>Período · {period.timezone} · [inicio, fin)</legend>
    <label>Inicio con offset<input required value={start} onChange={event => { setStart(event.target.value); }} /></label>
    <label>Fin con offset<input required value={end} onChange={event => { setEnd(event.target.value); }} /></label>
    <p>Use ISO 8601, por ejemplo 2026-01-01T00:00:00-03:00. En una hora repetida indique el offset elegido.</p>
    <button type="submit">Consultar período</button></fieldset>{error && <p role="alert">{error}</p>}</form>;
}
