/**007 real aggregate→events→trace→same-operation executions navigation under per-request Basic. */
import { test,expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

test('an actual operation links to its persisted trace and reference-filtered executions',async({browser})=>{
  /**Use references produced by the actual001 fixture; no fabricated trace or business result. */
  test.skip(!process.env.OBS_E2E_REFERENCE_FILE || !process.env.OBS_E2E_PASSWORD_FILE,'Requires real persisted references.');
  test.setTimeout(120000);
  const fixture=JSON.parse(readFileSync(process.env.OBS_E2E_REFERENCE_FILE!,'utf8'));
  const context=await browser.newContext({baseURL:process.env.OBS_E2E_URL,httpCredentials:{username:'prog-test-01',password:readFileSync(process.env.OBS_E2E_PASSWORD_FILE!,'utf8').trim()},ignoreHTTPSErrors:false});
  try{
    const page=await context.newPage();
    await page.goto(`/grafana/d/ecs-platform/platform?var-environment=test&var-operation=consumption.query_detail&from=${fixture.start_ms}&to=${fixture.end_ms}`);
    const panel=page.getByRole('region',{name:'Continuidad ECS-EC'});
    const link=panel.getByRole('link',{name:'Ver traza',exact:true}).first();
    await expect(link).toBeVisible({timeout:60000});
    const [tracePage]=await Promise.all([context.waitForEvent('page'),link.click()]);
    await expect(tracePage).toHaveURL(/\/jaeger\/trace\/[0-9a-f]{32}$/);
    await expect(tracePage.getByText('consumption.query_detail').first()).toBeVisible({timeout:30000});
    await tracePage.close();
    const executions=panel.getByRole('link',{name:/Otras ejecuciones/}).first();
    await expect(executions).toBeVisible({timeout:60000});
    await executions.click();
    await expect(page).toHaveURL(/var-operation_ref=[0-9a-f-]{36}/);
    await expect(panel.getByRole('link',{name:/Otras ejecuciones/})).toHaveCount(1,{timeout:60000});
  }finally{await context.close();}
});
