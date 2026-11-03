/** Capture the existing UI with browser-only synthetic API responses; never contact a business backend.
 * Run against Next dev: node scripts/review-views.mjs [output-directory].
 * Writes PNGs and JSON diagnostics. Exits nonzero for browser errors or unhandled fixture requests.
 * This is a visual review aid, not evidence of backend integration or authorization enforcement.
 */
import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const baseURL = process.env.UI_REVIEW_URL ?? 'http://127.0.0.1:3000';
if (!['localhost', '127.0.0.1', '[::1]'].includes(new URL(baseURL).hostname)) throw new Error('Use a local preview server.');
const output = resolve(process.argv[2] ?? 'test-results/ui-review');
await mkdir(output, { recursive: true });
const now = '2026-01-02T12:00:00Z';
const source = '10000000-0000-0000-0000-000000000001';
const period = { start: '2026-01-01T00:00:00-03:00', end: '2026-01-01T04:00:00-03:00', timezone: 'America/Santiago' };
const names = ['Energía eléctrica total', 'HVAC y agua caliente sanitaria', 'Iluminación exterior', 'Iluminación interior', 'Circuitos de enchufes', 'Sistema sanitario', 'Ascensores'];
const categories = names.map((name, i) => ({ id: `CAT-0${i + 1}`, name, scope: 'Edificio sintético de revisión', has_meter: i < 5, source_mode: i < 5 ? 'measured' : 'unavailable', base_categories: [], category_revision: 1 }));
const catalog = { building_id: source, timezone: period.timezone, cutoff_at: now, default_period: period, categories };
const configuration = { id: source, building_id: source, revision: 1, effective_from: period.start, recorded_at: now, timezone: period.timezone, categories: categories.map(c => ({ category_id: c.id, has_meter: c.has_meter, category_revision: 1, source_id: c.has_meter ? source.slice(0, -1) + c.id.at(-1) : null, source_label: c.has_meter ? `Medidor de prueba ${c.id}` : null })) };
const supply = { id: source, revision: 1, general_board_ref: 'Tablero de revisión sintético', category_id: 'CAT-01', general_source_id: source, distributor: null, location: 'Edificio de prueba', connection_conditions: null, document_refs: ['Documento sintético, sin validez tarifaria'], measurement_point_differences: [] };
const calculation = { id: 'synthetic-calculation', cycle_id: 'synthetic-cycle', revision: 1, temporal_state: 'cerrado', sufficiency: 'parcial', execution_state: 'completado', currency: 'CLP', available_subtotal: '100000', complete_total: null, reason_codes: ['billing_month_unresolved'], monthly_maxima: [], engine_version: 'synthetic-preview', input_hash: 'synthetic-preview', retain_until: '2027-01-02T12:00:00Z', components: [{ code: 'energy', kind: 'energia', basis_value: '1000', unit: 'kWh', rule_id: 'exact_intervals', unit_price: '100', tax_basis: 'neto', presented_amount: '100000', state: 'available', limitation_codes: [], applied_prices: [] }], snapshot: { cutoff_at: now, request: period, supply, supply_revision: 1, profile_revision: null, billing_month_ref: null, general_reason: null } };
const bill = { id: 'synthetic-bill', bill_revision_id: 'synthetic-bill-revision', revision: 1, supply_id: source, external_identifier: 'BOLETA-SINTETICA', issued_at: now, start: period.start, end: period.end, timezone: period.timezone, declared_start: null, declared_end: null, boundary_criterion: 'Período sintético de revisión', boundary_limited: false, document_reference: 'Documento de prueba', currency: 'CLP', energy_read: '1000', demand_read: null, demand_billed: null, declared_tax: null, total_payable: '100000', lines: [{ code: 'energy', description: 'Energía de prueba', quantity: '1000', unit: 'kWh', amount: '100000', tax_basis: 'neto', tax_amount: null, cycle_relation: 'current_cycle', document_reference: 'Documento de prueba' }] };
const comparison = { id: 'synthetic-comparison', revision: 1, calculation_id: calculation.id, bill_revision_id: bill.bill_revision_id, currency: 'CLP', comparable_calculated: '100000', comparable_billed: '100000', total_payable: '100000', delta_amount: '0', delta_percent: '0', pairs: [{ code: 'energy', tax_basis: 'neto', unit: 'kWh', calculated_amount: '100000', billed_amount: '100000', delta_amount: '0' }], excluded_lines: [], limitation_codes: [] };
const cycle = { id: calculation.cycle_id, start_at: period.start, end_at: period.end, timezone: period.timezone, calculation, comparison, comparison_status: 'available', historical_comparisons: [], delta_amount: '0', delta_percent: '0' };
const pageOf = items => ({ items, next_cursor: null, cutoff_at: now });
const account = { id: source, email: 'admin-ui@example.test', role: 'administrador_tecnico', status: 'active', must_change_password: false, revision: 1, created_at: now, updated_at: now };
const readPermissions = ['consumption.read', 'costs.read', 'reports.generate'];
const permissions = [...readPermissions, 'consumption.configuration.manage', 'costs.configuration.read', 'costs.configuration.manage', 'costs.calculations.create', 'costs.bills.manage', 'costs.comparisons.create', 'identity.accounts.read', 'administration.history.read'];

