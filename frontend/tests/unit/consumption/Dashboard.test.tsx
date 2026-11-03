/** Calendar refresh regressions: no polling, stable visible readings, manual recovery and timer cleanup. */
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { Dashboard } from '../../../src/components/consumption/Dashboard';
const { request } = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock('../../../src/lib/api/session', () => ({ apiRequest: request, sessionActivityHeaders: (kind: string) => ({ activity: kind }) }));
vi.mock('../../../src/components/identity/SessionProvider', () => ({ SessionGuard: ({ children }: { children: React.ReactNode }) => children }));
vi.mock('../../../src/components/identity/ApplicationFrame', () => ({ useBuildingTimezone: () => {} }));
vi.mock('../../../src/components/consumption/EnergyChart', () => ({ EnergyChart: ({ categoryId, points }: { categoryId: string; points: unknown }) => <div data-category={categoryId} data-points={JSON.stringify(points)}>Gráfico disponible</div> }));
const snapshot = {
  timezone: 'America/Santiago', cutoff_at: '2026-11-03T18:20:00-03:00',
  period: { start: '2026-11-03T00:00:00-03:00', end: '2026-11-04T00:00:00-03:00', timezone: 'America/Santiago' },
  categories: [{ id: 'CAT-01', name: 'Total', source_mode: 'calculated', base_categories: ['CAT-02'], energy_kwh: '123', coverage_percent: '98', covered_duration_us: '1', elapsed_duration_us: '2', last_reading_at: '2026-11-03T18:15:00-03:00', state: 'incomplete' }],
  series: [], chart_excluded_count: 0,
};
beforeEach(() => {
  vi.useFakeTimers(); vi.setSystemTime(new Date('2026-11-03T21:20:00Z'));
  request.mockReset().mockResolvedValue(snapshot);
});
afterEach(() => { cleanup(); vi.useRealTimers(); });
/** Finish promises produced by a fetch and its finally block without advancing calendar time. */
async function settle() { await act(async () => { await Promise.resolve(); }); }

it('fetches once at18:30:05 and18:45:05, never at five-second intervals', async () => {
  render(<Dashboard />); await settle();
  expect(request).toHaveBeenCalledTimes(1);
  await act(async () => { await vi.advanceTimersByTimeAsync(600000); });
  expect(request).toHaveBeenCalledTimes(1);
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(request).toHaveBeenCalledTimes(2);
  expect(request.mock.calls[1][1].headers.activity).toBe('background');
  await act(async () => { await vi.advanceTimersByTimeAsync(900000); });
  expect(request).toHaveBeenCalledTimes(3);
});

it('keeps chart and readings visible during a manual update and cancels the previous timer', async () => {
  let finish!: (value: typeof snapshot) => void;
  render(<Dashboard />); await settle();
  request.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  await act(async () => { await vi.advanceTimersByTimeAsync(300000); });
  fireEvent.click(screen.getByRole('button', { name: 'Actualizar' }));
  expect(screen.getByText('Gráfico disponible')).toBeTruthy();
  expect(screen.queryByText('Consultando el consumo del día…')).toBeNull();
  expect(request.mock.calls[1][1].headers.activity).toBe('interactive');
  await act(async () => { finish(snapshot); });
  await act(async () => { await vi.advanceTimersByTimeAsync(305000); });
  expect(request).toHaveBeenCalledTimes(3);
});

it('does not retry a failed scheduled fetch until the next quarter, and allows manual recovery', async () => {
  const view = render(<Dashboard />); await settle();
  request.mockRejectedValueOnce(new Error('unavailable'));
  await act(async () => { await vi.advanceTimersByTimeAsync(605000); });
  expect(screen.getByRole('alert')).toBeTruthy();
  expect(screen.getByText('Gráfico disponible')).toBeTruthy();
  await act(async () => { await vi.advanceTimersByTimeAsync(60000); });
  expect(request).toHaveBeenCalledTimes(2);
  fireEvent.click(screen.getByRole('button', { name: 'Actualizar' })); await settle();
  expect(request).toHaveBeenCalledTimes(3);
  expect(screen.queryByRole('alert')).toBeNull();
  view.unmount();
  await act(async () => { await vi.advanceTimersByTimeAsync(900000); });
  expect(request).toHaveBeenCalledTimes(3);
});

