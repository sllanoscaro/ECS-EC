/**001:T056 reads the actual003-derived series and008 delivery URLs; no intercepted responses. */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";

test.skip(!process.env.CONSUMPTION_LOCAL_BROWSER_EXPECTED, "Requires the exclusive001:T056 backend harness.");
test.use({ timezoneId: "Asia/Tokyo" });

test("SFTP intervals agree in API, graph and table and captured mail links retain authorization", async ({ page }) => {
  /**Private fixture files contain synthetic expectations/password; product URLs cannot create data or change time. */
  const expected = JSON.parse(readFileSync(process.env.CONSUMPTION_LOCAL_BROWSER_EXPECTED!, "utf8"));
  const password = readFileSync(process.env.IDENTITY_E2E_PASSWORD_FILE!, "utf8");
  // Match only this private fixture's Date to the injected006 clock; timers and all network I/O remain real.
  await page.clock.setFixedTime(new Date(expected.business_now));
  await page.goto("/ingreso/");
  await page.getByLabel("Correo electrónico", { exact: true }).fill("local-chain-operator@example.test");
  await page.getByLabel("Contraseña", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
  await expect(page).not.toHaveURL(/\/ingreso\//);
  await page.goto("/consumption/");
  await page.getByRole("combobox", { name: "Categoría", exact: true }).selectOption("CAT-03");
  await page.getByRole("button", { name: "Consultar", exact: true }).click();
  const rows = page.locator("tbody tr:not(.consumption-day-divider)");
  await expect(rows).toHaveCount(2);
  await expect(page.locator('[role="graphics-symbol"]')).toHaveCount(2);
  for (const [index, row] of expected.rows.entries()) {
    await expect(rows.nth(index).locator("td").nth(2)).toHaveText("4,0 kWh");
    await expect(rows.nth(index).locator("td").nth(2)).toHaveAttribute("title", "4");
    const symbol = page.locator('[role="graphics-symbol"]').nth(index);
    expect(await symbol.getAttribute("aria-label")).toContain(row.start);
    expect(await symbol.getAttribute("aria-label")).toContain(row.end);
    expect(await symbol.getAttribute("aria-label")).toContain("4 kWh");
  }
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(rows).toHaveCount(2);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: join(process.env.CONSUMPTION_LOCAL_BROWSER_ARTIFACTS!, `consumption-${process.env.CONSUMPTION_LOCAL_BROWSER_FORMAT}-${width}.png`), fullPage: true, animations: "disabled" });
  }
  await page.getByRole("combobox", { name: "Categoría", exact: true }).selectOption("CAT-05");
  await page.getByRole("button", { name: "Consultar", exact: true }).click();
  await expect(page.getByText("Sin datos", { exact: true })).toBeVisible();
  await expect(rows).toHaveCount(0);
  for (const link of expected.delivery_links) {
    await page.goto(link);
    await expect(page.getByRole("article")).toBeVisible();
    await expect(page.getByRole("article").getByText("Aceptada por el servicio", { exact: true })).toBeVisible();
    await expect(page.getByText(/Correo local de prueba · aceptación por el capturador/)).toBeVisible();
  }
  await page.context().clearCookies();
  await page.goto(expected.delivery_links[0]);
  await expect(page.getByRole("link", { name: "iniciar sesión", exact: true })).toBeVisible();
  await expect(page.getByRole("article")).toHaveCount(0);
  expect((await page.request.get(`/api/v1/notifications/deliveries/${expected.delivery_ids[0]}`)).status()).toBe(401);
  await page.getByRole("link", { name: "iniciar sesión", exact: true }).click();
  await expect(page).toHaveURL(/\/ingreso\//);
});