/** Return deterministic intervals, including a real measured zero; no fixture pretends to be installation data. */
function detail(url, scenario) {
  const category = categories.find(c => url.pathname.includes(c.id)) ?? categories[0];
  const rows = ['25', '0', '32', '18'].map((energy, i) => ({ record_id: `synthetic-${i}`, revision: 1, start: `2026-01-01T0${i}:00:00-03:00`, end: `2026-01-01T0${i + 1}:00:00-03:00`, energy_kwh: energy, first_incorporated_at: now, configuration_revision: 1, category_revision: 1, origin: { kind: 'measured', source_id: source, original_value: energy, original_unit: 'kWh' } }));
  const state = !category.has_meter ? 'no_meter' : scenario === 'empty' ? 'no_data' : scenario === 'incomplete' ? 'incomplete' : 'available';
  const result = { request_ref: 'synthetic-preview', building_id: source, category, period, cutoff_at: now, state, source_mode: category.source_mode, configuration_segments: [{ ...period, configuration_revision: 1, category_revision: 1, source_mode: category.source_mode, base_categories: [], source_id: category.has_meter ? source : null, basis_sources: [] }], rows: ['no_meter', 'no_data'].includes(state) ? [] : rows, diagnostics: [], warnings: scenario === 'incomplete' ? [{ code: 'observed_gaps', count: 1, message: 'Falta un intervalo en esta muestra sintética.' }] : [] };
  if (scenario === 'incomplete') result.rows = rows.filter((_, i) => i !== 2);
  if (url.pathname.endsWith('/aggregates')) {
    const granularity = url.searchParams.get('granularity');
    return { ...result, granularity, blocks: granularity === 'hour' ? result.rows.map((r, i) => ({ ...r, timezone: period.timezone, aggregate_id: `synthetic-block-${i}`, duration_us: '3600000000', covered_duration_us: '3600000000', coverage_percent: '100', coverage_state: 'complete', temporal_state: 'finished', contribution_count: 1, source_mode: 'measured', provenance_segments: [], created_at: now, last_new_data_at: now, retain_until: '2027-01-02T12:00:00Z', warnings: [] })) : [] };
  }
  return result;
}

