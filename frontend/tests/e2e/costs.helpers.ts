/** Ordinary006 browser login and CSRF-bound financial operations against isolated synthetic fixtures. */
import { readFileSync } from "node:fs";
import { expect, type Page } from "@playwright/test";

/** Authenticate an already renewed synthetic account via the public login form. */
export async function loginCosts(page: Page, role = "admin") {
  const password = readFileSync(process.env.IDENTITY_E2E_PASSWORD_FILE!, "utf8").replace(/\n$/, "") + " renewed";
  await page.goto("/ingreso/");
  await page.getByLabel("Correo", { exact: true }).fill(`${role}-active@example.test`);
  await page.getByLabel("Contraseña", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
  await expect(page).toHaveURL(/\/cuenta\/$/);
  await page.goto(role === "admin" ? "/administracion/costos/" : "/costos/");
  const cycles = await (await page.request.get("/api/v1/costs/cycles")).json();
  const reference = cycles.items.find((item: { start_at: string; end_at: string }) => item.start_at === "2026-01-01T00:00:00Z" && item.end_at === "2026-01-01T01:00:00Z");
  await page.goto((role === "admin" ? "/administracion/costos/" : "/costos/") + `?calculation=${reference.calculation.id}`);
  await expect(page.getByRole("heading", { name: /Cálculo · Revisión/ })).toBeVisible();
}

/** Submit a public API mutation using only cookies issued by the real006 login and a new explicit operation key. */
export async function mutate(page: Page, path: string, data: unknown, method = "POST", extra: Record<string, string> = {}) {
  const session = await (await page.request.get("/api/v1/auth/session")).json();
  const csrf = session.csrf_token;
  const response = await page.request.fetch(`/api/v1/costs/${path}`, { method, data,
    headers: { Origin: new URL(page.url()).origin, "X-CSRF-Token": csrf ?? "", "Idempotency-Key": crypto.randomUUID(), ...extra } });
  return response;
}
