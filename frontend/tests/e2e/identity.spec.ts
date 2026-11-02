/** Real PostgreSQL/monolith flows with synthetic protected fixtures; no public clock or user fixture endpoint. */
import { readFileSync, writeFileSync } from "node:fs";
import { expect, test } from "@playwright/test";

test.use({ ignoreHTTPSErrors: true });

test("both profiles renew, administer accounts, read history and close across tabs", async ({ page, context, baseURL }) => {
  /** Exercise normal browser credentials/cookies; private setup comes from an explicit protected file. */
  const file = process.env.IDENTITY_E2E_PASSWORD_FILE;
  if (!file) throw new Error("Identity E2E requires protected synthetic fixture configuration");
  const initial = readFileSync(file, "utf8").replace(/\n$/, "");
  for (const role of ["admin", "operator"]) {
    await page.goto("/ingreso/");
    await page.getByLabel("Correo", { exact: true }).fill(`${role}-active@example.test`);
    await page.getByLabel("Contraseña", { exact: true }).fill(initial);
    await page.getByRole("button", { name: "Ingresar", exact: true }).click();
    await expect(page).toHaveURL(/\/cuenta\/$/);
    await expect(page.getByText("Debe renovar su contraseña inicial antes de continuar.")).toBeVisible();
    const cookies = await context.cookies();
    const cookie = cookies.find((value) => value.name === "ecs_ec_session");
    expect(cookie?.httpOnly).toBeTruthy();
    expect(cookie?.sameSite).toBe("Lax");
    expect(cookie?.secure).toBe(baseURL?.startsWith("https://"));
    await page.getByLabel("Contraseña actual", { exact: true }).fill(initial);
    await page.getByLabel("Nueva contraseña", { exact: true }).fill(initial+" renewed");
    await page.getByLabel("Confirmar nueva contraseña", { exact: true }).fill(initial+" renewed");
    await page.getByRole("button", { name: "Cambiar contraseña", exact: true }).click();
    await expect(page).toHaveURL(/\/ingreso\/$/);
    await page.getByLabel("Correo", { exact: true }).fill(`${role}-active@example.test`);
    await page.getByLabel("Contraseña", { exact: true }).fill(initial+" renewed");
    await page.getByRole("button", { name: "Ingresar", exact: true }).click();
    await expect(page).toHaveURL(/\/cuenta\/$/);
    await expect(page.getByRole("button", { name: "Cerrar sesión", exact: true })).toBeVisible();
    if (role === "admin") {
      await page.getByRole("link", { name: "Usuarios", exact: true }).click();
      await expect(page.getByRole("table", { name: "Cuentas registradas" })).toBeVisible();
      for (const [email, profile] of [["ui-new@example.test", "operador"], ["ui-admin@example.test", "administrador_tecnico"]]) {
        await page.getByRole("button", { name: "Nueva cuenta", exact: true }).click();
        await page.getByLabel("Correo", { exact: true }).fill(email);
        await page.getByRole("combobox", { name: "Perfil", exact: true }).selectOption(profile);
        await page.getByLabel("Contraseña inicial", { exact: true }).fill(initial);
        await page.getByLabel("Confirmar contraseña", { exact: true }).fill(initial);
        await page.getByRole("button", { name: "Crear cuenta", exact: true }).click();
        await expect(page.getByRole("row").filter({ hasText: email })).toBeVisible();
      }
      await page.getByRole("button", { name: "Nueva cuenta", exact: true }).click();
      await page.getByLabel("Correo", { exact: true }).fill("ui-new@example.test");
      await page.getByLabel("Contraseña inicial", { exact: true }).fill(initial);
      await page.getByLabel("Confirmar contraseña", { exact: true }).fill(initial);
      await page.getByRole("button", { name: "Crear cuenta", exact: true }).click();
      await expect(page.getByText("El correo ya está registrado.", { exact: true })).toBeVisible();
      await expect(page.getByLabel("Contraseña inicial", { exact: true })).toHaveValue("");
      await page.getByRole("row").filter({ hasText: "ui-new@example.test" }).getByRole("button", { name: "Editar", exact: true }).click();
      await page.getByRole("combobox", { name: "Estado", exact: true }).selectOption("inactive");
      await page.getByRole("button", { name: "Guardar cambios", exact: true }).click();
      await expect(page.getByRole("row").filter({ hasText: "ui-new@example.test" }).getByText("Inactivo", { exact: true })).toBeVisible();
      await page.getByRole("row").filter({ hasText: "ui-new@example.test" }).getByRole("button", { name: "Restablecer contraseña", exact: true }).click();
      await page.getByLabel("Contraseña inicial", { exact: true }).fill(initial);
      await page.getByLabel("Confirmar contraseña", { exact: true }).fill(initial);
      await page.getByRole("button", { name: "Restablecer contraseña", exact: true }).last().click();
      await expect(page.getByRole("heading", { name: "Editar cuenta", exact: true })).toBeVisible();
      await page.getByRole("link", { name: "Historial", exact: true }).click();
      await expect(page.getByRole("table", { name: "Historial administrativo · UTC" })).toBeVisible();
      await expect(page.getByRole("cell", { name: "identity.account.created", exact: true }).first()).toBeVisible();
      await page.getByRole("combobox", { name: "Resultado", exact: true }).selectOption("rejected");
      await page.getByRole("button", { name: "Consultar historial", exact: true }).click();
      await expect(page.getByRole("cell", { name: /email_conflict/ }).first()).toBeVisible();
      await page.goto("/cuenta/");
      await expect(page.getByRole("button", { name: "Cerrar sesión", exact: true })).toBeVisible();
    }
    if (role === "operator") {
      const denied = await context.request.get("/api/v1/identity/accounts");
      expect(denied.status()).toBe(403);
      await expect(page.getByRole("link", { name: "Usuarios", exact: true })).toHaveCount(0);
      await page.goto("/administracion/historial/");
      await expect(page.getByText("Acceso denegado.", { exact: true })).toBeVisible();
      await expect(page.getByRole("table")).toHaveCount(0);
      await page.goto("/cuenta/");
      await expect(page.getByRole("button", { name: "Cerrar sesión", exact: true })).toBeVisible();
    }
    const other = await context.newPage();
    await other.goto("/cuenta/");
    await expect(other.getByRole("button", { name: "Cerrar sesión", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Cerrar sesión", exact: true }).click();
    await expect(page).toHaveURL(/\/ingreso\/$/);
    await expect(other.getByText("Debe", { exact: false })).toBeVisible();
    expect((await context.request.get("/api/v1/auth/session")).status()).toBe(401);
    await other.close();
  }
  const clock = process.env.IDENTITY_E2E_CLOCK_FILE;
  if (clock) {
    await page.getByLabel("Correo", { exact: true }).fill("operator-active@example.test");
    await page.getByLabel("Contraseña", { exact: true }).fill(initial+" renewed");
    await page.getByRole("button", { name: "Ingresar", exact: true }).click();
    await expect(page).toHaveURL(/\/cuenta\/$/);
    writeFileSync(clock, "1800", { mode: 0o600 });
    await page.reload();
    await expect(page.getByRole("link", { name: "iniciar sesión", exact: true })).toBeVisible();
    expect((await context.request.get("/api/v1/auth/session")).status()).toBe(401);
  }
});