/** Fulfill every API request in the browser; unknown endpoints fail visibly instead of reaching real infrastructure. */
async function fixtures(context, role, scenario, unknown) {
  await context.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace('/api/v1', '');
    const reply = (json, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(json) });
    if (route.request().method() !== 'GET') return reply({ code: 'preview_read_only', detail: 'Esta revisión visual no guarda cambios.' }, 503);
    if (path === '/auth/session') {
      if (role === 'anonymous') return reply({ code: 'session_required', detail: 'Debe iniciar sesión.' }, 401);
      return reply({ account: { ...account, role: role === 'operator' ? 'operador' : account.role }, session_state: scenario === 'renewal' ? 'password_change_required' : 'normal', must_change_password: scenario === 'renewal', absolute_expires_at: '2099-01-01T00:00:00Z', idle_expires_at: '2099-01-01T00:00:00Z', csrf_token: 'synthetic-preview', permissions: role === 'operator' ? readPermissions : permissions });
    }
    if (scenario === 'error') return reply({ code: 'preview_unavailable', detail: 'Fallo sintético de revisión visual.' }, 503);
    if (path === '/consumption/dashboard') {
      const start = '2026-11-02T00:00:00-03:00';
      const series = Array.from({length: 58}, (_, i) => ({ start: new Date(Date.parse(start) + i * 900000).toISOString(), end: new Date(Date.parse(start) + (i + 1) * 900000).toISOString(), energy_kwh: scenario === 'empty' ? null : String(i < 24 ? 2 : 10 + i % 4), coverage_percent: scenario === 'empty' ? '0' : '100' }));
      const energy = series.reduce((sum, r) => sum + Number(r.energy_kwh ?? 0), 0);
      return reply({timezone: period.timezone, cutoff_at: '2026-11-02T14:32:08-03:00', period: {start, end: '2026-11-03T00:00:00-03:00', timezone: period.timezone}, chart_excluded_count: 0, series, categories: categories.map((c, i) => ({...c, series: series.map(point => ({...point, energy_kwh: !c.has_meter || point.energy_kwh === null ? null : String(Number(point.energy_kwh) * (i === 0 ? 1 : 1 / (i + 1)))})), chart_excluded_count: 0, state: scenario === 'empty' ? 'no_data' : c.has_meter ? 'available' : 'no_meter', energy_kwh: scenario === 'empty' || !c.has_meter ? null : String(i === 0 ? energy : [0, 160, 45, 84, 132][i]), coverage_percent:'99.75', covered_duration_us:'52200000000', elapsed_duration_us:'52328000000', last_reading_at:'2026-11-02T14:30:00-03:00'}))});
    }
    if (path === '/consumption/catalog') return reply(catalog);
    if (path === '/consumption/configuration') return reply(configuration);
    if (/\/consumption\/categories\//.test(path)) return reply(detail(url, scenario));
    if (path === '/costs/supply') return reply(supply);
    if (path === '/costs/profiles') return reply({ ...pageOf([]), latest_version_id: null, selected_published_version_id: null, latest_version: null });
    if (['/costs/cycles', '/costs/history'].includes(path)) return reply(pageOf(scenario === 'empty' ? [] : [cycle]));
    if (path.startsWith('/costs/calculations/')) return reply(calculation);
    if (path === '/costs/bills') return reply(pageOf(scenario === 'empty' ? [] : [bill]));
    if (path.startsWith('/costs/comparisons/')) return reply(comparison);
    if (path === '/identity/accounts') return reply(pageOf(scenario === 'empty' ? [] : [account, { ...account, id: source.slice(0, -1) + '2', email: 'operador-ui@example.test', role: 'operador' }]));
    if (path === '/identity/administration-history') return reply(pageOf(scenario === 'empty' ? [] : [{ id: source, occurred_at: now, actor: { kind: 'account', account_id: source, process_code: null }, action: 'identity.account.created', target: { module: 'identity', entity_type: 'account', id: source, revision: 1 }, result: 'allowed', reason_code: 'created', operation_ref: 'synthetic-preview' }]));
    unknown.push(path);
    return reply({ code: 'unhandled_preview', detail: `Sin fixture: ${path}` }, 501);
  });
}

const routes = ['/', '/ingreso/', '/cuenta/', '/consumption/', '/costos/', '/administracion/consumo/', '/administracion/costos/', '/administracion/usuarios/', '/administracion/historial/', '/reportes/'];
const results = [];
const browser = await chromium.launch({ headless: true });
try {
  for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
    for (const path of routes) {
      const role = path === '/ingreso/' ? 'anonymous' : 'admin';
      await capture(path, viewport, role, 'populated');
    }
  }
  for (const [path, role, scenario] of [
    ['/consumption/', 'admin', 'hour'], ['/consumption/', 'admin', 'empty'], ['/consumption/', 'admin', 'incomplete'], ['/consumption/', 'admin', 'no-meter'], ['/consumption/', 'admin', 'error'],
    ['/costos/', 'admin', 'empty'], ['/costos/', 'admin', 'error'], ['/administracion/consumo/', 'admin', 'error'], ['/administracion/usuarios/', 'admin', 'empty'], ['/administracion/historial/', 'admin', 'empty'],
    ['/cuenta/', 'admin', 'renewal'], ['/administracion/costos/', 'admin', 'segment'], ['/administracion/costos/', 'admin', 'bill-edit'], ['/administracion/usuarios/', 'admin', 'edit'], ['/administracion/usuarios/', 'admin', 'reset'],
    ['/costos/', 'admin', 'evidence'], ['/consumption/', 'operator', 'populated'], ['/administracion/usuarios/', 'operator', 'denied'], ['/cuenta/', 'anonymous', 'anonymous'],
  ]) await capture(path, { width: 1440, height: 1000 }, role, scenario);
} finally {
  await browser.close();
  await writeFile(resolve(output, 'results.json'), JSON.stringify({ baseURL, data: 'browser-only synthetic fixtures; no backend integration tested', results }, null, 2));
}

