/**005 result lifecycle keeps the stored identity/file and never offers a failed or pending binary. */
import React from 'react';
import {afterEach,expect,test,vi} from 'vitest';
import {cleanup,render,screen,fireEvent,waitFor} from '@testing-library/react';
import {ReportStatus} from '../../src/components/reports/ReportStatus';
import {ReportForm} from '../../src/components/reports/ReportForm';
import {createReport} from '../../src/lib/api/reports';
import type {Report} from '../../src/lib/api/reports';
vi.mock('../../src/lib/api/reports',()=>({createReport:vi.fn(),reportStatus:vi.fn()}));
vi.mock('../../src/lib/api/consumption',()=>({consumptionApi:{catalog:vi.fn().mockResolvedValue({timezone:'America/Santiago'})}}));
const result:Report={id:'00000000-0000-0000-0000-000000000005',scale:'anual',state:'generado',timezone:'America/Santiago',window:{start:'2024-01-01',end:'2025-01-01'},cutoff_at:'2026-01-01T00:00:00Z',download_path:'/api/v1/reports/00000000-0000-0000-0000-000000000005/download',filename:'Edificio-anual-2024.pdf'};
afterEach(()=>{cleanup();vi.clearAllMocks();window.history.replaceState(null,'','/');});
test('only generated output offers the selected protected file',()=>{
 /**A saved resource is downloaded by identity; rerendering its status never starts another generation. */
 const {rerender}=render(<ReportStatus report={result} onRefresh={()=>{}}/>);
 expect(screen.getByRole('link',{name:'Descargar PDF'}).getAttribute('href')).toBe(result.download_path);
 rerender(<ReportStatus report={{...result,state:'fallido',download_path:null,functional_reason_code:'composicion_no_admisible'}} onRefresh={()=>{}}/>);
 expect(screen.queryByRole('link')).toBeNull();expect(screen.getByRole('alert').textContent).toContain('legibilidad');
});
test('selection survives uncertain failure and retry uses the same admission key',async()=>{
 /**An unansweredPOST can be retried without accidentally creating another report; inputs remain available. */
 vi.mocked(createReport).mockRejectedValueOnce(new Error('network')).mockResolvedValueOnce(result);
 render(<ReportForm/>);
 fireEvent.change(screen.getByLabelText('Tipo de reporte'),{target:{value:'anual'}});
 fireEvent.change(screen.getByLabelText('Año'),{target:{value:'2024'}});
 fireEvent.click(screen.getByRole('button',{name:'Generar PDF'}));
 await screen.findByRole('alert');
 expect((screen.getByLabelText('Año') as HTMLInputElement).value).toBe('2024');
 fireEvent.click(screen.getByRole('button',{name:'Generar PDF'}));
 await screen.findByRole('link',{name:'Descargar PDF'});
 expect(vi.mocked(createReport).mock.calls[0][1]).toBe(vi.mocked(createReport).mock.calls[1][1]);
});

test('a late saved-report lookup cannot replace a selection already edited',async()=>{
 /**Restoring a private result may finish after the person has started another calendar selection. */
 const {reportStatus}=await import('../../src/lib/api/reports');
 let finish!:(value:Report)=>void;
 vi.mocked(reportStatus).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
 window.history.replaceState(null,'','/reportes/?reporte='+result.id);
 render(<ReportForm/>);
 fireEvent.change(screen.getByLabelText('Tipo de reporte'),{target:{value:'anual'}});
 fireEvent.change(screen.getByLabelText('Año'),{target:{value:'2024'}});
 finish({...result,scale:'diario'});
 await screen.findByRole('link',{name:'Descargar PDF'});
 expect((screen.getByLabelText('Tipo de reporte') as HTMLSelectElement).value).toBe('anual');
 expect((screen.getByLabelText('Año') as HTMLInputElement).value).toBe('2024');
});
