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
    await page.getByLabel("Correo electrónico", { exact: true }).fill(`${role}-active@example.test`);
    await page.getByLabel("Contraseña", { exact: true }).fill(initial);
    await page.getByRole("button", { name: "Ingresar", exact: true }).click();
    await expect(page).toHaveURL(/^https?:\/\/[^/]+\/(?:cuenta\/)?$/);
    await page.goto("/cuenta/");
    await expect(page.getByText("Debe renovar su contraseña inicial antes de continuar.")).toBeVisible();
    const cookies = await context.cookies();
    const cookie = cookies.find((value) => value.name === "ecs_ec_session");
    expect(cookie?.httpOnly).toBeTruthy();
    expect(cookie?.sameSite).toBe("Lax");
    expect(cookie?.secure).toBe(baseURL?.startsWith("https://"));
    await page.getByLabel("Contraseña actual", { exact: true }).fill(initial);
    await page.getByLabel(/^Nueva contraseña/).fill(initial+" renewed");
    await page.getByLabel("Confirmar nueva contraseña", { exact: true }).fill(initial+" renewed");
    await page.getByRole("button", { name: "Cambiar contraseña", exact: true }).click();
    await expect(page).toHaveURL(/\/ingreso\/$/);
    await page.getByLabel("Correo electrónico", { exact: true }).fill(`${role}-active@example.test`);
    await page.getByLabel("Contraseña", { exact: true }).fill(initial+" renewed");
    await page.getByRole("button", { name: "Ingresar", exact: true }).click();
    await expect(page).toHaveURL(/^https?:\/\/[^/]+\/(?:cuenta\/)?$/);
    await page.goto("/cuenta/");
    await expect(page.getByRole("button", { name: "Salir", exact: true })).toBeVisible();
    if (role === "admin") {
      await page.locator('a[href="/administracion/usuarios/"]').click();
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
      await page.locator('a[href="/administracion/historial/"]').click();
      await expect(page.getByRole("table", { name: "Historial administrativo · UTC" })).toBeVisible();
      await expect(page.getByRole("cell", { name: "identity.account.created", exact: true }).first()).toBeVisible();
      await page.getByRole("combobox", { name: "Resultado", exact: true }).selectOption("rejected");
      await page.getByRole("button", { name: "Consultar historial", exact: true }).click();
      await expect(page.getByRole("cell", { name: /email_conflict/ }).first()).toBeVisible();
      await page.goto("/cuenta/");
      await expect(page.getByRole("button", { name: "Salir", exact: true })).toBeVisible();
    }
    if (role === "operator") {
      const denied = await context.request.get("/api/v1/identity/accounts");
      expect(denied.status()).toBe(403);
      await expect(page.locator('a[href="/administracion/usuarios/"]')).toHaveCount(0);
      await page.goto("/administracion/historial/");
      await expect(page.getByText("Acceso denegado.", { exact: true })).toBeVisible();
      await expect(page.getByRole("table")).toHaveCount(0);
      await page.goto("/cuenta/");
      await expect(page.getByRole("button", { name: "Salir", exact: true })).toBeVisible();
    }
    const other = await context.newPage();
    await other.goto("/cuenta/");
    await expect(other.getByRole("button", { name: "Salir", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Salir", exact: true }).click();
    await expect(page).toHaveURL(/\/ingreso\/$/);
    await expect(other.getByText("Debe", { exact: false })).toBeVisible();
    expect((await context.request.get("/api/v1/auth/session")).status()).toBe(401);
    await other.close();
  }
  const clock = process.env.IDENTITY_E2E_CLOCK_FILE;
  if (clock) {
    await page.getByLabel("Correo electrónico", { exact: true }).fill("operator-active@example.test");
    await page.getByLabel("Contraseña", { exact: true }).fill(initial+" renewed");
    await page.getByRole("button", { name: "Ingresar", exact: true }).click();
    await expect(page).toHaveURL(/^https?:\/\/[^/]+\/(?:cuenta\/)?$/);
    await page.goto("/cuenta/");
    writeFileSync(clock, "1800", { mode: 0o600 });
    await page.reload();
    await expect(page.getByRole("link", { name: "iniciar sesión", exact: true })).toBeVisible();
    expect((await context.request.get("/api/v1/auth/session")).status()).toBe(401);
  }
});

