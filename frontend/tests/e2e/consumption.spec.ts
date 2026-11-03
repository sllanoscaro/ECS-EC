/** Browser acceptance against the real monolith/002 reception fixtures, with no public seed endpoint. */
import { consumptionFixture } from "./consumption.setup";
import { expect, test } from "@playwright/test";
import type { DetailResult, AggregateQueryResult } from "../../src/lib/api/consumption";

test.use({ timezoneId: "Asia/Tokyo" });
test.skip(!process.env.CONSUMPTION_E2E_MODE, "Requires isolated seeded001/002 fixtures; identity's fixtures alone are insufficient.");

for (const role of ["admin", "operator"]) {
  test(`${role} sees the same exact API intervals in graph/table and preserves filters`, async ({ page, context }) => {
    /** First renewal uses006's real form; reruns authenticate the renewed credential after a process/DB restart. */
    const { password: initial } = consumptionFixture();
    await page.goto("/ingreso/");
    await page.getByLabel("Correo", { exact: true }).fill(`${role}-active@example.test`);
    await page.getByLabel("Contraseña", { exact: true }).fill(process.env.CONSUMPTION_E2E_RENEWED ? initial + " renewed" : initial);
    await page.getByRole("button", { name: "Ingresar", exact: true }).click();
    await expect(page).toHaveURL(/\/cuenta\/$/);
    if (!process.env.CONSUMPTION_E2E_RENEWED) {
      await page.getByLabel("Contraseña actual", { exact: true }).fill(initial);
      await page.getByLabel("Nueva contraseña", { exact: true }).fill(initial + " renewed");
      await page.getByLabel("Confirmar nueva contraseña", { exact: true }).fill(initial + " renewed");
      await page.getByRole("button", { name: "Cambiar contraseña", exact: true }).click();
      await expect(page).toHaveURL(/\/ingreso\/$/);
      await page.getByLabel("Correo", { exact: true }).fill(`${role}-active@example.test`);
      await page.getByLabel("Contraseña", { exact: true }).fill(initial + " renewed");
      await page.getByRole("button", { name: "Ingresar", exact: true }).click();
      await expect(page).toHaveURL(/\/cuenta\/$/);
    }
    await page.getByRole("link", { name: "Consumo", exact: true }).click();
    await expect(page.getByRole("combobox", { name: "Categoría", exact: true })).toBeVisible();
    await expect(page.getByRole("table")).toBeVisible();
    expect(await page.getByRole("combobox", { name: "Categoría", exact: true }).locator("option").count()).toBe(7);
    const selectedStart = await page.getByLabel("Inicio con offset", { exact: true }).inputValue();
    const apiResponse = await context.request.get("/api/v1/consumption/catalog");
    expect(apiResponse.headers()["cache-control"]).toBe("no-store");
    const catalog = await apiResponse.json();
    for (const category of ["CAT-01", "CAT-02", "CAT-03", "CAT-04", "CAT-05", "CAT-06", "CAT-07"] as const) {
      await page.getByRole("combobox", { name: "Categoría", exact: true }).selectOption(category);
      await expect(page.getByLabel("Inicio con offset", { exact: true })).toHaveValue(selectedStart);
      const params = new URLSearchParams(catalog.default_period);
      const response = await context.request.get(`/api/v1/consumption/categories/${category}/detail?${params}`);
      expect(response.status()).toBe(200);
      const result = await response.json() as DetailResult;
      if (category === "CAT-01") expect(result.rows[0].energy_kwh).toBe(process.env.CONSUMPTION_E2E_MODE === "physical" ? "100" : "20");
      await expect(page.getByRole("heading", { level: 2 })).toContainText(result.category.name);
      await expect(page.getByText(({available:"Datos disponibles",no_meter:"Sin medidor",no_data:"Sin datos",incomplete:"Datos incompletos"})[result.state], {exact:true})).toBeVisible();
      await expect(page.locator("tbody tr")).toHaveCount(result.rows.length);
      await expect(page.locator('[role="graphics-symbol"]')).toHaveCount(result.rows.length);
      for (const [index, row] of result.rows.entries()) {
        await expect(page.getByRole("cell", { name: `${row.energy_kwh} kWh`, exact: true })).toBeVisible();
        const symbol = page.locator('[role="graphics-symbol"]').nth(index);
        expect(await symbol.getAttribute("aria-label")).toContain(row.start);
        expect(await symbol.getAttribute("aria-label")).toContain(row.end);
        expect(await symbol.getAttribute("aria-label")).toContain(`${row.energy_kwh} kWh`);
      }
    }
    await page.getByRole("combobox", { name: "Categoría", exact: true }).selectOption("CAT-05");
    await expect(page.locator("tbody tr")).toHaveCount(3);
    await expect(page.locator('[data-kind="zero"]')).toHaveCount(1);
    await expect(page.locator('[data-kind="subpixel-positive"]')).toHaveCount(1);
    await page.getByLabel("Inicio con offset", { exact: true }).fill("2026-01-03T00:00:00-03:00");
    await page.getByRole("button", { name: "Consultar período" }).click();
    await expect(page.getByText("Revise inicio y fin:", { exact: false })).toBeVisible();
    await expect(page.locator("tbody tr")).toHaveCount(3);
    await page.getByLabel("Inicio con offset", { exact: true }).fill("2026-01-01T00:15:00-03:00");
    await page.getByLabel("Fin con offset", { exact: true }).fill("2026-01-01T00:45:00-03:00");
    await page.getByRole("button", { name: "Consultar período" }).click();
    await expect(page.getByText("Se excluyeron intervalos que cruzan los límites.", { exact: false })).toBeVisible();
    await expect(page.locator("tbody tr")).toHaveCount(0);
    //001 periods preserve building offsets even while the browser runs in Tokyo.
    for (const [start, end] of [
      ["2025-12-30T00:00:00-03:00", "2025-12-31T00:00:00-03:00"],
      ["2026-01-03T00:00:00-03:00", "2026-01-04T00:00:00-03:00"],
      ["2025-04-05T23:00:00-03:00", "2025-04-05T23:00:00-04:00"],
    ]) {
      await page.getByLabel("Inicio con offset", { exact: true }).fill(start);
      await page.getByLabel("Fin con offset", { exact: true }).fill(end);
      const received = page.waitForResponse(r => r.url().includes("/CAT-05/detail?") && new URL(r.url()).searchParams.get("start") === start && r.status() === 200);
      await page.getByRole("button", { name: "Consultar período" }).click();
      const result = await (await received).json() as DetailResult;
      expect(result.period.start).toBe(start);
      expect(result.period.end).toBe(end);
      await expect(page.locator("tbody tr")).toHaveCount(0);
      await expect(page.locator('[role="graphics-symbol"]')).toHaveCount(0);
      await page.getByRole("combobox", { name: "Categoría", exact: true }).selectOption("CAT-03");
      await expect(page.getByLabel("Inicio con offset", { exact: true })).toHaveValue(start);
      await page.getByRole("combobox", { name: "Categoría", exact: true }).selectOption("CAT-05");
    }
    //002 grouping keeps the explicit filter/category and compares every block to the real API.
    await page.getByLabel("Inicio con offset", { exact: true }).fill("2026-01-01T00:00:00-03:00");
    await page.getByLabel("Fin con offset", { exact: true }).fill("2026-01-02T00:00:00-03:00");
    await page.getByRole("button", { name: "Consultar período" }).click();
    for (const granularity of ["hour", "day", "month", "year"] as const) {
      const end = granularity === "month" ? "2026-02-01T00:00:00-03:00" : granularity === "year" ? "2027-01-01T00:00:00-03:00" : "2026-01-02T00:00:00-03:00";
      await page.getByLabel("Fin con offset", { exact: true }).fill(end);
      await page.getByRole("button", { name: "Consultar período" }).click();
      await page.getByRole("combobox", { name: "Agrupación", exact: true }).selectOption(granularity);
      await expect(page.getByLabel("Inicio con offset", { exact: true })).toHaveValue("2026-01-01T00:00:00-03:00");
      for (const category of ["CAT-01", "CAT-02", "CAT-03", "CAT-04", "CAT-05", "CAT-06", "CAT-07"] as const) {
        const query = new URLSearchParams({start: "2026-01-01T00:00:00-03:00", end, timezone: "America/Santiago", granularity});
        await page.getByRole("combobox", { name: "Categoría", exact: true }).selectOption(category);
        const response = await context.request.get(`/api/v1/consumption/categories/${category}/aggregates?${query}`);
        expect(response.status()).toBe(200);
        const result = await response.json() as AggregateQueryResult;
        await expect(page.locator("tbody tr")).toHaveCount(result.blocks.length);
        await expect(page.locator('[role="graphics-symbol"]')).toHaveCount(result.blocks.length);
        for (const [index, block] of result.blocks.entries()) {
          const row = page.locator("tbody tr").nth(index);
          await expect(row.locator("td").nth(0)).toContainText(block.start);
          await expect(row.locator("td").nth(2)).toHaveText(block.energy_kwh === null ? "—" : `${block.energy_kwh} kWh`);
          const symbol = page.locator('[role="graphics-symbol"]').nth(index);
          await expect(symbol).toHaveAttribute("aria-label", new RegExp(block.energy_kwh === null ? "Sin datos" : `${block.energy_kwh} kWh`));
        }
      }
    }
    await page.goto("/administracion/consumo/");
    if (role === "operator") {
      await expect(page.getByText("Acceso denegado.", { exact: true })).toBeVisible();
      expect((await context.request.get("/api/v1/consumption/configuration")).status()).toBe(403);
    } else {
      await expect(page.getByRole("button", { name: "Guardar configuración" })).toBeVisible();
      await page.getByLabel("Etiqueta CAT-05", { exact: true }).fill("Synthetic browser label");
      await page.getByRole("button", { name: "Guardar configuración" }).click();
      await expect(page.getByText(/Configuración guardada/)).toBeVisible();
      await page.reload();
      await expect(page.getByLabel("Etiqueta CAT-05", { exact: true })).toHaveValue("Synthetic browser label");
    }
  });
}
