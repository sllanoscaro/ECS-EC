/** Real002 writes/withdrawals via an internal CLI and protected frozen clock, with real006 authentication. */
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { expect, test } from '@playwright/test';
import { consumptionFixture } from './consumption.setup';

test.use({ timezoneId: 'Asia/Tokyo' });
test.skip(!process.env.HISTORY_E2E_CLOCK_FILE, 'Requires isolated history harness and private clock, never production.');

/** Mutate only the private fixture file; the production app has no public clock endpoint. */
function time(value: string) { writeFileSync(process.env.HISTORY_E2E_CLOCK_FILE!, value, { mode: 0o600 }); }
/** Invoke the real internal publisher/retention boundary in the same explicitly isolated test environment. */
function control(action: 'base' | 'complete' | 'withdraw') {
  execFileSync(resolve('../.venv/bin/python'), ['-m', 'backend.tests.control_history_browser', action], { cwd: resolve('..'), stdio: 'pipe' });
}

test('late commit, future boundaries and expired detail preserve API/chart/table evidence', async ({ page, context }) => {
  const { password } = consumptionFixture();
  /** Keep browser Date aligned with the same fixed server instant; real timers still drive network/rendering. */
  async function setTime(value: string) {
    time(value);
    await page.clock.setFixedTime(new Date(value));
  }
  /** Existing006 credentials were renewed by consumption.spec.ts before this independent harness run. */
  async function login() {
    await page.goto('/ingreso/');
    await page.getByLabel('Correo', { exact: true }).fill('operator-active@example.test');
    await page.getByLabel('Contraseña', { exact: true }).fill(password + ' renewed');
    await page.getByRole('button', { name: 'Ingresar', exact: true }).click();
    await expect(page).toHaveURL(/\/cuenta\/$/);
    await page.getByRole('link', { name: 'Consumo', exact: true }).click();
  }
  /** Submit explicit offset boundaries and await a completed matching capture. */
  async function period(start: string, end: string) {
    await page.getByLabel('Inicio con offset', { exact: true }).fill(start);
    await page.getByLabel('Fin con offset', { exact: true }).fill(end);
    await page.getByRole('button', { name: 'Consultar período' }).click();
  }
  await setTime('2026-12-01T12:00:00Z'); control('base');
  await login();
  await page.getByRole('combobox', { name: 'Categoría', exact: true }).selectOption('CAT-05');
  await page.getByRole('combobox', { name: 'Agrupación', exact: true }).selectOption('hour');
  await period('2026-02-01T00:00:00-03:00', '2026-02-01T01:00:00-03:00');
  await expect(page.getByRole('cell', { name: '3 kWh', exact: true })).toBeVisible();
  await expect(page.getByRole('cell', { name: /75 %/ })).toBeVisible();
  await setTime('2026-12-01T12:15:00Z'); control('complete');
  await page.getByRole('button', { name: 'Actualizar consumo', exact: true }).click();
  await expect(page.getByRole('cell', { name: /100 %/ })).toBeVisible();
  await expect(page.locator('[role="graphics-symbol"]')).toHaveAttribute('aria-label', /3 kWh.*100 %/);
  // Delay an actual API response for A, then select empty B; A cannot overwrite the current selection.
  let release!: () => void, arrived!: () => void, finished!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  const received = new Promise<void>(resolve => { arrived = resolve; });
  const completed = new Promise<void>(resolve => { finished = resolve; });
  const pattern = '**/consumption/categories/CAT-05/aggregates?**';
  await page.route(pattern, async route => {
    const response = await route.fetch(); arrived(); await held;
    await route.fulfill({ response }); finished();
  });
  await page.getByRole('button', { name: 'Actualizar consumo', exact: true }).click();
  await received;
  await page.getByRole('combobox', { name: 'Categoría', exact: true }).selectOption('CAT-03');
  await expect(page.getByRole('cell', { name: '—', exact: true })).toBeVisible();
  release(); await completed;
  await expect(page.getByRole('cell', { name: '—', exact: true })).toBeVisible();
  await page.unroute(pattern);
  await page.getByRole('combobox', { name: 'Categoría', exact: true }).selectOption('CAT-05');
  await expect(page.getByRole('cell', { name: '3 kWh', exact: true })).toBeVisible();
  let fail = true;
  await page.route(pattern, route => { if (fail) { fail = false; return route.abort(); } return route.continue(); });
  await page.getByRole('button', { name: 'Actualizar consumo', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Reintentar', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Reintentar', exact: true }).click();
  await expect(page.getByRole('cell', { name: '3 kWh', exact: true })).toBeVisible();
  await page.unroute(pattern);
  await period('2026-12-01T10:00:00-03:00', '2026-12-01T11:00:00-03:00');
  await expect(page.getByRole('cell', { name: 'Aún no iniciado', exact: true })).toBeVisible();
  await setTime('2026-12-01T13:00:00Z');
  // The old session has expired;006 requires reauthentication before any new capture.
  await page.reload(); await login();
  await page.getByRole('combobox', { name: 'Categoría', exact: true }).selectOption('CAT-05');
  await page.getByRole('combobox', { name: 'Agrupación', exact: true }).selectOption('hour');
  await period('2026-12-01T10:00:00-03:00', '2026-12-01T11:00:00-03:00');
  await expect(page.getByRole('cell', { name: 'En curso', exact: true })).toBeVisible();
  await setTime('2026-12-01T14:00:00Z'); await page.reload(); await login();
  await page.getByRole('combobox', { name: 'Categoría', exact: true }).selectOption('CAT-05');
  await page.getByRole('combobox', { name: 'Agrupación', exact: true }).selectOption('hour');
  await period('2026-12-01T10:00:00-03:00', '2026-12-01T11:00:00-03:00');
  await expect(page.getByRole('cell', { name: 'Terminado', exact: true })).toBeVisible();
  await expect(page.getByRole('cell', { name: '—', exact: true })).toBeVisible();
  await setTime('2027-12-02T14:00:00Z'); control('withdraw'); await page.reload(); await login();
  await page.getByRole('combobox', { name: 'Categoría', exact: true }).selectOption('CAT-05');
  await page.getByRole('combobox', { name: 'Agrupación', exact: true }).selectOption('hour');
  await period('2026-02-01T00:00:00-03:00', '2026-02-01T01:00:00-03:00');
  await expect(page.getByRole('cell', { name: '3 kWh', exact: true })).toBeVisible();
  await expect(page.getByText('Detalle retirado; el agregado conserva sus aportes históricos.', { exact: true }).first()).toBeVisible();
  await page.getByRole('combobox', { name: 'Agrupación', exact: true }).selectOption('detail');
  await expect(page.locator('tbody tr')).toHaveCount(0);
  await expect(page.getByText(/Detalle retirado; los agregados conservan/)).toBeVisible();
  expect((await context.request.get('/api/v1/consumption/catalog')).status()).toBe(200);
});
