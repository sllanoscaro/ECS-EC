/**007 technical metrics: real closed window and explicit unavailable-query state; no business widgets. */
import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

test('closed real window states units, cut, denominator and independent coverage',async({browser})=>{
  /**A private fixture contains actual001 eight successes/two failures with real Alloy/Jaeger delivery. */
  test.skip(!process.env.OBS_E2E_REFERENCE_FILE || !process.env.OBS_E2E_PASSWORD_FILE,'Requires an explicit closed real-source window.');
  test.setTimeout(120000);
  const fixture=JSON.parse(readFileSync(process.env.OBS_E2E_REFERENCE_FILE!,'utf8'));
  const context=await browser.newContext({baseURL:process.env.OBS_E2E_URL,httpCredentials:{username:'prog-test-01',password:readFileSync(process.env.OBS_E2E_PASSWORD_FILE!,'utf8').trim()},ignoreHTTPSErrors:false});
  try{
    const page=await context.newPage();
    await page.goto(`/grafana/d/ecs-platform/platform?var-environment=test&var-operation=consumption.query_detail&from=${fixture.start_ms}&to=${fixture.end_ms}`);
    const panel=page.getByRole('region',{name:'Continuidad ECS-EC'});
    await expect(panel.getByText('Logs: complete · Trazas: complete',{exact:true})).toBeVisible({timeout:60000});
    await expect(panel.getByRole('row').filter({hasText:'Operaciones terminadas'}).getByRole('cell').nth(1)).toHaveText('10');
    await expect(panel.getByRole('row').filter({hasText:'Error inesperado'}).getByRole('cell').nth(1)).toHaveText('20');
    await expect(panel.getByText(/UTC \[/)).toBeVisible();
    await expect(panel.getByText(/Corte/)).toBeVisible();
    await expect(panel.getByText(/milisegundos|ms \/ /)).toBeVisible();
    await page.screenshot({path:process.env.OBS_E2E_SCREENSHOT ?? '/tmp/ecs-step4-closed-metrics.png',fullPage:true});
  }finally{await context.close();}
});

test('a failed technical query never manufactures activity or error zero',async({browser})=>{
  /**Abort only Loki transport in the browser; Jaeger evidence and query failures stay independently visible. */
  test.skip(!process.env.OBS_E2E_PASSWORD_FILE,'Requires provisioned isolated test gateway.');
  test.setTimeout(120000);
  const context=await browser.newContext({baseURL:process.env.OBS_E2E_URL,httpCredentials:{username:'prog-test-01',password:readFileSync(process.env.OBS_E2E_PASSWORD_FILE!,'utf8').trim()},ignoreHTTPSErrors:false});
  try{
    await context.route('**/logs/loki/api/v1/query_range?**',route=>route.abort());
    const page=await context.newPage();
    await page.goto('/grafana/d/ecs-platform/platform?var-environment=test');
    const panel=page.getByRole('region',{name:'Continuidad ECS-EC'});
    await expect(panel.getByText(/^Logs: unknown/)).toBeVisible({timeout:60000});
    await expect(panel.getByRole('row').filter({hasText:'Error inesperado'}).getByRole('cell').nth(1)).toHaveText('N/D');
    await expect(panel.getByText(/consulta_logs_fallida/)).toBeVisible();
  }finally{await context.close();}
});
