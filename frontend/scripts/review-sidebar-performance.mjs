/** Local sidebar profiling with synthetic dashboard data, never a business backend. */
import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const output=resolve(process.argv[2] ?? 'test-results/sidebar-performance');
const captureOnly=process.env.SIDEBAR_CAPTURE_ONLY === '1';
const baseURL=process.env.UI_REVIEW_URL ?? 'http://127.0.0.1:3011';
if (!['127.0.0.1','localhost'].includes(new URL(baseURL).hostname)) throw new Error('Local preview only');
await mkdir(output,{recursive:true});
const start='2026-11-02T00:00:00-03:00';
const series=Array.from({length:80},(_,i)=>({start:new Date(Date.parse(start)+i*900000).toISOString(),end:new Date(Date.parse(start)+(i+1)*900000).toISOString(),energy_kwh:String(10+i%4),coverage_percent:'100'}));
const names=['Energía eléctrica total','HVAC y agua caliente sanitaria','Iluminación exterior','Iluminación interior','Circuitos de enchufes','Sistema sanitario','Ascensores'];
const dashboard={timezone:'America/Santiago',cutoff_at:'2026-11-02T20:00:00-03:00',period:{start,end:'2026-11-03T00:00:00-03:00',timezone:'America/Santiago'},series,chart_excluded_count:0,categories:names.map((name,i)=>({id:`CAT-0${i+1}`,name,source_mode:'measured',base_categories:[],state:'available',energy_kwh:String(i===0?920:[0,400,100,160,220,20,20][i]),coverage_percent:'100',covered_duration_us:'72000000000',elapsed_duration_us:'72000000000',last_reading_at:'2026-11-02T20:00:00-03:00',series,chart_excluded_count:0}))};
const browser=await chromium.launch({headless:true});
const results=[];
async function capture(page, filename) {
 await page.evaluate(async()=>{
  if(document.activeElement instanceof HTMLElement) document.activeElement.blur();
  scrollTo(0,0);
  await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
 });
 await page.waitForFunction(()=>scrollY===0);
 await page.screenshot({path:resolve(output,filename),fullPage:true});
}
try {
 for (const width of captureOnly?[390]:[1440,390]) for (const rate of captureOnly?[1]:[1,4]) {
  const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'no-preference'});
  await context.route('**/api/v1/**',async route=>{
   const path=new URL(route.request().url()).pathname;
   const value=path.endsWith('/auth/session')?{account:{id:'profile',email:'preview@example.test',role:'administrador_tecnico'},session_state:'normal',must_change_password:false,permissions:['consumption.read','costs.read','identity.accounts.read','administration.history.read','consumption.configuration.manage','costs.configuration.manage','reports.generate'],absolute_expires_at:'2099-01-01T00:00:00Z',idle_expires_at:'2099-01-01T00:00:00Z'}:path.endsWith('/consumption/dashboard')?dashboard:null;
   if (!value) throw new Error(`Unhandled fixture ${path}`);
   await route.fulfill({contentType:'application/json',body:JSON.stringify(value)});
  });
  const page=await context.newPage();
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto(baseURL,{waitUntil:'networkidle'});
  await page.locator('.dashboard-grid').waitFor();
  await page.evaluate(()=>document.fonts.ready);
  if(captureOnly) {
   await capture(page,`sidebar-${width}-${rate}x.png`);
   await context.close();
   continue;
  }
  const cdp=await context.newCDPSession(page);
  await cdp.send('Performance.enable');
  await cdp.send('Emulation.setCPUThrottlingRate',{rate});
  const finish=()=>page.locator('.app-frame aside').evaluate(async element=>{
   getComputedStyle(element).width;
   await Promise.all(element.getAnimations().map(animation=>animation.finished.catch(()=>{})));
  });
  async function toggle(open) {
   await page.evaluate(({width,open})=>{
    const target=document.querySelector(width>900?(open?'nav [aria-current="page"]':'.collapse-button'):'.mobile-header button');
    target.click();
   },{width,open});
   await finish();
  }
  // Settle one full cycle before measuring to exclude font/image and initial layout work.
  await toggle(width>900?false:true);await toggle(width>900?true:false);
  const samples=[];
  for(let i=0;i<6;i++) {
   const before=Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(m=>[m.name,m.value]));
   await page.evaluate(()=>{
    window.__sidebarProfile={frames:[],longTasks:[],running:true};
    const state=window.__sidebarProfile;
    state.observer=new PerformanceObserver(list=>state.longTasks.push(...list.getEntries().map(e=>({duration:e.duration,start:e.startTime}))));
    state.observer.observe({type:'longtask'});
    let previous;
    const frame=now=>{if(previous!==undefined)state.frames.push(now-previous);previous=now;if(state.running)requestAnimationFrame(frame);};
    requestAnimationFrame(frame);
   });
   await toggle(width>900?i%2===1:i%2===0);
   const frames=await page.evaluate(()=>{const state=window.__sidebarProfile;state.running=false;state.observer.disconnect();return {frames:state.frames,longTasks:state.longTasks};});
   const after=Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(m=>[m.name,m.value]));
   samples.push({...frames,layoutCount:after.LayoutCount-before.LayoutCount,layoutMs:(after.LayoutDuration-before.LayoutDuration)*1000,styleMs:(after.RecalcStyleDuration-before.RecalcStyleDuration)*1000,taskMs:(after.TaskDuration-before.TaskDuration)*1000});
   if(i===0) await capture(page,`sidebar-${width}-${rate}x-${width>900?'collapsed':'open'}.png`);
  }
  const layout=await page.locator('.app-frame').evaluate(element=>{
   const aside=element.querySelector('aside'), clip=getComputedStyle(aside).clipPath;
   return {padding:parseFloat(getComputedStyle(element).paddingLeft),sidebar:aside.getBoundingClientRect().width-(clip.startsWith('inset(')?parseFloat(clip.split(' ')[1] ?? '0'):0),overflow:document.documentElement.scrollWidth-innerWidth};
  });
  if (layout.overflow || width>900 && Math.abs(layout.padding-layout.sidebar)>1) throw new Error('Sidebar alignment/overflow regression');
  await page.emulateMedia({reducedMotion:'reduce'});
  const reduced=await page.locator('.app-frame aside').evaluate(element=>getComputedStyle(element).transitionDuration);
  if(reduced!=='0s') throw new Error('Reduced motion still animates the panel');
  if(width>900) {
   await page.emulateMedia({reducedMotion:'no-preference'});
   await page.evaluate(async()=>{
    document.querySelector('.collapse-button').click();
    await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
    document.querySelector('nav [aria-current="page"]').click();
   });
   await finish();
   if(await page.locator('.app-frame').evaluate(el=>el.classList.contains('shell--collapsed'))) throw new Error('Interrupted animation lost the latest toggle');
  }
  await capture(page,`sidebar-${width}-${rate}x.png`);
  results.push({width,cpuThrottle:rate,errors,layout,reduced,samples});
  console.log(JSON.stringify({width,rate,meanLayoutMs:samples.reduce((sum,s)=>sum+s.layoutMs,0)/6,maxFrameMs:Math.max(...samples.flatMap(s=>s.frames)),longTasks:samples.flatMap(s=>s.longTasks).length}));
  await context.close();
 }
} finally {
 await browser.close();
 if(!captureOnly) await writeFile(resolve(output,'results.json'),JSON.stringify({limitations:'Local headless Chromium with browser-only synthetic data. CPU throttling is not a real-device measurement.',results},null,2));
}
