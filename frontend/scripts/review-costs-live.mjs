/** Verify production-rendered Costos with responses exported from the real local-demo database.
 * Session presentation is synthetic; financial payloads are unmodified backend exports.
 * This does not substitute an authenticated end-to-end HTTP test.
 */
import {chromium} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const input=process.argv[2];
if(!input)throw new Error('Supply the protected local-demo response export.');
const source=JSON.parse(await readFile(input,'utf8'));
const output=resolve(process.argv[3]??'test-results/costs-live');
const base=process.env.UI_REVIEW_URL??'http://127.0.0.1:8000';
if(!['localhost','127.0.0.1'].includes(new URL(base).hostname))throw new Error('Local only');
if(source.distribution.state!=='available'||source.cycle.comparison_status!=='available')throw new Error('Demo is not ready');
await mkdir(output,{recursive:true});
const browser=await chromium.launch({headless:true});
const results=[];
try{
 for(const width of [1440,390]){
  const errors=[],unknown=[],mutations=[];
  const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'});
  await context.route('**/api/v1/**',async route=>{
   const path=new URL(route.request().url()).pathname.replace('/api/v1','');
   const reply=value=>route.fulfill({contentType:'application/json',body:JSON.stringify(value)});
   if(route.request().method()!=='GET'){mutations.push(path);return route.fulfill({status:405});}
   if(path==='/auth/session')return reply({account:{email:'revision-demo@example.test',role:'operador'},session_state:'normal',must_change_password:false,permissions:['costs.read','consumption.read'],absolute_expires_at:'2099-01-01T00:00:00Z',idle_expires_at:'2099-01-01T00:00:00Z'});
   if(path==='/costs/cycles'||path==='/costs/history')return reply({items:[source.cycle],next_cursor:null,cutoff_at:source.distribution.cutoff_at});
   if(path.endsWith('/distribution'))return reply(source.distribution);
   if(path.startsWith('/costs/calculations/'))return reply(source.cycle.calculation);
   if(path==='/costs/bills')return reply({items:[source.bill],next_cursor:null,cutoff_at:source.distribution.cutoff_at});
   if(path.startsWith('/costs/comparisons/'))return reply(source.cycle.comparison);
   unknown.push(path);return route.fulfill({status:501});
  });
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/costos/',{waitUntil:'networkidle'});
  await page.locator('.cost-category-table tfoot').waitFor();
  await page.locator('.cost-comparison-values').waitFor();
  await page.locator('.cost-demo-notice').waitFor();
  const rows=await page.locator('.cost-category-table tbody tr').count();
  const slices=await page.locator('.cost-donut circle[stroke-dasharray]').count();
  if(rows<6||slices<6)throw new Error('Category breakdown missing');
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
  if(overflow||errors.length||unknown.length||mutations.length)throw new Error(JSON.stringify({overflow,errors,unknown,mutations}));
  await page.evaluate(async()=>{await document.fonts.ready;document.activeElement?.blur();scrollTo(0,0);await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));});
  await page.screenshot({path:resolve(output,`costs-${width}.png`),fullPage:true});
  results.push({width,rows,slices,overflow,errors,unknown,mutations,calculation_id:source.cycle.calculation.id});
  await context.close();
 }
}finally{await browser.close();await writeFile(resolve(output,'results.json'),JSON.stringify({data:'Real local-demo backend export; synthetic session presentation. API authorization tested separately on isolated PostgreSQL.',results},null,2));}
console.log(JSON.stringify(results));
