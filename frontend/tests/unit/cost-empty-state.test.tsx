import {cleanup,render,screen,fireEvent} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {CostsEmptyState} from '../../src/components/costs/CostsEmptyState';

const state=vi.hoisted(()=>({readiness:vi.fn(),permissions:[] as string[]}));
vi.mock('../../src/lib/api/costs',()=>({costsApi:{readiness:state.readiness}}));
vi.mock('../../src/components/identity/SessionProvider',()=>({useSession:()=>({session:{permissions:state.permissions}})}));
afterEach(()=>{cleanup();state.readiness.mockReset();state.permissions=[];});
it('explains each missing prerequisite without offering administrative actions to an operator',async()=>{
 state.readiness.mockResolvedValue({physical_general:false,supply_configured:false,profile_published:false});
 render(<CostsEmptyState/>);
 expect(await screen.findByText(/el total calculado de categorías no permite/)).toBeTruthy();
 expect(screen.getByText(/cargos, precios y vigencias/)).toBeTruthy();
 expect(screen.queryByRole('link',{name:'Configurar costos'})).toBeNull();
});
it('links an authorized administrator to the first calculation only when prerequisites exist',async()=>{
 state.permissions=['costs.calculations.create'];
 state.readiness.mockResolvedValue({physical_general:true,supply_configured:true,profile_published:true});
 render(<CostsEmptyState/>);
 expect((await screen.findByRole('link',{name:'Generar el primer cálculo'})).getAttribute('href')).toBe('/administracion/costos/');
 expect(screen.getByText(/mediciones físicas completas/)).toBeTruthy();
});
it('distinguishes diagnostic failure from missing configuration and supports retry',async()=>{
 state.readiness.mockRejectedValueOnce(new Error('offline')).mockResolvedValue({physical_general:false,supply_configured:false,profile_published:false});
 render(<CostsEmptyState/>);
 expect(await screen.findByRole('alert')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Reintentar configuración'}));
 expect(await screen.findByText(/el total calculado de categorías no permite/)).toBeTruthy();
 expect(state.readiness).toHaveBeenCalledTimes(2);
});
