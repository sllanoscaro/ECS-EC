/**008 actual monolith/006/PostgreSQL configuration flow; private synthetic accounts and no mail injection endpoint. */
import {test,expect,type Page} from '@playwright/test';
import {readFileSync} from 'node:fs';

/**Enter through the ordinary protected login UI; cookie/CSRF stay with the browser. */
async function login(page:Page,role:'admin'|'operator'){
 await page.goto('/ingreso/');await page.getByLabel('Correo electrónico',{exact:true}).fill(`notification-${role}@example.test`);await page.getByLabel('Contraseña',{exact:true}).fill(readFileSync(process.env.NOTIFICATION_E2E_PASSWORD_FILE!,'utf8').trim());await page.getByRole('button',{name:'Ingresar',exact:true}).click();await expect(page).toHaveURL(/^http:\/\/127\.0\.0\.1:[0-9]+\/(?:cuenta\/)?$/);
}

test('an administrator configures06:00, previews actual dates, explicitly activates, revises and pauses',async({page})=>{
 /**The preview and persisted rule come from the actual installed API; screenshots contain synthetic accounts only. */
 test.skip(!process.env.NOTIFICATION_E2E_PASSWORD_FILE,'Requires explicit private008 fixtures');test.setTimeout(120000);
 await login(page,'admin');await page.goto('/notificaciones/reglas/');await expect(page.getByRole('heading',{name:'Reglas de notificación'})).toBeVisible();
 await page.getByLabel('Nombre de la regla').fill('Resumen diario 06:00');await page.getByRole('checkbox',{name:/notification-admin@example.test/}).check();await expect(page.getByLabel('Hora local')).toHaveValue('06:00');
 await page.getByRole('button',{name:'Guardar regla',exact:true}).click();await expect(page.getByText('desactivada',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Previsualizar fechas'}).click();await expect(page.getByRole('region',{name:'Vista previa'})).toBeVisible();await expect(page.getByRole('region',{name:'Vista previa'}).getByRole('listitem')).toHaveCount(3);
 await page.getByRole('button',{name:'Activar regla',exact:true}).click();await expect(page.getByText('activa',{exact:true})).toBeVisible();
 await page.getByLabel('Nombre de la regla').fill('Resumen revisado');await page.getByRole('button',{name:'Guardar revisión',exact:true}).click();await expect(page.getByText('pausada',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Ver versiones',exact:true}).click();await expect(page.getByRole('list',{name:'Versiones conservadas'}).getByRole('listitem')).toHaveCount(2);
 await page.getByRole('button',{name:'Previsualizar fechas'}).click();await page.getByRole('button',{name:'Activar regla',exact:true}).click();await expect(page.getByText('activa',{exact:true})).toBeVisible();await page.getByRole('button',{name:'Pausar regla',exact:true}).click();await expect(page.getByText('pausada',{exact:true})).toBeVisible();
 for(const width of [1440,768,390]){await page.setViewportSize({width,height:900});await page.evaluate(()=>window.scrollTo(0,0));await page.waitForTimeout(200);await page.screenshot({path:`${process.env.NOTIFICATION_E2E_ARTIFACTS}/rules-${width}.png`,fullPage:true});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();}
});

test('operator and anonymous direct paths expose no rule configuration or account directory',async({browser,baseURL})=>{
 /**Navigation filtering is only presentation; the real API denies every direct management access. */
 test.skip(!process.env.NOTIFICATION_E2E_PASSWORD_FILE,'Requires explicit private008 fixtures');test.setTimeout(120000);
 const context=await browser.newContext({baseURL,ignoreHTTPSErrors:false});const page=await context.newPage();
 try{expect((await context.request.get('/api/v1/notifications/rules')).status()).toBe(401);await login(page,'operator');await expect(page.locator('a[href="/notificaciones/reglas/"]')).toHaveCount(0);expect((await context.request.get('/api/v1/notifications/recipients')).status()).toBe(403);await page.goto('/notificaciones/reglas/');await expect(page.getByText('Acceso denegado.',{exact:true})).toBeVisible();await expect(page.getByLabel('Nombre de la regla')).toHaveCount(0);}finally{await context.close();}
});
