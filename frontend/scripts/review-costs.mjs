/** Isolated visual/interaction checks: synthetic responses in Playwright only, never application fixtures. */
import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const output = resolve(process.argv[2] ?? 'test-results/costs-integrated');
await mkdir(output, { recursive:true });
const baseURL = process.env.UI_REVIEW_URL ?? 'http://127.0.0.1:3011';
if (!['localhost','127.0.0.1'].includes(new URL(baseURL).hostname)) throw new Error('Local preview only.');
const period = {start:'2026-10-01T00:00:00-03:00',end:'2026-11-01T00:00:00-03:00',timezone:'America/Santiago'};
const cutoff = '2026-11-02T12:00:00Z';
const component = (code,kind,amount) => ({code,kind,presented_amount:amount,state:'available',tax_basis:kind === 'impuesto' ? 'impuesto_separado' : 'neto', basis_value:'10000', unit:'kWh',rule_id:'exact_intervals',unit_price:'100',applied_prices:[],limitation_codes:[],profile_version_refs:[],evidence_refs:[]});
const calculation = {id:'preview-calculation',cycle_id:'preview-cycle',previous_id:'preview-previous',revision:3,cutoff_at:cutoff,temporal_state:'cerrado',execution_state:'completado',sufficiency:'completo',complete_total:'1428000',available_subtotal:'1428000',net_total:'1200000',tax_total:'228000',currency:'CLP',reason_codes:[],monthly_maxima:[],snapshot:{request:period,cutoff_at:cutoff,supply_revision:1,profile_revision:1,supply:{general_board_ref:'Suministro de muestra',general_source_id:'preview-source',document_refs:[],measurement_point_differences:[]}},components:[component('energy','energia','1000000'),component('demand','demanda_punta','150000'),component('transmission','transmision','40000'),component('fixed','fijo','10000'),component('iva','impuesto','228000')]};
const bill = {id:'preview-bill',bill_revision_id:'preview-bill-revision',revision:1,external_identifier:'Boleta de muestra',total_payable:'1416100'};
const comparison = {id:'preview-comparison',revision:1,calculation_id:calculation.id,bill_revision_id:bill.bill_revision_id,comparable_calculated:'1428000',comparable_billed:'1416100',delta_amount:'11900',delta_percent:'0.84',total_payable:bill.total_payable,currency:'CLP',pairs:[],excluded_lines:[],limitation_codes:[]};
const cycle = {id:calculation.cycle_id,start_at:period.start,end_at:period.end,timezone:period.timezone,calculation,bill,comparison,comparison_status:'available',historical_comparisons:[],delta_amount:'11900',delta_percent:'0.84'};
const names = ['HVAC y agua caliente sanitaria','Iluminación exterior','Iluminación interior','Circuitos de enchufes','Sistema sanitario','Ascensores'];
const percentages = [40,10,16,22,7,5];
const distribution = {calculation_id:calculation.id,cutoff_at:cutoff,state:'available',reason_code:null,energy_amount:'1000000',other_amount:'428000',unassigned_amount:'0',unassigned_percent:'0',categories:names.map((name,i) => ({id:`CAT-0${i+2}`,name,state:'available',energy_kwh:String(percentages[i]*100),percent:String(percentages[i]),estimated_amount:String(percentages[i]*10000)}))};
const pageOf = items => ({items,next_cursor:null,cutoff_at:cutoff});
const browser = await chromium.launch({headless:true});
const results = [];
try {
  for (const width of [1440,390]) for (const scenario of ['complete','incomplete','empty','error','no-meter','distribution-error','pending','historical']) {
    const context = await browser.newContext({viewport:{width,height:width === 1440 ? 1086 : 844},reducedMotion:'reduce'});
    const errors = [], requests = [];
    const current = scenario === 'incomplete' ? {...calculation,complete_total:null,net_total:null,tax_total:null,sufficiency:'parcial',reason_codes:['insufficient_demand_history']} : calculation;
    await context.route('**/api/v1/**', async route => {
      const path = new URL(route.request().url()).pathname.replace('/api/v1','');
      requests.push({path,method:route.request().method()});
      const reply = (value,status=200) => route.fulfill({status,contentType:'application/json',body:JSON.stringify(value)});
      if (route.request().method() !== 'GET') throw new Error('Consultation made a mutation.');
      if (path === '/auth/session') return reply({account:{id:'preview-account',email:'operador@edificio.cl',role:'operador',status:'active'},session_state:'normal',must_change_password:false,absolute_expires_at:'2099-01-01T00:00:00Z',idle_expires_at:'2099-01-01T00:00:00Z',permissions:['consumption.read','costs.read']});
      if (scenario === 'error') return reply({code:'preview_error',detail:'Fallo de muestra'},503);
      if (path === '/costs/readiness') return reply({physical_general:false,supply_configured:false,profile_published:false});
      if (path.endsWith('/distribution')) {
        const estimate = {...distribution,calculation_id:path.split('/').at(-2)};
        if (scenario === 'distribution-error') return reply({code:'preview_error',detail:'Fallo de muestra'},503);
        if (scenario === 'incomplete') return reply({...estimate,state:'unavailable',reason_code:'category_coverage_incomplete',other_amount:null,categories:estimate.categories.map(row => ({...row,state:'incomplete',percent:null,estimated_amount:null}))});
        if (scenario === 'no-meter') return reply({...estimate,unassigned_amount:'50000',unassigned_percent:'5',categories:estimate.categories.map((row,i) => i === 5 ? {...row,state:'no_meter',percent:null,estimated_amount:null,energy_kwh:null} : row)});
        return reply(estimate);
      }
      if (path === '/costs/cycles' || path === '/costs/history') return reply(pageOf(scenario === 'empty' ? [] : [{...cycle,calculation:current,...(scenario === 'pending' ? {comparison:null,comparison_status:'missing_for_selected_revisions'} : {})}]));
      if (path === '/costs/bills') return reply(pageOf([bill]));
      if (path === '/costs/calculations/preview-previous') return reply({...current,id:'preview-previous',revision:2,previous_id:null});
      if (path.startsWith('/costs/calculations/')) return reply(current);
      throw new Error(`Unhandled endpoint ${path}`);
    });
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    try {
      await page.goto(`${baseURL}/costos/`,{waitUntil:'networkidle'});
      await page.getByRole('heading',{name:'Costos de energía',exact:true}).waitFor();
      if (!['empty','error'].includes(scenario)) {
        await page.getByRole('heading',{name:'Costo de energía por categoría',exact:true}).waitFor();
        if (scenario === 'complete') {
          if (await page.locator('.cost-category-table tbody tr').count() !== 6) throw new Error('Missing category rows.');
          if (await page.locator('.cost-donut circle[stroke-dasharray]').count() !== 6) throw new Error('Missing pie slices.');
          await page.getByRole('combobox',{name:'Revisión',exact:true}).selectOption('preview-previous');
          if (new URL(page.url()).searchParams.has('calculation')) throw new Error('Draft revision applied before Consultar.');
          await page.getByRole('button',{name:'Consultar',exact:true}).click();
          await page.waitForURL(/calculation=preview-previous/);
          await page.waitForLoadState('networkidle');
          if (new URL(page.url()).searchParams.get('calculation') !== 'preview-previous') throw new Error('Historical revision did not apply.');
          await page.getByRole('combobox',{name:'Revisión',exact:true}).selectOption('preview-calculation');
          await page.getByRole('button',{name:'Consultar',exact:true}).click();
          await page.waitForURL(/calculation=preview-calculation/);
          await page.waitForLoadState('networkidle');
          await page.getByRole('button',{name:'Actualizar',exact:true}).click();
          await page.waitForLoadState('networkidle');
        }
        if (scenario === 'historical') {
          await page.getByRole('combobox',{name:'Revisión',exact:true}).selectOption('preview-previous');
          await page.getByRole('button',{name:'Consultar',exact:true}).click();
          await page.waitForURL(/calculation=preview-previous/);
          await page.waitForLoadState('networkidle');
          if (await page.locator('.cost-comparison-values').count()) throw new Error('Current contrast displayed for historical calculation.');
        }
        if (scenario === 'incomplete' && await page.locator('circle[stroke-dasharray]').count()) throw new Error('Incomplete evidence rendered a full pie.');
        if (scenario === 'pending' && await page.locator('.cost-comparison-values').count()) throw new Error('Pending contrast has values.');
        if (scenario === 'no-meter') await page.getByRole('cell',{name:'Sin medidor',exact:true}).waitFor();
      }
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth-innerWidth);
      if (overflow) throw new Error(`Page overflow ${overflow}px`);
      const screenshot = `${scenario}-${width}.png`;
      await page.evaluate(() => scrollTo(0,0));
      await page.screenshot({path:resolve(output,screenshot),fullPage:true});
      if (scenario === 'complete') {
        await page.getByText('Historial de ciclos y revisiones',{exact:false}).click();
        await page.getByRole('button',{name:'Consultar historial de costos',exact:true}).waitFor();
        await page.getByRole('button',{name:'Consultar cálculo 3',exact:true}).click();
        await page.getByText('Revisar bases de reproducción',{exact:true}).click();
        await page.waitForLoadState('networkidle');
        await page.locator('.table-scroll').evaluateAll(elements => elements.forEach(el => { el.scrollLeft = 0; }));
        await page.evaluate(() => scrollTo(0,0));
        await page.waitForFunction(() => scrollY === 0);
        await page.screenshot({path:resolve(output,`details-${width}.png`),fullPage:true});
      }
      results.push({scenario,width,screenshot,overflow,errors,requests});
      console.log(`${scenario}-${width}: ${errors.length} browser errors; overflow ${overflow}px`);
    } catch(error) { results.push({scenario,width,errors:[...errors,error.message],requests}); console.error(`${scenario}-${width}: ${error.message}`); }
    finally { await context.close(); }
  }
} finally { await browser.close(); await writeFile(resolve(output,'results.json'),JSON.stringify({data:'Synthetic browser fixtures only. Backend tested separately.',results},null,2)); }
if (results.some(result => result.errors.length)) process.exitCode=1;