test('real providers enforce both profiles, activity deadlines and private cleanup', async ({page, context}) => {
  /** Run only with a deliberately provisioned private clock and actual001/002/004/005 fixtures. */
  test.skip(!process.env.IDENTITY_E2E_STEP3, 'Requires the separate step3 provider fixture and private clock.');
  test.setTimeout(120000);
  const clock=process.env.IDENTITY_E2E_CLOCK_FILE!;
  const password=readFileSync(process.env.IDENTITY_E2E_PASSWORD_FILE!, 'utf8').trimEnd()+' renewed';
  const requests: {path:string;activity:string|undefined;method:string}[]=[];
  page.on('request',request=>{if(request.url().includes('/api/v1/')) requests.push({path:new URL(request.url()).pathname,activity:request.headers()['x-session-activity'],method:request.method()});});
  async function login(role='operator') {
    /** Re-enter through normal006 credentials; time and users have no public fixture endpoints. */
    await page.goto('/ingreso/');
    await page.getByLabel('Correo electrónico',{exact:true}).fill(`${role}-active@example.test`);
    await page.getByLabel('Contraseña',{exact:true}).fill(password);
    await page.getByRole('button',{name:'Ingresar',exact:true}).click();
    await expect(page).toHaveURL(/^https?:\/\/[^/]+\/(?:cuenta\/)?$/);
    await page.goto("/cuenta/");
  }
  for(const role of ['admin','operator']) {
    await login(role);
    if(role==='admin') {
      await page.goto('/administracion/costos/');
      await page.getByLabel('Inicio del ciclo con offset',{exact:true}).fill('2026-01-01T00:00:00Z');
      await page.getByLabel('Fin del ciclo con offset',{exact:true}).fill('2026-01-01T01:00:00Z');
      await page.getByLabel('Mes de demanda documentado (opcional)',{exact:true}).fill('2026-01');
      await page.getByLabel('Referencia documental del mes',{exact:true}).fill('synthetic:identity:month');
      await page.getByRole('button',{name:'Confirmar cálculo',exact:true}).click();
      await expect(page.getByText('Costo completo: 100000 CLP',{exact:true})).toBeVisible();
      await page.getByLabel('Motivo del recálculo',{exact:true}).fill('Synthetic identity recalc');
      const recalculated=page.waitForResponse(r=>r.url().endsWith('/costs/calculations')&&r.request().method()==='POST');
      await page.getByRole('button',{name:'Confirmar cálculo',exact:true}).click();
      expect((await (await recalculated).json()).revision).toBe(2);
    }
    await page.goto('/consumption/');
    await expect(page.getByRole('combobox',{name:'Categoría',exact:true})).toBeVisible();
    await page.getByRole('combobox',{name:'Categoría',exact:true}).selectOption('CAT-01');
    await page.getByLabel('Desde',{exact:true}).fill('2025-12-31T21:00');
    await page.getByLabel('Hasta',{exact:true}).fill('2025-12-31T22:00');
    await page.getByRole('button',{name:'Consultar',exact:true}).click();
    await expect(page.getByRole('cell',{name:/1[.,]?000(?:,0)? kWh/,exact:true})).toBeVisible();
    await page.goto('/costos/');
    await expect(page.getByRole('heading',{name:'Desglose del ciclo',exact:true})).toBeVisible();
    await page.goto('/reportes/');
    await page.getByLabel('Tipo de reporte').selectOption('anual');
    await page.getByLabel('Año',{exact:true}).fill('2025');
    await page.getByRole('button',{name:'Generar PDF',exact:true}).click();
    await expect(page.getByRole('heading',{name:'Documento disponible'})).toBeVisible({timeout:15000});
    const download=page.waitForEvent('download');
    await page.getByRole('link',{name:'Descargar PDF',exact:true}).click();
    expect((await download).suggestedFilename()).toContain('anual');
    if(role==='admin') {
      await page.goto('/administracion/consumo/');
      await expect(page.getByRole('heading',{name:'Configuración de consumo',exact:true})).toBeVisible();
      const before=await (await page.request.get('/api/v1/consumption/configuration')).json();
      await page.getByRole('combobox',{name:'Origen de la energía total',exact:true}).selectOption('calculated');
      await page.getByRole('button',{name:'Guardar configuración',exact:true}).click();
      await expect(page.getByText(`Configuración guardada. Revisión ${before.revision+1}.`,{exact:true})).toBeVisible();
      await page.getByRole('combobox',{name:'Origen de la energía total',exact:true}).selectOption('measured');
      await page.getByRole('combobox',{name:'Medidor del total',exact:true}).selectOption('00000000-0000-0000-0000-000000000001');
      await page.getByRole('button',{name:'Guardar configuración',exact:true}).click();
      await expect(page.getByText(`Configuración guardada. Revisión ${before.revision+2}.`,{exact:true})).toBeVisible();
    } else {
      for(const path of ['/administracion/consumo/','/administracion/costos/','/administracion/historial/']) {
        await page.goto(path);
        await expect(page.getByText('Acceso denegado.',{exact:true})).toBeVisible();
      }
      for(const [method,path] of [['GET','/consumption/configuration'],['GET','/costs/supply'],['GET','/costs/profiles'],['POST','/costs/profiles'],['POST','/costs/bills'],['POST','/costs/calculations'],['PUT','/costs/supply']]) {
        expect((await page.request.fetch('/api/v1'+path,{method,data:method==='GET'?undefined:{}})).status()).toBe(403);
      }
    }
    await page.goto('/cuenta/');await page.getByRole('button',{name:'Salir',exact:true}).click();
  }
  await login();
  await page.goto('/consumption/');
  await expect(page.getByRole('button',{name:'Actualizar',exact:true})).toBeEnabled();
  const start=await (await page.request.get('/api/v1/auth/session')).json();
  let offset=Number(readFileSync(clock,'utf8'));
  writeFileSync(clock,String(offset+29*60));
  const consulted=page.waitForResponse(r=>r.url().includes('/consumption/categories/')&&r.status()===200);
  await page.getByRole('button',{name:'Actualizar',exact:true}).click();await consulted;
  const extended=await (await page.request.get('/api/v1/auth/session',{headers:{'X-Session-Activity':'interactive'}})).json();
  expect(Date.parse(extended.idle_expires_at)-Date.parse(start.idle_expires_at)).toBeGreaterThanOrEqual(29*60*1000);
  expect(Date.parse(extended.idle_expires_at)-Date.parse(start.idle_expires_at)).toBeLessThan(29*60*1000+10000);
  expect(extended.absolute_expires_at).toBe(start.absolute_expires_at);
  writeFileSync(clock,String(offset+59*60+10));
  await page.evaluate(()=>window.dispatchEvent(new PageTransitionEvent('pageshow')));
  await expect(page.getByRole('link',{name:'iniciar sesión',exact:true})).toBeVisible();
  await expect(page.getByLabel('Desde',{exact:true})).toHaveCount(0);
  expect((await page.request.get('/api/v1/consumption/catalog',{headers:{'X-Session-Activity':'interactive'}})).status()).toBe(401);
  await login();offset=Number(readFileSync(clock,'utf8'));
  const baseline=await (await page.request.get('/api/v1/auth/session')).json();
  writeFileSync(clock,String(offset+29*60));
  expect((await page.request.get('/api/v1/consumption/catalog',{headers:{'X-Session-Activity':'background'}})).status()).toBe(200);
  const introspection=await (await page.request.get('/api/v1/auth/session',{headers:{'X-Session-Activity':'interactive'}})).json();
  expect(introspection.idle_expires_at).toBe(baseline.idle_expires_at);
  writeFileSync(clock,String(offset+30*60+1));
  expect((await page.request.get('/api/v1/consumption/catalog',{headers:{'X-Session-Activity':'interactive'}})).status()).toBe(401);
  await context.clearCookies();await login();offset=Number(readFileSync(clock,'utf8'));
  for(let i=1;i<=16;i++) {
    writeFileSync(clock,String(offset+i*29*60));
    expect((await page.request.get('/api/v1/consumption/catalog',{headers:{'X-Session-Activity':'interactive'}})).status()).toBe(200);
  }
  writeFileSync(clock,String(offset+8*60*60+1));
  expect((await page.request.get('/api/v1/consumption/catalog',{headers:{'X-Session-Activity':'interactive'}})).status()).toBe(401);
  expect(requests.some(r=>r.path.includes('/consumption/categories/')&&r.activity==='interactive')).toBe(true);
  expect(requests.some(r=>r.path.startsWith('/api/v1/costs/')&&r.activity==='interactive')).toBe(true);
  expect(requests.some(r=>/^\/api\/v1\/reports\/[a-f0-9-]+$/.test(r.path)&&r.method==='GET'&&r.activity==='background')).toBe(true);
  expect(requests.filter(r=>r.path==='/api/v1/auth/session').every(r=>r.activity==='background')).toBe(true);
});

