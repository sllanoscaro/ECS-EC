/** Real manual bills, signed exclusions and explicit comparison revisions through the004 browser forms. */
import { expect, test } from "@playwright/test";
import { loginCosts } from "./costs.helpers";

test.skip(!process.env.COSTS_E2E, "Requires the separate renewed synthetic costs fixture.");
test("manual bill, explicit contrast, correction, historical replay and zero denominator", async ({ page }) => {
  await loginCosts(page);
  await page.getByRole("button", { name: "Nueva boleta", exact: true }).click();
  await page.getByLabel("Identificador de boleta", { exact: true }).fill(`synthetic-${Date.now()}`);
  await page.getByLabel("Emisión con offset", { exact: true }).fill("2026-01-02T00:00:00Z");
  await page.getByLabel("Referencia del documento", { exact: true }).fill("synthetic:bill");
  await page.getByLabel("Total a pagar de boleta (CLP)", { exact: true }).fill("99950");
  await page.getByRole("button", { name: "Añadir concepto", exact: true }).click();
  await page.getByLabel("Código de concepto 1", { exact: true }).fill("energy");
  await page.getByLabel("Descripción 1", { exact: true }).fill("Energía sintética");
  await page.getByLabel("Importe CLP 1", { exact: true }).fill("100000");
  await page.getByRole("button", { name: "Añadir concepto", exact: true }).click();
  await page.getByLabel("Código de concepto 2", { exact: true }).fill("credit");
  await page.getByLabel("Descripción 2", { exact: true }).fill("Abono ajeno al ciclo");
  await page.getByLabel("Importe CLP 2", { exact: true }).fill("-50");
  await page.getByRole("combobox", { name: /^Relación con ciclo 2/ }).selectOption("outside_cycle");
  const firstResponse = page.waitForResponse(r => r.url().endsWith("/costs/bills") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Confirmar boleta", exact: true }).click();
  const bill = await (await firstResponse).json();
  expect(bill.revision).toBe(1);
  await expect(page.getByText("Contraste pendiente para estas revisiones", { exact: true })).toBeVisible();
  await page.getByRole("combobox", { name: /^Revisión de boleta para contrastar/ }).selectOption(bill.bill_revision_id);
  const comparisonResponse = page.waitForResponse(r => r.url().endsWith("/costs/comparisons") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Confirmar contraste", exact: true }).click();
  const comparison = await (await comparisonResponse).json();
  expect(comparison.delta_amount).toBe("0");
  expect(comparison.total_payable).toBe("99950");
  await expect(page.getByLabel("Conceptos excluidos").getByText(/credit: -50 CLP/)).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Contraste registrado").getByText("Diferencia: 0 CLP · Porcentaje: 0 %", { exact: true })).toBeVisible();
  await page.getByRole("listitem").filter({ hasText: bill.external_identifier }).getByRole("button", { name: "Corregir boleta revisión 1", exact: true }).click();
  await page.getByLabel("Importe CLP 1", { exact: true }).fill("90000");
  await page.getByLabel("Total a pagar de boleta (CLP)", { exact: true }).fill("89950");
  const correctionResponse = page.waitForResponse(r => r.url().includes(`/costs/bills/${bill.id}`) && r.request().method() === "PUT");
  await page.getByRole("button", { name: "Confirmar boleta", exact: true }).click();
  const corrected = await (await correctionResponse).json();
  expect(corrected.revision).toBe(2);
  await expect(page.getByText("Contraste pendiente para estas revisiones", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Contraste registrado")).toHaveCount(0);
  await page.getByRole("combobox", { name: /^Revisión de boleta para contrastar/ }).selectOption(corrected.bill_revision_id);
  await page.getByRole("button", { name: "Confirmar contraste", exact: true }).click();
  await expect(page.getByLabel("Contraste registrado").getByText("Diferencia: 10000 CLP · Porcentaje: 11.111111 %", { exact: true })).toBeVisible();
  expect((await (await page.request.get(`/api/v1/costs/comparisons/${comparison.id}`)).json()).delta_amount).toBe("0");
  await page.getByLabel("Importe CLP 1", { exact: true }).fill("0");
  await page.getByLabel("Total a pagar de boleta (CLP)", { exact: true }).fill("-50");
  const zeroResponse = page.waitForResponse(r => r.url().includes(`/costs/bills/${bill.id}`) && r.request().method() === "PUT");
  await page.getByRole("button", { name: "Confirmar boleta", exact: true }).click();
  const zero = await (await zeroResponse).json();
  await page.getByRole("combobox", { name: /^Revisión de boleta para contrastar/ }).selectOption(zero.bill_revision_id);
  await page.getByRole("button", { name: "Confirmar contraste", exact: true }).click();
  await expect(page.getByLabel("Contraste registrado").getByText(/Porcentaje: No aplica/)).toBeVisible();
});

test("operator sees persisted contrast without mutation forms", async ({ page }) => {
  await loginCosts(page, "operator");
  await expect(page.getByRole("button", { name: "Confirmar boleta", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Confirmar contraste", exact: true })).toHaveCount(0);
  expect((await page.request.post("/api/v1/costs/comparisons", { data: {} })).status()).toBe(403);
});

test("a lost bill response preserves fields and replays one durable revision", async ({ page }) => {
  await loginCosts(page);
  await page.getByRole("button", { name: "Nueva boleta", exact: true }).click();
  const identifier = `synthetic-retry-${Date.now()}`;
  await page.getByLabel("Identificador de boleta", { exact: true }).fill(identifier);
  await page.getByLabel("Emisión con offset", { exact: true }).fill("2026-01-02T00:00:00Z");
  await page.getByLabel("Referencia del documento", { exact: true }).fill("synthetic:retry");
  await page.getByLabel("Total a pagar de boleta (CLP)", { exact: true }).fill("100000");
  const keys: string[] = [];
  await page.route("**/api/v1/costs/bills", async route => {
    /** Let the real server commit, then lose only the first response; the next request must replay that identity. */
    if (route.request().method() !== "POST") { await route.continue(); return; }
    keys.push(route.request().headers()["idempotency-key"]);
    if (keys.length === 1) { expect((await route.fetch()).status()).toBe(201); await route.abort("failed"); }
    else await route.continue();
  });
  await page.getByRole("button", { name: "Confirmar boleta", exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByLabel("Identificador de boleta", { exact: true })).toHaveValue(identifier);
  const replay = page.waitForResponse(r => r.url().endsWith("/costs/bills") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Confirmar boleta", exact: true }).click();
  const document = await (await replay).json();
  expect(document.revision).toBe(1); expect(keys[0]).toBe(keys[1]);
  const revisions = await (await page.request.get(`/api/v1/costs/bills?cycle_id=${document.cycle_id}&limit=100`)).json();
  expect(revisions.items.filter((value: { id: string }) => value.id === document.id)).toHaveLength(1);
});
