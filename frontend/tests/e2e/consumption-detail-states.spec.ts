/** Advanced001 states consume actual001/002 producers through a protected, test-only CLI. */
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { expect, test } from '@playwright/test';
import { consumptionFixture } from './consumption.setup';

test.use({ timezoneId: 'Asia/Tokyo' });
test.skip(!process.env.HISTORY_E2E_CLOCK_FILE || process.env.CONSUMPTION_E2E_MODE !== 'physical', 'Requires isolated seven-source fixture and private clock.');

test('detail preserves incomplete, late total, six maxima and changed calculation evidence', async ({ page }) => {
  /** Run an authorized internal publisher and align browser Date with the private server clock. */
  async function scenario(action: string) {
    const selection = JSON.parse(execFileSync(resolve('../.venv/bin/python'), ['-m', 'backend.tests.control_consumption_browser', action], { cwd: resolve('..'), encoding: 'utf8' }));
    await page.clock.setFixedTime(new Date(readFileSync(process.env.HISTORY_E2E_CLOCK_FILE!, 'utf8')));
    return selection as {start:string;end:string};
  }
  /** Await exactly the current category/period capture to avoid accepting an earlier response. */
  async function query(start:string, end:string) {
    await page.getByLabel('Inicio con offset', {exact:true}).fill(start);
    await page.getByLabel('Fin con offset', {exact:true}).fill(end);
    await page.getByRole('button', {name:'Consultar período'}).click();
  }
  const partial = await scenario('partial');
  await page.goto('/ingreso/');
  await page.getByLabel('Correo',{exact:true}).fill('operator-active@example.test');
  await page.getByLabel('Contraseña',{exact:true}).fill(consumptionFixture().password+' renewed');
  await page.getByRole('button',{name:'Ingresar',exact:true}).click();
  await expect(page).toHaveURL(/\/cuenta\/$/);
  await page.getByRole('link',{name:'Consumo',exact:true}).click();
  await query(partial.start,partial.end);
  await expect(page.getByText('Datos incompletos',{exact:true})).toBeVisible();
  await expect(page.locator('tbody tr')).toHaveCount(0);
  await scenario('late');
  await page.getByRole('button',{name:'Actualizar consumo',exact:true}).click();
  await expect(page.getByRole('cell',{name:'20 kWh',exact:true})).toBeVisible();
  const maximum = await scenario('maximum');
  await query(maximum.start,maximum.end);
  const total='5999999999999999999999999999999.999999999999994 kWh';
  await expect(page.getByRole('cell',{name:total,exact:true})).toBeVisible();
  await expect(page.locator('[role="graphics-symbol"]')).toHaveAttribute('aria-label',new RegExp(total.replace('.','\\.')));
  for (const category of ['CAT-02','CAT-03','CAT-04','CAT-05','CAT-06','CAT-07']) {
    await page.getByRole('combobox',{name:'Categoría',exact:true}).selectOption(category);
    await expect(page.getByRole('cell',{name:'999999999999999999999999999999.999999999999999 kWh',exact:true})).toBeVisible();
  }
  await page.getByRole('combobox',{name:'Categoría',exact:true}).selectOption('CAT-01');
  const changed = await scenario('changed');
  await query(changed.start,changed.end);
  await expect(page.getByText('Cambió la configuración de cálculo dentro del intervalo',{exact:true})).toBeVisible();
  await expect(page.locator('tbody tr')).toHaveCount(0);
  await page.getByRole('combobox',{name:'Categoría',exact:true}).selectOption('CAT-05');
  await expect(page.getByRole('cell',{name:'12 kWh',exact:true})).toBeVisible();
  // Hold a real response for A; B must remain selected after A finally arrives.
  let release!: () => void, arrived!: () => void;
  const held = new Promise<void>(resolve => { release=resolve; });
  const received = new Promise<void>(resolve => { arrived=resolve; });
  await page.route('**/CAT-05/detail?**', async route => {
    const response=await route.fetch(); arrived(); await held;
    await route.fulfill({response}).catch(() => {});
  });
  await page.getByRole('button',{name:'Actualizar consumo',exact:true}).click();
  await received;
  await page.getByRole('combobox',{name:'Categoría',exact:true}).selectOption('CAT-03');
  await expect(page.locator('tbody tr')).toHaveCount(0);
  release();
  await page.unroute('**/CAT-05/detail?**');
  await expect(page.locator('tbody tr')).toHaveCount(0);
  await page.getByRole('combobox',{name:'Categoría',exact:true}).selectOption('CAT-05');
  await expect(page.getByRole('cell',{name:'12 kWh',exact:true})).toBeVisible();
  // A transport failure must clear stale numbers and offer a keyboard-accessible retry.
  let fail=true;
  await page.route('**/CAT-05/detail?**', route => {if(fail){fail=false;return route.abort();}return route.continue();});
  await page.getByRole('button',{name:'Actualizar consumo',exact:true}).click();
  await expect(page.getByRole('button',{name:'Reintentar',exact:true})).toBeVisible();
  await expect(page.locator('tbody tr')).toHaveCount(0);
  await page.getByRole('button',{name:'Reintentar',exact:true}).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('cell',{name:'12 kWh',exact:true})).toBeVisible();
  const own = await scenario('own');
  await query(own.start,own.end);
  await expect(page.getByText('Sin datos',{exact:true})).toBeVisible();
  await expect(page.locator('tbody tr')).toHaveCount(0);
});
