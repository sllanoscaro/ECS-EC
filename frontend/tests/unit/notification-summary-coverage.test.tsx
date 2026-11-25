/**008 count/coverage presentation must distinguish actual zero from absent or partial history. */
import React from 'react';
import '@testing-library/jest-dom/vitest';
import {render,screen,cleanup} from '@testing-library/react';
import {afterEach,test,expect} from 'vitest';
import {SummaryCoverage} from '../../src/components/notifications/SummaryCoverage';
afterEach(cleanup);
test('complete zero is an event count while unknown is unavailable',()=>{
 /**A selected failed source stays visible and never becomes zero. */
 render(<SummaryCoverage items={[{kind:'recepcion',count:0,coverage:'completa',covered_periods:[{start:'2026-01-01T00:00:00Z',end:'2026-01-02T00:00:00Z'}],known_gaps:[],source_refs:[],limitation_code:null},{kind:'calidad',count:null,coverage:'desconocida',covered_periods:[],known_gaps:[],source_refs:[],limitation_code:'fuente_no_consultable'}]}/>);
 expect(screen.getByText('Eventos: 0')).toBeVisible();expect(screen.getByText('No disponible')).toBeVisible();expect(screen.getByText('Cobertura: Desconocida')).toBeVisible();
});
test('limited counts are identified as observed with explicit history gaps',()=>{
 /**Observed events do not become a total covering a known missing period. */
 render(<SummaryCoverage items={[{kind:'recepcion',count:3,coverage:'incompleta',covered_periods:[],known_gaps:[{start:'2026-01-01T00:00:00Z',end:'2026-01-02T00:00:00Z'}],source_refs:[],limitation_code:'outside_registered_history'}]}/>);
 expect(screen.getByText('Eventos observados: 3')).toBeVisible();expect(screen.getByText(/Hueco conocido:/)).toBeVisible();
});
