/**007: opt-in real technical Viewer checks; functional/person coverage remains explicit. */
import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, resolve } from "node:path";

test.describe("external observability", () => {
  test.skip(!process.env.OBS_E2E_PASSWORD_FILE, "Requires provisioned test gateway, trusted CA and external technical password file.");
  test("Viewer dashboard and denied administration", async ({ browser }) => {
    /** Authenticate only to the technical origin; every request still passes gateway Basic. */
    test.setTimeout(120000);
    const password = readFileSync(process.env.OBS_E2E_PASSWORD_FILE!, "utf8").trim();
    const context = await browser.newContext({
      baseURL: process.env.OBS_E2E_URL ?? "https://localhost:3444",
      ignoreHTTPSErrors: false,
      httpCredentials: { username: "prog-test-01", password },
    });
    const page = await context.newPage();
    await page.goto("/grafana/d/ecs-platform/platform");
    await expect(page.getByText("ECS-EC — observabilidad técnica").first()).toBeVisible({ timeout: 30000 });
    expect((await context.request.get("/grafana/api/admin/users")).status()).toBe(403);
    expect((await context.request.get("/jaeger/api/v3/services")).status()).toBe(200);
    await expect(page.getByText("Eventos técnicos observados — UTC", { exact: true })).toBeVisible();
    if (process.env.OBS_E2E_REFERENCE_FILE) {
      const fixture = JSON.parse(readFileSync(process.env.OBS_E2E_REFERENCE_FILE, "utf8"));
      await page.goto("/jaeger/trace/" + fixture.references[0].trace_id);
      await expect(page.getByText("consumption.query_detail").first()).toBeVisible({ timeout: 30000 });
    }
    await context.close();
  });
});

test("functional navigation retains006 permissions without a technical viewer", async ({ browser }) => {
  /** Exercise real functional sessions independently of technical Basic; no TLS bypass. */
  test.skip(!process.env.OBS_FUNCTIONAL_PASSWORD_FILE, "Requires real006 test accounts and monolith; missing providers are not simulated.");
  test.setTimeout(90000);
  const password = readFileSync(process.env.OBS_FUNCTIONAL_PASSWORD_FILE!, "utf8").trim();
  for (const role of ["admin", "operator"]) {
    const context = await browser.newContext({ baseURL: process.env.OBS_FUNCTIONAL_BASE_URL, ignoreHTTPSErrors: false });
    const page = await context.newPage();
    await page.goto("/ingreso/");
    await page.getByLabel("Correo", { exact: true }).fill(`obs-${role}@example.test`);
    await page.getByLabel("Contraseña", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Ingresar", exact: true }).click();
    await expect(page).toHaveURL(/\/cuenta\/$/);
    await expect(page.getByRole("link", { name: /observabilidad|grafana|jaeger/i })).toHaveCount(0);
    if (role === "admin") {
      await page.getByRole("link", { name: "Historial", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Historial administrativo", exact: true })).toBeVisible();
      expect((await context.request.get("/api/v1/identity/administration-history")).status()).toBe(200);
    } else {
      await expect(page.getByRole("link", { name: "Historial", exact: true })).toHaveCount(0);
    }
    const cookie = (await context.cookies()).map(c => `${c.name}=${c.value}`).join("; ");
    const response = await context.request.get((process.env.OBS_E2E_URL ?? "https://localhost:3444") + "/grafana/", { headers: { Cookie: cookie } });
    expect(response.status()).toBe(401);
    await context.close();
  }
});

test("revocation denies subsequent UI resources with previous cookies", async ({ browser }) => {
  /** Revoke through the external host CLI; restore only the explicit synthetic test identity. */
  test.skip(!process.env.OBS_E2E_PASSWORD_FILE || !process.env.OBS_TEST_ROOT, "Requires a dedicated test registry owned by this harness.");
  const root = process.env.OBS_TEST_ROOT!;
  if (readFileSync(resolve(root, "environment"), "utf8").trim() !== "test") throw Error("Test resource root required");
  const password = readFileSync(process.env.OBS_E2E_PASSWORD_FILE!, "utf8").trim();
  const context = await browser.newContext({ baseURL: process.env.OBS_E2E_URL ?? "https://localhost:3444",
    ignoreHTTPSErrors: false, httpCredentials: { username: "prog-test-01", password } });
  try {
    expect((await context.request.get("/jaeger/api/v3/services")).status()).toBe(200);
    execFileSync("bash", [resolve("../scripts/observability/manage_programmer.sh"), "revoke", "--environment", "test",
      "--subject", "prog-test-01", "--root", dirname(root)], { stdio: "pipe" });
    await context.addCookies([{ name: "grafana_session", value: "previous", domain: "localhost", path: "/", secure: true }]);
    expect((await context.request.get("/jaeger/api/v3/services")).status()).toBe(401);
    const page = await context.newPage();
    expect((await page.goto("/grafana/"))?.status()).toBe(401);
  } finally {
    // Private fixture seam only: plaintext remains on stdin, never argv/env/output.
    const code = "import json,sys; from pathlib import Path; from scripts.observability.manage_programmer import update; d=json.load(sys.stdin); update(Path(d['root']).parent,'test','prog-test-01','grant',d['password'].encode())";
    execFileSync(resolve("../.venv/bin/python"), ["-c", code], { cwd: resolve(".."),
      input: JSON.stringify({ root, password }), stdio: ["pipe", "pipe", "pipe"] });
    await context.close();
  }
});
