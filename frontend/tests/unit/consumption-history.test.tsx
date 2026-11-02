/** Known wire blocks must appear identically in chart/table without browser aggregation. */
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { GranularitySelector } from '../../src/components/consumption/GranularitySelector';
import { EnergyChart } from '../../src/components/consumption/EnergyChart';
import { EnergyTable } from '../../src/components/consumption/EnergyTable';

afterEach(cleanup);

import { blocks } from "./consumption/history-fixtures";

it('selects all five granularities without editing period or category', () => {
  const change = vi.fn();
  render(<GranularitySelector value="detail" onChange={change} />);
  expect(screen.getAllByRole('option')).toHaveLength(5);
  fireEvent.change(screen.getByLabelText('Agrupación'), { target: { value: 'month' } });
  expect(change).toHaveBeenCalledWith('month');
});

it('keeps zero distinct from absence and shows exact coverage/temporal states in both views', () => {
  render(<><EnergyChart rows={[]} blocks={blocks} timezone="America/Santiago" />
    <EnergyTable rows={[]} blocks={blocks} categoryId="CAT-05" timezone="America/Santiago" /></>);
  expect(screen.getByRole('cell', { name: '0 kWh' })).not.toBeNull();
  expect(screen.getByRole('cell', { name: '—' })).not.toBeNull();
  expect(screen.getByRole('cell', { name: /<100 %/ })).not.toBeNull();
  const symbols = screen.getAllByRole('graphics-symbol');
  expect(symbols).toHaveLength(2);
  expect(symbols[0].getAttribute('data-kind')).toBe('zero');
  expect(symbols[1].getAttribute('data-kind')).toBe('gap');
  fireEvent.focus(symbols[1]);
  expect(screen.getByRole('tooltip').textContent).toContain('Aún no iniciado');
  expect(screen.getByRole('tooltip').textContent).toContain('Sin datos');
});

it('preserves the exact minimum and a very large aggregate in focused evidence', () => {
  const exact = [ { ...blocks[0], energy_kwh: '0.000000000000001' },
    { ...blocks[0], start: blocks[1].start, end: blocks[1].end, aggregate_id: 'large',
      energy_kwh: '10000000000000000000000000000000000000000000000000000000.000000000000001' } ];
  render(<><EnergyChart rows={[]} blocks={exact} timezone="America/Santiago" />
    <EnergyTable rows={[]} blocks={exact} categoryId="CAT-05" timezone="America/Santiago" /></>);
  for (const [index, block] of exact.entries()) {
    expect(screen.getByRole('cell', { name: `${block.energy_kwh} kWh` })).not.toBeNull();
    fireEvent.focus(screen.getAllByRole('graphics-symbol')[index]);
    expect(screen.getByRole('tooltip').textContent).toContain(`${block.energy_kwh} kWh`);
  }
});
