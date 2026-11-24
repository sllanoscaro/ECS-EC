/** Real005 browser generation, download, uncertain retry and006 session return on a separate synthetic database. */
import {readFileSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {expect,test} from '@playwright/test';
test.skip(!process.env.REPORTS_E2E,'Requires seed_report_reference.py and the real monolith on an isolated *_test database.');
const password=()=>readFileSync(process.env.IDENTITY_E2E_PASSWORD_FILE!,'utf8').replace(/\n$/,'');
test.beforeAll(async({request})=>{
 /** Renew a seeded ordinary operator through006's public CSRF/session/password flows. */
 if(process.env.REPORTS_E2E_RENEWED)return;
 const origin=process.env.E2E_BASE_URL!;const csrf=await(await request.get('/api/v1/auth/csrf')).json();
 const login=await request.post('/api/v1/auth/login',{headers:{Origin:origin,'X-CSRF-Token':csrf.csrf_token},data:{email:'operator-active@example.test',password:password()}});
 expect(login.status()).toBe(200);const session=await login.json();
 const changed=await request.post('/api/v1/auth/password',{headers:{Origin:origin,'X-CSRF-Token':session.csrf_token},data:{current_password:password(),new_password:password()+' renewed'}});
 expect(changed.status()).toBe(204);
});

test('three scales produce stored PDFs and survive transport and session failures',async({page,context})=>{
 test.setTimeout(60000);
 /** Exercise real producer data; routing below interrupts only one transport attempt and supplies no fake response. */
 await page.goto('/ingreso/?retorno=%2Freportes%2F');
 await page.getByLabel('Correo electrónico',{exact:true}).fill('operator-active@example.test');
 await page.getByLabel('Contraseña',{exact:true}).fill(password()+' renewed');
 await page.getByRole('button',{name:'Ingresar',exact:true}).click();
 await expect(page).toHaveURL(/\/reportes\/$/);
 await expect(page.getByText('Zona horaria del edificio: America/Santiago')).toBeVisible();
 for(const scale of ['diario','mensual','anual']){
  await page.getByLabel('Tipo de reporte').selectOption(scale);
  if(scale==='diario')await page.getByLabel('Fecha',{exact:true}).fill('2025-12-31');
  else {await page.getByLabel('Año',{exact:true}).fill('2026');if(scale==='mensual')await page.getByRole('combobox',{name:'Mes',exact:true}).selectOption('3');}
  await page.getByRole('button',{name:'Generar PDF',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Documento disponible'})).toBeVisible({timeout:15000});
  const selected=(await page.getByRole('link',{name:'Descargar PDF'}).getAttribute('href'))!;
  const downloaded=page.waitForEvent('download');await page.getByRole('link',{name:'Descargar PDF'}).click();const file=await downloaded;
  expect(file.suggestedFilename()).toContain(scale);
  const directory=process.env.REPORTS_ARTIFACT_DIRECTORY;if(directory)await file.saveAs(join(directory,scale+'.pdf'));
  const first=await page.request.get(selected);const second=await page.request.get(selected);
  expect(first.status()).toBe(200);expect(first.headers()['cache-control']).toBe('no-store');expect(await first.body()).toEqual(await second.body());
 }
 const failureControl=process.env.REPORTS_E2E_FAILURE_FILE;
 if(failureControl){
  writeFileSync(failureControl,'composition');
  try{await page.getByRole('button',{name:'Generar PDF',exact:true}).click();await expect(page.getByRole('heading',{name:'No se pudo generar el documento'})).toBeVisible({timeout:15000});await expect(page.getByRole('main').getByRole('alert')).toContainText('legibilidad');await expect(page.getByRole('link',{name:'Descargar PDF'})).toHaveCount(0);await expect(page.getByLabel('Año',{exact:true})).toHaveValue('2026');}
  finally{writeFileSync(failureControl,'');}
 }
 await page.getByLabel('Año',{exact:true}).fill('9998');await page.getByRole('button',{name:'Generar PDF',exact:true}).click();
 await expect(page.getByRole('main').getByRole('alert')).toContainText('todavía no comienza');await expect(page.getByLabel('Año',{exact:true})).toHaveValue('9998');
 await page.getByLabel('Año',{exact:true}).fill('2026');
 let lostKey='';await page.route('**/api/v1/reports',async route=>{lostKey=route.request().headers()['idempotency-key'];await route.abort('failed');},{times:1});
 await page.getByRole('button',{name:'Generar PDF',exact:true}).click();await expect(page.getByRole('main').getByRole('alert')).toContainText('No se pudo confirmar');
 const retried=page.waitForRequest(request=>request.url().endsWith('/api/v1/reports')&&request.method()==='POST');
 await page.getByRole('button',{name:'Generar PDF',exact:true}).click();expect((await retried).headers()['idempotency-key']).toBe(lostKey);
 await expect(page.getByRole('heading',{name:'Documento disponible'})).toBeVisible({timeout:15000});
 const savedUrl=page.url();
 const directory=process.env.REPORTS_ARTIFACT_DIRECTORY;
 if(directory){await page.setViewportSize({width:1440,height:1000});await page.screenshot({path:join(directory,'desktop.png'),fullPage:true,animations:'disabled'});await page.setViewportSize({width:390,height:844});await page.screenshot({path:join(directory,'mobile.png'),fullPage:true,animations:'disabled'});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);}
 await context.clearCookies();await page.reload();await page.getByRole('link',{name:'iniciar sesión',exact:true}).click();
 await expect(page).toHaveURL(/retorno=/);await page.getByLabel('Correo electrónico',{exact:true}).fill('operator-active@example.test');await page.getByLabel('Contraseña',{exact:true}).fill(password()+' renewed');await page.getByRole('button',{name:'Ingresar',exact:true}).click();
 await expect(page).toHaveURL(savedUrl);await expect(page.getByRole('heading',{name:'Documento disponible'})).toBeVisible();
 await expect(page.getByLabel('Tipo de reporte')).toHaveValue('anual');await expect(page.getByLabel('Año',{exact:true})).toHaveValue('2026');
});