test('administrative invalid inputs preserve revisions and history retains trusted actors',async({page})=>{
  /** Use existing001/004 forms and009 history after the real financial provider scenarios. */
  test.skip(!process.env.IDENTITY_E2E_STEP3,'Requires the separate step3 provider fixture.');
  const password=readFileSync(process.env.IDENTITY_E2E_PASSWORD_FILE!,'utf8').trimEnd()+' renewed';
  await page.goto('/ingreso/');
  await page.getByLabel('Correo electrónico',{exact:true}).fill('admin-active@example.test');
  await page.getByLabel('Contraseña',{exact:true}).fill(password);
  await page.getByRole('button',{name:'Ingresar',exact:true}).click();
  await expect(page).toHaveURL(/^https?:\/\/[^/]+\/(?:cuenta\/)?$/);
  const admin=(await(await page.request.get('/api/v1/auth/session')).json()).account.id;
  await page.goto('/administracion/consumo/');
  const before=await(await page.request.get('/api/v1/consumption/configuration')).json();
  await page.getByLabel('Zona IANA del edificio',{exact:true}).fill('Invalid/Zone');
  const rejected=page.waitForResponse(r=>r.url().endsWith('/consumption/configuration')&&r.request().method()==='PUT');
  await page.getByRole('button',{name:'Guardar configuración',exact:true}).click();
  expect((await rejected).status()).toBe(422);
  expect(await(await page.request.get('/api/v1/consumption/configuration')).json()).toEqual(before);
  await expect(page.getByLabel('Zona IANA del edificio',{exact:true})).toHaveValue('Invalid/Zone');
  await page.goto('/administracion/costos/');
  // Confirm an actual new profile revision and bill through004's forms before checking invalid drafts.
  const published=page.waitForResponse(r=>r.url().endsWith('/costs/profiles')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Confirmar nueva revisión de perfil',exact:true}).click();
  expect((await published).status()).toBe(201);
  await page.getByRole('button',{name:'Nueva boleta',exact:true}).click();
  await page.getByLabel('Identificador de boleta',{exact:true}).fill(`identity-${Date.now()}`);
  await page.getByLabel('Emisión con offset',{exact:true}).fill('2026-01-02T00:00:00Z');
  await page.getByLabel('Referencia del documento',{exact:true}).fill('synthetic:identity:bill');
  await page.getByLabel('Total a pagar de boleta (CLP)',{exact:true}).fill('100000');
  await page.getByRole('button',{name:'Añadir concepto',exact:true}).click();
  await page.getByLabel('Código de concepto 1',{exact:true}).fill('energy');
  await page.getByLabel('Descripción 1',{exact:true}).fill('Energía sintética');
  await page.getByLabel('Importe CLP 1',{exact:true}).fill('100000');
  const billed=page.waitForResponse(r=>r.url().endsWith('/costs/bills')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Confirmar boleta',exact:true}).click();
  expect((await billed).status()).toBe(201);
  const profiles=await(await page.request.get('/api/v1/costs/profiles')).json();
  await page.getByLabel('Precio cargo 1.1',{exact:true}).fill('-1');
  await page.getByRole('button',{name:'Confirmar nueva revisión de perfil',exact:true}).click();
  expect((await(await page.request.get('/api/v1/costs/profiles')).json()).latest_version_id).toBe(profiles.latest_version_id);
  await page.goto('/administracion/historial/');
  await expect(page.getByRole('table',{name:'Historial administrativo · UTC',exact:true})).toBeVisible();
  for(const action of ['consumption.configuration.changed','costs.profile.created','costs.bill.created','costs.calculation.created']) {
    const response=await page.request.get('/api/v1/identity/administration-history',{params:{action,result:'allowed',limit:100}});
    expect(response.status()).toBe(200);
    const entries=(await response.json()).items;
    expect(entries.some((entry:{actor:{kind:string;account_id:string}})=>entry.actor.kind==='account'&&entry.actor.account_id===admin)).toBe(true);
  }
  await page.getByRole('button',{name:'Salir',exact:true}).click();
  await expect(page).toHaveURL(/\/ingreso\/$/);
  await page.getByLabel('Correo electrónico',{exact:true}).fill('operator-active@example.test');
  await page.getByLabel('Contraseña',{exact:true}).fill(password);
  await page.getByRole('button',{name:'Ingresar',exact:true}).click();
  await expect(page).toHaveURL(/^https?:\/\/[^/]+\/(?:cuenta\/)?$/);
  await page.goto('/administracion/historial/');
  await expect(page.getByText('Acceso denegado.',{exact:true})).toBeVisible();
  await expect(page.getByRole('table')).toHaveCount(0);
});
