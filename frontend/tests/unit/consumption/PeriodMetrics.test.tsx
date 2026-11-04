/** Period statistics use the same available values as the table, preserving exact arithmetic. */
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, it } from 'vitest';
import { periodMetrics } from '../../../src/components/consumption/periodMetrics';
import { PeriodMetrics } from '../../../src/components/consumption/PeriodMetrics';
import type { AggregateQueryResult } from '../../../src/lib/api/consumption';
import { blocks } from './history-fixtures';
afterEach(cleanup);

it('includes measured zero and excludes missing evidence from sum, extrema and mean', () => {
  expect(periodMetrics(['0', '10', '20', null].map(energy_kwh => ({energy_kwh})))).toEqual({ maximum: '20', minimum: '0', mean: '10', sum: '30', count: 3 });
  expect(periodMetrics([{energy_kwh:null}])).toEqual({ maximum:null, minimum:null, mean:null, sum:null, count:0 });
});
it('preserves sum carry above ambient decimal precision and at the smallest supported energy', () => {
  expect(periodMetrics([{energy_kwh:'999999999999999999999999999999.999999999999999'}, {energy_kwh:'0.000000000000001'}])).toEqual({maximum:'999999999999999999999999999999.999999999999999', minimum:'0.000000000000001', sum:'1000000000000000000000000000000', mean:'500000000000000000000000000000', count:2});
});
it('labels grouped arithmetic and available evidence without treating a null block as zero', () => {
  render(<PeriodMetrics data={{blocks} as AggregateQueryResult} />);
  expect(screen.getByText('Media por bloque')).toBeTruthy();
  expect(screen.getByText('Bloques con datos').nextElementSibling?.textContent).toBe('1');
  expect(screen.getAllByText('0,0')).toHaveLength(4);
});
it('uses dashes for missing energy and a zero count when no readings are available', () => {
  render(<PeriodMetrics data={{blocks:[]} as unknown as AggregateQueryResult} />);
  expect(screen.getAllByText('—')).toHaveLength(4);
  expect(screen.getByText('Bloques con datos').nextElementSibling?.textContent).toBe('0');
});
