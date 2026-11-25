/**008 measured/calculated/absent evidence retains units and never displays missing energy as zero. */
import React from 'react';
import '@testing-library/jest-dom/vitest';
import {render,screen,cleanup} from '@testing-library/react';
import {afterEach,test,expect} from 'vitest';
import {UrgentEvidence} from '../../src/components/notifications/UrgentEvidence';
import type {FunctionalContent} from '../../src/lib/api/notification-types';
afterEach(cleanup);
const content:FunctionalContent={building_name:'Synthetic',type:'alerta_consumo',priority:'urgente',rule_id:'00000000-0000-0000-0000-000000000008',rule_version:1,headline:'Total',window:{start:'2026-01-01T00:00:00Z',end:'2026-01-01T01:00:00Z'},recovered_periods:[],cutoff_at:'2026-01-01T01:00:00Z',is_late:false,data_status:'disponible',summary_items:[],protected_paths:['/consumption/'],timezone:'UTC',condition:{kind:'consumo',category_id:'CAT-01',unit:'kWh',window:{kind:'hora'},comparison:'gt',threshold_kwh:'15'},evidence:[{category_id:'CAT-01',unit:'kWh',formula_version:null,detected_at:'2026-01-01T01:00:00Z',window:{start:'2026-01-01T00:00:00Z',end:'2026-01-01T01:00:00Z'},value_kwh:'20',origin:'calculado',quality:'valida',basis_categories:['CAT-03','CAT-05'],scope_description:'Total de las categorías indicadas.',source_refs:[],limitation_code:null,received_at:null}]};
test('actual calculated total and basis stay distinct from physical general metering',()=>{
 /**The owner supplied20; the component formats the string without recomputing a total. */
 render(<UrgentEvidence content={content}/>);expect(screen.getByText('20 kWh')).toBeVisible();expect(screen.getByText('Base calculada: CAT-03, CAT-05')).toBeVisible();expect(screen.getByText(/mayor que 15 kWh/)).toBeVisible();
});
test('missing value has an explicit unavailable label rather than zero',()=>{
 /**Absence preserves a null value and its functional limitation. */
 render(<UrgentEvidence content={{...content,evidence:[{...content.evidence[0],value_kwh:null,quality:'sin_datos',limitation_code:'sin_novedades_aceptadas_en_plazo'}]}}/>);expect(screen.getByText('Energía no disponible')).toBeVisible();expect(screen.queryByText('0 kWh')).not.toBeInTheDocument();
});