/** Render a route, apply only local disclosure/filter interactions, capture the full page and measure overflow. */
async function capture(path, viewport, role, scenario) {
  const slug = `${path === '/' ? 'inicio' : path.replaceAll('/', '-').replace(/^-|-$/g, '')}-${viewport.width}-${role}-${scenario}`;
  if (process.env.UI_REVIEW_FILTER && !new RegExp(process.env.UI_REVIEW_FILTER).test(slug)) return;
  const errors = [], unknown = [], sockets = [], consoleErrors = [];
  const context = await browser.newContext({ viewport, colorScheme: 'light', reducedMotion: 'reduce' });
  await fixtures(context, role, scenario, unknown);
  const page = await context.newPage();
  page.setDefaultTimeout(5000);
  page.on('pageerror', error => errors.push(error.message));
  page.on('websocket', socket => sockets.push(new URL(socket.url()).pathname));
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  try {
    const response = await page.goto(`${baseURL}${path}`, { waitUntil: 'networkidle' });
    await page.getByRole('heading', { level: 1 }).waitFor();
    if (['/', '/consumption/'].includes(path) && role === 'admin' && scenario === 'populated') {
      if (viewport.width >= 900) {
        await page.getByRole('button', {name:'Plegar panel lateral'}).click();
        await page.locator('nav [aria-current="page"]').click();
      } else {
        await page.getByRole('button', {name:'Abrir menú'}).click();
        await page.locator('nav [aria-current="page"]').waitFor({state:'visible'});
        await page.keyboard.press('Escape');
        await page.getByRole('button', {name:'Abrir menú'}).waitFor();
      }
      const activeStyle = await page.locator('nav [aria-current="page"]').evaluate(el => ({background:getComputedStyle(el).backgroundColor, color:getComputedStyle(el).color}));
      if (activeStyle.background !== 'rgb(79, 154, 23)' || activeStyle.color !== 'rgb(255, 255, 255)') throw new Error('El enlace activo no conserva los colores aprobados.');
    }
    if (path === '/' && scenario === 'populated') {
      const totalPaths = await page.locator('[data-series="smooth"]').evaluateAll(paths => paths.map(p => p.getAttribute('d')));
      const category = page.getByRole('button', { name: /Iluminación exterior/ });
      await category.focus();
      await page.keyboard.press('Enter');
      if (await category.getAttribute('aria-pressed') !== 'true') throw new Error('Category selection missing.');
      if (await page.locator('[data-series="smooth"]').first().getAttribute('stroke') !== '#7A6EAB') throw new Error('Incorrect category color.');
      const reset = page.getByRole('button', { name: 'Ver consumo total' });
      if (await page.locator('.dashboard-series').evaluate(el => getComputedStyle(el).animationName) !== 'dashboard-series-fade') throw new Error('Reduced motion alternative missing.');
      const amount = category.locator('.category-energy');
      const amountStyle = await amount.evaluate(el => ({ color: getComputedStyle(el).color, weight: getComputedStyle(el).fontWeight, text: el.textContent }));
      if (amountStyle.color !== 'rgb(122, 110, 171)' || amountStyle.weight !== '700' || !amountStyle.text.endsWith(' kWh')) throw new Error('Category energy must be bold, colored and include kWh.');
      await page.emulateMedia({ reducedMotion: 'no-preference' });
      await reset.click();
      if (await page.locator('.dashboard-series').evaluate(el => getComputedStyle(el).animationName) !== 'dashboard-series-reveal') throw new Error('Total transition missing.');
      await category.click();
      if (await page.locator('.dashboard-series').evaluate(el => getComputedStyle(el).animationName) !== 'dashboard-series-reveal') throw new Error('Category transition missing.');
      await page.locator('.dashboard-series').evaluate(async el => { await Promise.all(el.getAnimations().map(animation => animation.finished)); });
      await page.emulateMedia({ reducedMotion: 'reduce' });
      if (await reset.evaluate(el => getComputedStyle(el).color) !== 'rgb(93, 101, 99)') throw new Error('Reset button must be gray.');
      if (viewport.width >= 900) {
        const legendTop = await page.locator('.chart-legend>span').evaluateAll(spans => spans.map(el => el.getBoundingClientRect().top));
        if (Math.max(...legendTop) - Math.min(...legendTop) > 2) throw new Error('Refresh note is not aligned with the legend.');
      }
      const point = page.locator('.chart-panel [role="graphics-symbol"][data-kind="bar"]').last();
      await point.focus();
      const tooltip = page.getByRole('tooltip');
      if (!/^\d+(?:\.\d{3})*,\d kWh · \d{2}:\d{2}:\d{2}$/.test(await tooltip.textContent())) throw new Error('Dashboard tooltip format is incorrect.');
      if (await page.locator('p.chart-tooltip').count()) throw new Error('Measurement still appears below the chart.');
      if (viewport.width >= 900) {
        const chartBox = await page.locator('.chart-panel').boundingBox();
        const categoryBox = await page.locator('.category-panel').boundingBox();
        const hvacLines = await page.getByRole('button', { name: /HVAC y agua caliente sanitaria/ }).locator('.category-label>span').evaluate(el => {
          const range = document.createRange(); range.selectNodeContents(el); return range.getClientRects().length;
        });
        if (hvacLines !== 1) throw new Error('HVAC category name must occupy one line on desktop.');
        if (chartBox.width <= categoryBox.width) throw new Error('Chart must remain wider than category panel.');
        if (chartBox.height >= categoryBox.height) throw new Error('Chart panel still stretches to category panel height.');
      }
      await page.evaluate(() => scrollTo(0, 0));
      await page.screenshot({ path: resolve(output, `${slug}-selected.png`), fullPage: true });
      await page.getByRole('button', { name: /Iluminación interior/ }).click();
      if (await category.getAttribute('aria-pressed') !== 'false') throw new Error('Old category stays selected.');
      if (await page.locator('[data-series="smooth"]').first().getAttribute('stroke') !== '#2876B7') throw new Error('Second category color missing.');
      await page.getByRole('button', { name: /Ascensores/ }).click();
      if (await page.locator('[data-series="smooth"]').count()) throw new Error('Missing meter must have no curve.');
      await reset.click();
      const restoredPaths = await page.locator('[data-series="smooth"]').evaluateAll(paths => paths.map(p => p.getAttribute('d')));
      if (JSON.stringify(totalPaths) !== JSON.stringify(restoredPaths) || await reset.count()) throw new Error('Original total was not restored.');
    }
    if (role === 'admin' && path === '/administracion/costos/' && scenario !== 'error') await page.getByRole('heading', { name: /Suministro general/ }).waitFor();
    if (scenario === 'hour') await page.goto(`${baseURL}${path}?escala=hour`, {waitUntil:'networkidle'});
    if (scenario === 'no-meter') await page.getByLabel('Categoría').selectOption('CAT-07');
    if (scenario === 'segment') { await page.getByRole('button', { name: 'Añadir segmento', exact: true }).click(); await page.getByRole('button', { name: 'Añadir cargo al segmento 1' }).click(); }
    if (scenario === 'evidence') await page.getByText('Revisar bases de reproducción', { exact: true }).click();
    if (scenario === 'bill-edit') await page.getByRole('button', { name: 'Corregir boleta revisión 1' }).click();
    if (scenario === 'edit') await page.getByRole('button', { name: 'Editar', exact: true }).first().click();
    if (scenario === 'reset') await page.getByRole('button', { name: /Restablecer/ }).first().click();
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: resolve(output, `${slug}.png`), fullPage: true });
    const metrics = await page.evaluate(() => ({ title: document.querySelector('h1')?.textContent, width: innerWidth, scrollWidth: document.documentElement.scrollWidth, headings: [...document.querySelectorAll('h2,h3')].map(el => el.textContent), alerts: [...document.querySelectorAll('[role="alert"]')].map(el => el.textContent) }));
    results.push({ path, role, scenario, viewport, status: response.status(), screenshot: `${slug}.png`, ...metrics, hmrConnected: sockets.some(path => path.includes('hmr')), consoleErrors, errors, unknown });
    console.log(`${slug}: HTTP ${response.status()}, overflow ${metrics.scrollWidth - metrics.width}px, errors ${errors.length}`);
  } catch (error) {
    results.push({ path, role, scenario, viewport, errors: [...errors, error.message], unknown });
    console.error(`${slug}: ${error.message}`);
  } finally { await context.close(); }
}

if (results.some(r => r.errors.length || r.unknown.length || r.status !== 200)) process.exitCode = 1;
