/** Real004 calculation/recurrence, durable reload and006 permissions on isolated001/002 physical fixtures. */
import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";

test.skip(!process.env.COSTS_E2E, "Requires scripts/seed_costs_reference.py on a separate synthetic database.");
for (const role of ["admin", "operator"]) {
  test(`${role} reads exact costs and respects explicit mutation permissions`, async ({ page, context }) => {
    /** Use ordinary login and password renewal, never a special authentication or calculation fixture endpoint. */
    const initial = readFileSync(process.env.IDENTITY_E2E_PASSWORD_FILE!, "utf8").replace(/\n$/, "");
    await page.goto("/ingreso/");
    await page.getByLabel("Correo", { exact: true }).fill(`${role}-active@example.test`);
    await page.getByLabel("Contraseña", { exact: true }).fill(process.env.COSTS_E2E_RENEWED ? initial + " renewed" : initial);
    await page.getByRole("button", { name: "Ingresar", exact: true }).click();
    await expect(page).toHaveURL(/\/cuenta\/$/);
    if (!process.env.COSTS_E2E_RENEWED) {
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
    if (role === "admin") {
      await page.getByRole("link", { name: "Administrar costos", exact: true }).click();
      await expect(page.getByLabel("Inicio del ciclo con offset", { exact: true })).toBeVisible();
      await page.getByLabel("Inicio del ciclo con offset", { exact: true }).fill("2026-01-01T00:00:00Z");
      await page.getByLabel("Fin del ciclo con offset", { exact: true }).fill("2026-01-01T01:00:00Z");
      if (await page.getByLabel("Motivo del recálculo", { exact: true }).getAttribute("required") !== null) {
        await page.getByLabel("Motivo del recálculo", { exact: true }).fill("Synthetic resumed calculation");
      }
      await page.getByLabel("Mes de demanda documentado (opcional)", { exact: true }).fill("2026-01");
      await page.getByLabel("Referencia documental del mes", { exact: true }).fill("synthetic:month:2026-01");
      const createdResponse = page.waitForResponse(response => response.url().endsWith("/api/v1/costs/calculations") && response.request().method() === "POST");
      await page.getByRole("button", { name: "Confirmar cálculo", exact: true }).click();
      const created = await (await createdResponse).json();
      await expect(page.getByRole("heading", { name: /Cálculo · Revisión/ })).toContainText(`Revisión ${created.revision}`);
      await expect(page.getByText("Costo completo: 100000 CLP", { exact: true })).toBeVisible();
      await expect(page.getByText("Mes de demanda: 2026-01", { exact: true })).toBeVisible();
      const first = page.url();
      const firstRevision = created.revision as number;
      await page.reload();
      await expect(page.getByText("Costo completo: 100000 CLP", { exact: true })).toBeVisible();
      await page.getByLabel("Motivo del recálculo", { exact: true }).fill("Synthetic recheck");
      await page.getByRole("button", { name: "Confirmar cálculo", exact: true }).click();
      await expect(page.getByRole("heading", { name: /Cálculo · Revisión/ })).toContainText(`Revisión ${firstRevision + 1}`);
      expect(page.url()).not.toBe(first);
    } else {
      await page.goto("/administracion/costos/");
      await expect(page.getByText("Acceso denegado.", { exact: true })).toBeVisible();
      expect((await context.request.post("/api/v1/costs/calculations", { data: {} })).status()).toBe(403);
      const cycles = await (await context.request.get("/api/v1/costs/cycles")).json();
      const reference = cycles.items.find((item: { end_at: string }) => item.end_at === "2026-01-01T01:00:00Z");
      await page.goto(`/costos/?calculation=${reference.calculation.id}`);
      await expect(page.getByText("Costo completo: 100000 CLP", { exact: true })).toBeVisible();
      await expect(page.getByRole("button", { name: "Confirmar cálculo", exact: true })).toHaveCount(0);
    }
    await expect(page.locator('section[aria-label="Resultado del cálculo"]').getByRole("cell", { name: "100000 CLP", exact: true })).toBeVisible();
    await expect(page.locator('section[aria-label="Resultado del cálculo"] [role="graphics-symbol"]')).toHaveAttribute("aria-label", "energy: 100000 CLP");
  });
}
