/** Draft filters apply atomically on submit; minute controls retain untouched exact boundaries. */
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { ConsumptionFilters } from '../../../src/components/consumption/ConsumptionFilters';
import type { Catalog } from '../../../src/lib/api/consumption';
afterEach(cleanup);
const period = {start:'2026-01-01T00:00:12.123456-03:00', end:'2026-01-02T00:00:34.654321-03:00', timezone:'America/Santiago'};
const catalog: Catalog = {building_id:'synthetic', timezone:period.timezone, cutoff_at:period.end, default_period:period, categories: [{id:'CAT-01' as const,name:'Total'}, {id:'CAT-05' as const,name:'Enchufes'}].map(category => ({...category,scope:'Edificio sintético',has_meter:true,source_mode:'measured' as const,base_categories:[],category_revision:1}))};

it('shows minutes and leaves category edits unapplied until Consultar, retaining original boundary precision', () => {
  const apply = vi.fn();
  render(<ConsumptionFilters catalog={catalog} category="CAT-01" period={period} apply={apply} />);
  expect((screen.getByLabelText('Desde') as HTMLInputElement).value).toBe('2026-01-01T00:00');
  expect(screen.getByLabelText('Desde').getAttribute('step')).toBe('60');
  expect((screen.getByLabelText('Hasta') as HTMLInputElement).value).toBe('2026-01-02T00:00');
  fireEvent.change(screen.getByLabelText('Categoría'), {target:{value:'CAT-05'}});
  expect(apply).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Consultar'}));
  expect(apply).toHaveBeenCalledExactlyOnceWith('CAT-05',period);
});
it('edits a minute boundary with zero seconds while preserving the untouched end', () => {
  const apply = vi.fn();
  render(<ConsumptionFilters catalog={catalog} category="CAT-01" period={period} apply={apply} />);
  fireEvent.change(screen.getByLabelText('Desde'), {target:{value:'2026-01-01T01:15'}});
  fireEvent.click(screen.getByRole('button',{name:'Consultar'}));
  expect(apply).toHaveBeenCalledWith('CAT-01',{...period,start:'2026-01-01T01:15:00-03:00'});
});
it('requires an explicit offset after editing a repeated minute and rejects a missing local hour', () => {
  const apply = vi.fn();
  render(<ConsumptionFilters catalog={catalog} category="CAT-01" period={{...period,start:'2026-04-04T22:00:00-03:00',end:'2026-09-07T01:00:00-03:00'}} apply={apply} />);
  fireEvent.change(screen.getByLabelText('Desde'), {target:{value:'2026-04-04T23:30'}});
  fireEvent.click(screen.getByRole('button',{name:'Consultar'}));
  expect(apply).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText('Desfase de Desde'), {target:{value:'2026-04-04T23:30:00-04:00'}});
  fireEvent.click(screen.getByRole('button',{name:'Consultar'}));
  expect(apply.mock.calls[0][1].start).toBe('2026-04-04T23:30:00-04:00');
  apply.mockClear();
  fireEvent.change(screen.getByLabelText('Desde'), {target:{value:'2026-09-06T00:30'}});
  fireEvent.click(screen.getByRole('button',{name:'Consultar'}));
  expect(apply).not.toHaveBeenCalled();
});
