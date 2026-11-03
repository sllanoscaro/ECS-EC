/** Review the login in Chromium using browser-only synthetic responses, never real credentials.
 * Run against local Next dev with `node scripts/review-login.mjs [output-directory]`.
 * Captures responsive/error states and verifies redirects; this does not test server authentication.
 */
import { chromium, expect } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const baseURL = process.env.UI_REVIEW_URL ?? 'http://127.0.0.1:3000';
if (!['localhost', '127.0.0.1', '[::1]'].includes(new URL(baseURL).hostname)) throw new Error('Use a local preview server.');
const output = resolve(process.argv[2] ?? 'test-results/login-review');
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
const results = [];
const session = { account: { id: 'synthetic', email: 'review@example.test', role: 'operador' }, session_state: 'normal', must_change_password: false, csrf_token: 'synthetic', absolute_expires_at: '2099-01-01T00:00:00Z', idle_expires_at: '2099-01-01T00:00:00Z', permissions: ['consumption.read', 'costs.read'] };

/** Inspect one isolated scenario, intercepting every API request before it can reach a backend. */
async function review(name, width, height, state = 'empty', destination) {
  const context = await browser.newContext({ viewport: { width, height }, reducedMotion: 'reduce' });
  const page = await context.newPage();
  const errors = [], submissions = [];
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  page.on('pageerror', error => errors.push(error.message));
  await context.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname;
    const reply = (body, status = 200, headers = {}) => route.fulfill({ status, contentType: 'application/json', headers, body: JSON.stringify(body) });
    if (path.endsWith('/auth/session')) {
      if (state === 'checking') await gate;
      return state === 'authenticated' ? reply(session) : reply({ code: 'session_required', detail: 'Debe iniciar sesión.' }, 401);
    }
    if (path.endsWith('/auth/csrf')) return reply({ csrf_token: 'synthetic' });
    if (path.endsWith('/auth/login')) {
      submissions.push(route.request().postDataJSON());
      expect(route.request().headers()['x-csrf-token']).toBe('synthetic');
      if (state === 'busy') await gate;
      if (state === 'limited') return reply({ code: 'rate_limited', detail: 'Demasiados intentos. Espere antes de volver a ingresar.' }, 429, { 'Retry-After': '30' });
      if (destination) return reply({ ...session, must_change_password: destination === '/cuenta/', session_state: destination === '/cuenta/' ? 'password_change_required' : 'normal' });
      return reply({ code: 'invalid_credentials', detail: 'No fue posible ingresar con esas credenciales.' }, 401);
    }
    return reply({ code: 'synthetic_unavailable', detail: 'No se consultan datos privados en esta revisión.' }, 503);
  });
  try {
    await page.goto(`${baseURL}/ingreso/${destination === '/costos/' ? '?retorno=/costos/' : ''}`);
    if (state === 'checking') await expect(page.getByRole('status')).toHaveText('Comprobando sesión…');
    else if (state === 'authenticated') await expect(page.getByRole('link', { name: 'Ir a mi cuenta' })).toBeVisible();
    else {
      await expect(page.getByLabel('Correo electrónico')).toBeVisible();
      if (['invalid', 'limited', 'busy'].includes(state) || destination) {
        await page.getByLabel('Correo electrónico').fill('review@example.test');
        await page.getByLabel('Contraseña').fill('  synthetic password  ');
        await page.getByRole('button', { name: 'Ingresar', exact: true }).click();
        if (destination) {
          await expect(page).toHaveURL(`${baseURL}${destination}`);
          expect(submissions).toEqual([{ email: 'review@example.test', password: '  synthetic password  ' }]);
          results.push({ name, destination, status: 'passed', errors });
          return;
        }
        if (state === 'busy') await expect(page.getByRole('button', { name: 'Ingresando…' })).toBeDisabled();
        else {
          await expect(page.getByRole('alert')).toBeVisible();
          await expect(page.getByLabel('Contraseña')).toHaveValue('');
          await expect(page.getByLabel('Correo electrónico')).toHaveValue('review@example.test');
          if (state === 'limited') await expect(page.getByRole('button', { name: 'Ingresar', exact: true })).toBeDisabled();
        }
      }
    }
    await page.evaluate(() => document.fonts.ready);
    await expect(page.locator('aside, .mobile-header')).toHaveCount(0);
    await page.screenshot({ path: resolve(output, `${name}.png`), fullPage: true });
    const metrics = await page.evaluate(() => {
      const panel = document.querySelector('.login-panel').getBoundingClientRect();
      const email = document.querySelector('#login-email');
      return { width: innerWidth, height: innerHeight, scrollWidth: document.documentElement.scrollWidth, scrollHeight: document.documentElement.scrollHeight, panel: { x: panel.x, y: panel.y, width: panel.width, height: panel.height }, font: getComputedStyle(document.body).fontFamily, fieldHeight: email?.getBoundingClientRect().height, alertColor: document.querySelector('[role=alert]') ? getComputedStyle(document.querySelector('[role=alert]')).color : null };
    });
    expect(metrics.scrollWidth).toBe(width);
    expect(Math.abs(metrics.panel.x + metrics.panel.width / 2 - width / 2)).toBeLessThan(1);
    expect(metrics.panel.y).toBeGreaterThanOrEqual(0);
    expect(errors).toEqual([]);
    if (state === 'empty') {
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      await expect(page.getByLabel('Correo electrónico')).toBeFocused();
      await page.keyboard.press('Tab');
      await expect(page.getByLabel('Contraseña')).toBeFocused();
      await page.keyboard.press('Tab');
      await expect(page.getByRole('button', { name: 'Ingresar', exact: true })).toBeFocused();
    }
    results.push({ name, state, status: 'passed', ...metrics, errors });
    console.log(`${name}: ${width}px, overflow ${metrics.scrollWidth - width}px, errors ${errors.length}`);
  } finally { release(); await context.close(); }
}

try {
  await review('desktop', 1440, 1000);
  await review('comp-desktop', 1568, 1003);
  await review('tablet', 768, 1024);
  await review('mobile', 390, 844);
  await review('short-mobile', 320, 520);
  await review('invalid-mobile', 390, 844, 'invalid');
  await review('limited-mobile', 390, 844, 'limited');
  await review('busy-mobile', 390, 844, 'busy');
  await review('checking-mobile', 390, 844, 'checking');
  await review('authenticated-mobile', 390, 844, 'authenticated');
  await review('default-redirect', 1440, 1000, 'empty', '/');
  await review('return-redirect', 1440, 1000, 'empty', '/costos/');
  await review('renewal-redirect', 1440, 1000, 'empty', '/cuenta/');
} finally {
  await browser.close();
  await writeFile(resolve(output, 'results.json'), JSON.stringify({ data: 'browser-only synthetic fixtures; no backend authentication tested', results }, null, 2));
}
