import { act, cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { EnergyDistribution } from '../../src/components/costs/EnergyDistribution';
import type { EnergyDistribution as Distribution } from '../../src/lib/api/costs';
import type { CalculationDetail } from '../../src/lib/api/costs';
import { CostsConsultation } from '../../src/components/costs/CostsConsultation';

const request = vi.hoisted(() => vi.fn());
vi.mock('../../src/lib/api/costs', () => ({costsApi:{distribution:request}}));
vi.mock('../../src/components/costs/FinancialPanel', () => ({FinancialPanel:() => null}));
vi.mock('../../src/components/costs/CostHistory', () => ({CostHistory:() => null}));

afterEach(cleanup);
const data: Distribution = { calculation_id:'one', cutoff_at:'2026-11-02T12:00:00Z', state:'available', reason_code:null,
  energy_amount:'100000', other_amount:'42800', unassigned_amount:'60000', unassigned_percent:'60',
  categories:[{ id:'CAT-02', name:'HVAC y agua caliente sanitaria', state:'available', energy_kwh:'400', percent:'40', estimated_amount:'40000' },
    {id:'CAT-07',name:'Ascensores',state:'no_meter',energy_kwh:null,percent:null,estimated_amount:null}] };
it('shows exact CLP, percentages and the unassigned balance without fabricating an unmetered category', () => {
  render(<EnergyDistribution data={data} busy={false} error={false} retry={vi.fn()} timezone="America/Santiago" />);
  expect(screen.getByRole('cell', {name:'$40.000'})).toBeTruthy();
  expect(screen.getByRole('cell', {name:'40 %'})).toBeTruthy();
  expect(screen.getByRole('cell', {name:'Sin medidor'})).toBeTruthy();
  expect(screen.getByRole('rowheader', {name:'Sin asignar a categorías'})).toBeTruthy();
  expect(screen.getByText(/No incluye demanda/)).toBeTruthy();
});
it('withholds pie geometry and amounts on inconsistent or incomplete evidence', () => {
  const view = render(<EnergyDistribution data={{...data,state:'unavailable',reason_code:'categories_exceed_general',categories:data.categories.map(row => ({...row,percent:null,estimated_amount:null}))}}
    busy={false} error={false} retry={vi.fn()} timezone="America/Santiago" />);
  expect(screen.getByRole('status').textContent).toContain('supera el consumo del medidor general');
  expect(view.container.querySelectorAll('circle[stroke-dasharray]').length).toBe(0);
  expect(screen.queryByRole('cell',{name:'$40.000'})).toBeNull();
});

it('keeps fractional percentages exact in the table while shortening labels inside the ring',()=>{
 const view=render(<EnergyDistribution data={{...data,unassigned_percent:'58.03',categories:[{...data.categories[0],percent:'41.97'}]}}
   busy={false} error={false} retry={vi.fn()} timezone="America/Santiago"/>);
 expect(screen.getByRole('cell',{name:'41,97 %'})).toBeTruthy();
 const labels=[...view.container.querySelectorAll('.cost-donut text')].map(text=>text.textContent);
 expect(labels).toContain('42 %');expect(labels).toContain('58 %');
 expect(labels).not.toContain('58,03 %');
});

it('aborts the old request and never combines a new calculation with stale distribution amounts', async () => {
  let resolveOld!: (value:Distribution) => void;
  let resolveNew!: (value:Distribution) => void;
  request.mockReset().mockImplementationOnce(() => new Promise(resolve => {resolveOld=resolve;}))
    .mockImplementationOnce(() => new Promise(resolve => {resolveNew=resolve;}));
  const calculation = {id:'one',cycle_id:'cycle',revision:1,complete_total:'0',available_subtotal:'0',net_total:null,
    temporal_state:'cerrado',execution_state:'completado',sufficiency:'completo',cutoff_at:data.cutoff_at,
    components:[],monthly_maxima:[],reason_codes:[],snapshot:{cutoff_at:data.cutoff_at,request:{start:'2026-10-01T00:00:00Z',end:'2026-11-01T00:00:00Z',timezone:'America/Santiago'},
      supply:{general_board_ref:'Test',document_refs:[],measurement_point_differences:[]}}} as unknown as CalculationDetail;
  const props = {page:null,busy:false,error:'',refresh:vi.fn(),choose:vi.fn()};
  const view=render(<CostsConsultation {...props} selected={calculation} />);
  await waitFor(() => expect(request).toHaveBeenCalledTimes(1));
  const signal = request.mock.calls[0][1] as AbortSignal;
  view.rerender(<CostsConsultation {...props} selected={{...calculation,id:'two'}} />);
  await waitFor(() => expect(request).toHaveBeenCalledTimes(2));
  expect(signal.aborted).toBe(true);
  await act(async () => resolveOld(data));
  expect(screen.queryByRole('cell',{name:'$40.000'})).toBeNull();
  expect(screen.getByRole('status').textContent).toContain('Consultando el consumo');
  await act(async () => resolveNew({...data,calculation_id:'two',energy_amount:'50000',categories:[]}));
  expect(screen.getByRole('cell',{name:'$50.000'})).toBeTruthy();
});
