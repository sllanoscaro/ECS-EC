/**002 state/race regressions preserve exact server states and invalidate old grouped requests on retry/logout. */
import { act, cleanup, render, renderHook, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { consumptionApi, type AggregateQueryResult, type Granularity } from '../../src/lib/api/consumption';
import { clearPrivateData } from '../../src/lib/api/session';
import { useConsumptionQuery } from '../../src/components/consumption/useConsumptionQuery';
import { QueryState } from '../../src/components/consumption/QueryState';
import { EnergyTable } from '../../src/components/consumption/EnergyTable';
import { blocks } from './consumption/history-fixtures';

afterEach(() => { cleanup(); vi.restoreAllMocks(); });
const period = { start: blocks[0].start, end: blocks[1].end, timezone: 'America/Santiago' };
const result: AggregateQueryResult = { request_ref: 'test', building_id: 'test', category_id: 'CAT-05', period,
  granularity: 'hour', unit: 'kWh', cutoff_at: '2026-01-01T00:00:00Z', state: 'incomplete', source_mode: 'measured',
  configuration_segments: [], blocks, excluded_blocks: [], diagnostics: [], warnings: [], reason_code: null };

it('distinguishes loading/error/incomplete and the three exact temporal states', () => {
  const { rerender } = render(<QueryState loading error={null} data={null} retry={() => {}} />);
  expect(screen.getByRole('status').textContent).toContain('Consultando');
  rerender(<QueryState loading={false} error="Consulta fallida" data={null} retry={() => {}} />);
  expect(screen.getByRole('alert').textContent).toContain('Consulta fallida');
  rerender(<QueryState loading={false} error={null} data={result} retry={() => {}} />);
  expect(screen.getByRole('status').textContent).toBe('Datos incompletos');
  rerender(<EnergyTable rows={[]} blocks={[blocks[0], blocks[1], { ...blocks[1], start: '2026-01-01T02:00:00-03:00', temporal_state: 'ongoing' }]} categoryId="CAT-05" timezone={period.timezone} />);
  for (const name of ['Terminado', 'Aún no iniciado', 'En curso']) expect(screen.getByRole('cell', { name })).not.toBeNull();
});

it('keys grouped requests by granularity, retains B error after late A and clears retry on session expiry', async () => {
  const queue: { resolve: (data: AggregateQueryResult) => void; reject: (error: Error) => void }[] = [];
  vi.spyOn(consumptionApi, 'aggregates').mockImplementation(() => new Promise((resolve, reject) => queue.push({ resolve, reject })));
  const { result: query, rerender } = renderHook(({ granularity }) => useConsumptionQuery('CAT-05', period, consumptionApi.detail, granularity),
    { initialProps: { granularity: 'hour' as Granularity } });
  rerender({ granularity: 'day' });
  await act(async () => queue[1].reject(new Error('synthetic failure')));
  expect(query.current.error).toBeTruthy();
  await act(async () => queue[0].resolve(result));
  expect(query.current.data).toBeNull();
  act(() => query.current.retry());
  expect(consumptionApi.aggregates).toHaveBeenLastCalledWith('CAT-05', period, 'day', expect.any(AbortSignal));
  act(clearPrivateData);
  await act(async () => queue[2].resolve(result));
  expect(query.current.data).toBeNull();
});