it('scales category bars against the daily total, including the largest partial', async () => {
  /** With100kWh total,60 and40kWh must occupy60% and40%, rather than100% and66.7%. */
  const total = { ...snapshot.categories[0], energy_kwh: '100' };
  request.mockResolvedValue({ ...snapshot, categories: [total,
    { ...total, id: 'CAT-03', name: 'Iluminación exterior', energy_kwh: '60' },
    { ...total, id: 'CAT-04', name: 'Iluminación interior', energy_kwh: '40' },
  ] });
  const { container } = render(<Dashboard />); await settle();
  const bars = container.querySelectorAll<HTMLElement>('.category-track > span');
  expect(bars[0].style.width).toBe('60%');
  expect(bars[1].style.width).toBe('40%');
});

it.each(['0', null])('does not display a full bar when the daily total is %s', async energy => {
  /** An unavailable denominator cannot imply that a category represents all daily energy. */
  const total = { ...snapshot.categories[0], energy_kwh: energy };
  request.mockResolvedValue({ ...snapshot, categories: [total,
    { ...total, id: 'CAT-03', name: 'Iluminación exterior', energy_kwh: '0' },
  ] });
  const { container } = render(<Dashboard />); await settle();
  expect(container.querySelector<HTMLElement>('.category-track > span')?.style.width).toBe('0%');
});

it('uses the requested coverage description and shows100% without an incomplete warning', async () => {
  /** A fully covered closed period must not be labelled incomplete because a new quarter is open. */
  request.mockResolvedValue({ ...snapshot, coverage_end_at: '2026-11-03T18:15:00-03:00', categories: [
    { ...snapshot.categories[0], coverage_percent: '100.00', state: 'available' },
  ] });
  render(<Dashboard />); await settle();
  expect(screen.getByText(/^100,0 %$/)).toBeTruthy();
  expect(screen.getByText('Porcentaje de intervalos registrados correctamente')).toBeTruthy();
  expect(screen.queryByText(/Datos incompletos: la cobertura/)).toBeNull();
});


it('selects exclusive category evidence, switches categories and restores the original total without fetching', async () => {
  /** Distinct series, including zero and null, must survive selection and background refresh. */
  const point = (energy_kwh: string | null) => ({ start: snapshot.period.start, end: '2026-11-03T00:15:00-03:00', energy_kwh, coverage_percent: '100' });
  const total = { ...snapshot.categories[0], series: [point('123')], chart_excluded_count: 0 };
  const exterior = { ...total, id: 'CAT-03', name: 'Iluminación exterior', series: [point('0'), point(null)] };
  const interior = { ...total, id: 'CAT-04', name: 'Iluminación interior', series: [point('40')], chart_excluded_count: 1 };
  request.mockResolvedValue({ ...snapshot, series: total.series, categories: [total, exterior, interior] });
  render(<Dashboard />); await settle();
  expect(screen.queryByRole('button', { name: 'Ver consumo total' })).toBeNull();
  const exteriorButton = screen.getByRole('button', { name: /Iluminación exterior/ });
  fireEvent.click(exteriorButton);
  expect(exteriorButton.getAttribute('aria-pressed')).toBe('true');
  expect(screen.getByText('Gráfico disponible').getAttribute('data-category')).toBe('CAT-03');
  expect(JSON.parse(screen.getByText('Gráfico disponible').getAttribute('data-points')!)).toEqual(exterior.series);
  fireEvent.click(screen.getByRole('button', { name: /Iluminación interior/ }));
  expect(exteriorButton.getAttribute('aria-pressed')).toBe('false');
  expect(screen.getByText('Gráfico disponible').getAttribute('data-category')).toBe('CAT-04');
  expect(screen.getByText(/Hay lecturas que no caben/)).toBeTruthy();
  await act(async () => { await vi.advanceTimersByTimeAsync(605000); });
  expect(screen.getByText('Gráfico disponible').getAttribute('data-category')).toBe('CAT-04');
  fireEvent.click(screen.getByRole('button', { name: 'Ver consumo total' }));
  expect(screen.getByText('Gráfico disponible').getAttribute('data-category')).toBe('CAT-01');
  expect(JSON.parse(screen.getByText('Gráfico disponible').getAttribute('data-points')!)).toEqual(total.series);
  expect(screen.queryByRole('button', { name: 'Ver consumo total' })).toBeNull();
  expect(screen.queryByText(/Hay lecturas que no caben/)).toBeNull();
  expect(request).toHaveBeenCalledTimes(2);
});

