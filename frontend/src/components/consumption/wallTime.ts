/** Exact local wall-time resolution; never assume the browser's zone or a fixed Santiago offset. */
import { instantMicros } from './format';
/** Preserve fractional seconds while removing only the explicit offset for native inputs. */
export function wallValue(value: string) { return value.replace(/(?:Z|[+-]\d{2}:\d{2})$/, ''); }
/** Enumerate round-tripping offsets around a local wall date; missing hours return no candidates. */
export function wallCandidates(wall: string, timezone: string): string[] {
  if (!/^\d{4}-\d\d-\d\dT\d\d:\d\d(?::\d\d(?:\.\d{1,6})?)?$/.test(wall)) return [];
  const normalized = wall.length === 16 ? wall + ':00' : wall;
  const guess = Date.parse(normalized + 'Z');
  if (!Number.isFinite(guess)) return [];
  const formatter = new Intl.DateTimeFormat('en-CA', { timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' });
  const offsets = new Set<number>();
  for (let hour = -36; hour <= 36; hour += 6) {
    const at = new Date(guess + hour * 3600000);
    const parts = formatter.formatToParts(at);
    const get = (type: string) => parts.find(p => p.type === type)!.value;
    const wallMs = Date.parse(`${get('year')}-${get('month')}-${get('day')}T${get('hour')}:${get('minute')}:${get('second')}Z`);
    offsets.add(Math.round((wallMs - Math.floor(at.getTime() / 1000) * 1000) / 60000));
  }
  return [...offsets].flatMap(offset => {
    const suffix = `${offset >= 0 ? '+' : '-'}${String(Math.floor(Math.abs(offset) / 60)).padStart(2, '0')}:${String(Math.abs(offset) % 60).padStart(2, '0')}`;
    const value = normalized + suffix;
    const parts = formatter.formatToParts(new Date(value));
    const get = (type: string) => parts.find(p => p.type === type)!.value;
    return `${get('year')}-${get('month')}-${get('day')}T${get('hour')}:${get('minute')}:${get('second')}` === normalized.slice(0, 19) ? [value] : [];
  }).sort((a, b) => instantMicros(a) < instantMicros(b) ? -1 : 1);
}
