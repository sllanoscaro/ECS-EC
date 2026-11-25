/**008 meaningful rule editor checks: applicable fields, registered recipients and safe conflicts with input preserved. */
import React from 'react';
import '@testing-library/jest-dom/vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {afterEach,test,expect,vi} from 'vitest';
import {RuleEditor} from '../../src/components/notifications/RuleEditor';
import {notificationsApi,type Catalog,type Rule} from '../../src/lib/api/notifications';
import {Problem} from '../../src/lib/api/session';
vi.mock('../../src/lib/api/notifications',()=>({notificationsApi:{save:vi.fn(),preview:vi.fn(),activate:vi.fn(),pause:vi.fn(),versions:vi.fn()}}));
afterEach(()=>{cleanup();vi.clearAllMocks();});
const account='00000000-0000-0000-0000-000000000008';
const catalog:Catalog={periodic_content_types:['recepcion','calidad','cambios_administrativos'],urgent_event_types:['recepcion_rechazada','calculo_fallido','pdf_fallido'],categories:['CAT-01'],required_permissions:[]};
const recipient={id:account,display_name:'operator@example.test',current_email:'operator@example.test',role:'operador' as const,eligible:true,reason_code:null};
/**Mount one real editor; server mocks are explicit transport boundaries, not claims of integration acceptance. */
function mount(current?:Rule){return render(<RuleEditor current={current} catalog={catalog} recipients={[recipient]} categories={[{id:'CAT-01',name:'Total',scope:'Base configurada',has_meter:false,source_mode:'calculated',base_categories:['CAT-03','CAT-05'],category_revision:1}]} timezone="America/Santiago" onSaved={vi.fn()} onReload={vi.fn()}/>);}

test('daily06:00 uses a registered account and saves inactive without silently activating',async()=>{
 /**The editor submits exact server vocabulary and retains its action key through an uncertain response. */
 vi.mocked(notificationsApi.save).mockRejectedValueOnce(new Error('connection lost')).mockResolvedValueOnce({id:account} as Rule);
 mount();fireEvent.change(screen.getByLabelText('Nombre de la regla'),{target:{value:'Corte diario'}});fireEvent.click(screen.getByRole('checkbox',{name:/operator@example.test/}));
 fireEvent.click(screen.getByRole('button',{name:'Guardar regla'}));await screen.findByRole('alert');
 fireEvent.click(screen.getByRole('button',{name:'Guardar regla'}));await waitFor(()=>expect(notificationsApi.save).toHaveBeenCalledTimes(2));
 const [body,key]=vi.mocked(notificationsApi.save).mock.calls[0];expect(body.mode).toBe('periodica');if(body.mode==='periodica')expect(body.schedule).toMatchObject({kind:'diaria',local_time:'06:00'});expect(body.recipient_ids).toEqual([account]);expect(vi.mocked(notificationsApi.save).mock.calls[1][1]).toBe(key);expect(notificationsApi.activate).not.toHaveBeenCalled();
});

test('administrative content prevents choosing an operator while allowing explicit removal',()=>{
 /**Changing content cannot trap an ineligible already selected recipient in a disabled checked box. */
 mount();const accountBox=screen.getByRole('checkbox',{name:/operator@example.test/});fireEvent.click(accountBox);fireEvent.click(screen.getByRole('checkbox',{name:'Cambios administrativos'}));expect(accountBox).not.toBeDisabled();fireEvent.click(accountBox);expect(accountBox).toBeDisabled();
});

test('urgent variants discard periodic fields and show calculated source basis',()=>{
 /**Consumption evidence belongs to the actual source; no binary conversion or second CAT01 sum enters the draft. */
 mount();fireEvent.change(screen.getByLabelText('Modalidad'),{target:{value:'urgente'}});expect(screen.getByText(/calculado · base CAT-03, CAT-05/)).toBeTruthy();expect(screen.queryByLabelText('Hora local')).toBeNull();expect(screen.getByLabelText('Umbral (kWh)')).toHaveValue('100');fireEvent.change(screen.getByLabelText('Condición'),{target:{value:'ausencia_datos'}});expect(screen.getByLabelText('Silencio máximo (minutos)')).toHaveAttribute('min','15');expect(screen.queryByLabelText('Umbral (kWh)')).toBeNull();
});

test('a conflict preserves entered name and offers explicit reload',async()=>{
 /**No mutation is automatically repeated against a newer revision or silently overwrites a user draft. */
 const current={id:account,revision:2,status:'pausada',version_number:1,current_version_id:account,next_due_at:null,created_at:'2026-01-01T00:00:00Z',updated_at:'2026-01-01T00:00:00Z',effective_content_types:['recepcion'],config:{name:'Original',mode:'periodica',timezone:'America/Santiago',recipient_ids:[account],content_types:['recepcion'],schedule:{kind:'diaria',starts_at:'2026-01-01T00:00:00Z',local_time:'06:00'}}} as Rule;
 vi.mocked(notificationsApi.save).mockRejectedValue(new Problem(412,'revision_conflict','Conflict'));mount(current);fireEvent.change(screen.getByLabelText('Nombre de la regla'),{target:{value:'Entrada preservada'}});fireEvent.click(screen.getByRole('button',{name:'Guardar revisión'}));await screen.findByRole('alert');expect(screen.getByLabelText('Nombre de la regla')).toHaveValue('Entrada preservada');expect(screen.getByRole('button',{name:'Recargar versión vigente'})).toBeTruthy();
});