it('allows selecting a category without a meter without substituting total readings', async () => {
  /** Empty evidence remains empty while the return control stays available. */
  request.mockResolvedValue({ ...snapshot, categories: [snapshot.categories[0], {
    ...snapshot.categories[0], id: 'CAT-07', name: 'Ascensores', state: 'no_meter', energy_kwh: null, series: [], chart_excluded_count: 0,
  }] });
  render(<Dashboard />); await settle();
  fireEvent.click(screen.getByRole('button', { name: /Ascensores/ }));
  expect(screen.getByText('Gráfico disponible').getAttribute('data-category')).toBe('CAT-07');
  expect(screen.getByText('Gráfico disponible').getAttribute('data-points')).toBe('[]');
  expect(screen.getByText('Sin medidor para esta categoría.').getAttribute('role')).toBe('status');
  expect(screen.getByRole('button', { name: 'Ver consumo total' })).toBeTruthy();
});


it('rounds summary, coverage and category figures to one decimal', async () => {
  /** Decimal half-up rounding is presentation only; source values still drive geometry. */
  const total = { ...snapshot.categories[0], energy_kwh: '123.45', coverage_percent: '98.76' };
  request.mockResolvedValue({ ...snapshot, categories: [total, { ...total, id: 'CAT-03', name: 'Iluminación exterior', energy_kwh: '12.35' }] });
  render(<Dashboard />); await settle();
  expect(screen.getByText('123,5 kWh')).toBeTruthy();
  expect(screen.getByText('98,8 %')).toBeTruthy();
  expect(screen.getByRole('button', { name: /Iluminación exterior/ }).textContent).toContain('12,4');
});


it('orders categories by exact descending consumption with zero before missing data and preserves selection after refresh', async () => {
  /** Values that round identically or exceed Number precision must keep their exact ordering. */
  const category = (id: string, name: string, energy_kwh: string | null) => ({ ...snapshot.categories[0], id, name, energy_kwh });
  request.mockResolvedValue({ ...snapshot, categories: [snapshot.categories[0],
    category('CAT-02', 'Sin datos HVAC', null), category('CAT-03', 'Exterior', '99999999999999999999.11'),
    category('CAT-04', 'Interior', '99999999999999999999.12'), category('CAT-05', 'Enchufes', '0'),
    category('CAT-06', 'Sanitario', '0.02'), category('CAT-07', 'Ascensores', null),
  ] });
  const { container } = render(<Dashboard />); await settle();
  expect([...container.querySelectorAll('.category-label>span')].map(el => el.textContent)).toEqual([
    'Interior', 'Exterior', 'Sanitario', 'Enchufes', 'Sin datos HVAC', 'Ascensores',
  ]);
  fireEvent.click(screen.getByRole('button', { name: /Exterior/ }));
  fireEvent.click(screen.getByRole('button', { name: 'Actualizar' })); await settle();
  expect(screen.getByRole('button', { name: /Exterior/ }).getAttribute('aria-pressed')).toBe('true');
});
