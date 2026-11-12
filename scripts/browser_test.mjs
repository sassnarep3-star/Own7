/* Linux/x64 browser + WCAG checks using only pinned npm-delivered binaries. */
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createServer} from 'node:http';
import {existsSync, mkdirSync, readFileSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {dirname, extname, join, resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {brotliDecompressSync} from 'node:zlib';
import chromium from '@sparticuz/chromium';
import {chromium as playwright} from 'playwright-core';

const root=resolve(dirname(fileURLToPath(import.meta.url)), '..');
const manifest=JSON.parse(readFileSync(join(root,'research/site-manifest.json'),'utf8'));
const catalog=JSON.parse(readFileSync(join(root,'research/catalog.json'),'utf8'));
const visitPages=[...manifest.canonical_pages,...(manifest.auxiliary_pages||[])];
const out=join(root,'.artifacts');
mkdirSync(out,{recursive:true});
const report={status:'running',browser:null,desktop_pages:[],mobile_pages:[],accessibility_violations:[],runtime_errors:[],assertions:[]};
const mime={'.html':'text/html','.css':'text/css','.js':'application/javascript','.svg':'image/svg+xml','.json':'application/json','.csv':'text/csv','.md':'text/plain'};
const allowedFolders=new Set(['assets','css','js','data','research','docs','pages','verified','handoff','market-evidence','rental','nfl']);
const publicRootFiles=new Set([...manifest.canonical_pages,...Object.keys(manifest.legacy_redirects),'README.md','COORDINATION.md']);
const server=createServer((req,res)=>{
  try{
    const url=new URL(req.url,'http://localhost');
    if(!url.pathname.startsWith('/Own7/')){res.writeHead(404).end();return;}
    let local=decodeURIComponent(url.pathname.slice('/Own7/'.length));
    if(!local)local='index.html';
    const path=resolve(root,local);
    const folder=local.split('/')[0];
    if(!path.startsWith(root+sep)||(!allowedFolders.has(folder)&&!publicRootFiles.has(local))||!mime[extname(path)]||!existsSync(path)){
      res.writeHead(404).end();return;
    }
    res.writeHead(200,{'Content-Type':mime[extname(path)]+'; charset=utf-8','Cache-Control':'no-store'});res.end(readFileSync(path));
  }catch{res.writeHead(404).end();}
});
await new Promise(resolve=>server.listen(0,'0.0.0.0',resolve));
const origin=`http://127.0.0.1:${server.address().port}`;
const base=origin+'/Own7/';
let browser;
try{
  // Bundle includes NSS/NSPR libraries; extract offline for minimal Linux hosts.
  const libs=join(tmpdir(),'own7-chromium-libs');mkdirSync(libs,{recursive:true});
  const archive=resolve(dirname(fileURLToPath(import.meta.resolve('@sparticuz/chromium'))),'../bin/al2023.tar.br');
  execFileSync('tar',['-xf','-','-C',libs],{input:brotliDecompressSync(readFileSync(archive))});
  const libraryPath=[join(libs,'lib'),process.env.LD_LIBRARY_PATH].filter(Boolean).join(':');
  browser=await playwright.launch({executablePath:await chromium.executablePath(),headless:true,
    // Do not disable web security or permit mixed content to make tests pass.
    args:chromium.args.filter(a=>a!=='--disable-web-security'&&a!=='--allow-running-insecure-content'),
    env:{...process.env,LD_LIBRARY_PATH:libraryPath}});
  report.browser=await browser.version();
  const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1,acceptDownloads:true,reducedMotion:'reduce'});
  const page=await context.newPage();
  page.on('pageerror',error=>report.runtime_errors.push(error.message));
  page.on('console',message=>{if(message.type()==='error')report.runtime_errors.push(message.text());});
  page.on('response',response=>{if(response.status()>=400)report.runtime_errors.push(`${response.status()} ${response.url()}`);});
  page.on('requestfailed',request=>report.runtime_errors.push(`${request.failure()?.errorText} ${request.url()}`));
  const axePath=join(root,'node_modules/axe-core/axe.min.js');
  async function visit(slug,mode){
    const response=await page.goto(base+slug,{waitUntil:'networkidle'});
    assert.equal(response.status(),200,slug+' status');
    assert.equal(await page.locator('main h1').count(),1,slug+' single main heading');
    if(manifest.canonical_pages.includes(slug))assert.equal(await page.locator('nav a[aria-current="page"]').count(),1,slug+' active navigation');
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),slug+' outer horizontal overflow');
    assert(await page.locator('td[data-empty]').evaluateAll(cells=>cells.every(c=>!c.textContent.trim())),slug+' unknown fields blank');
    await page.addScriptTag({path:axePath});
    const result=await page.evaluate(async()=>await window.axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}}));
    for(const violation of result.violations)report.accessibility_violations.push({page:slug,mode,id:violation.id,impact:violation.impact,nodes:violation.nodes.map(n=>({target:n.target,summary:n.failureSummary}))});
    report[mode+'_pages'].push(slug);
  }
  for(const slug of visitPages)await visit(slug,'desktop');
  await page.goto(base+'index.html',{waitUntil:'networkidle'});
  await page.screenshot({path:join(out,'dashboard-desktop.png'),fullPage:true});

  await page.goto(base+'data.html',{waitUntil:'networkidle'});
  const teams=page.locator('#team-data-table');
  assert.equal(await teams.locator('tbody tr:visible').count(),30);
  await page.locator('[data-search-for="team-data-table"]').fill('Denver');
  assert.equal(await teams.locator('tbody tr:visible').count(),1);
  assert((await teams.locator('tbody tr:visible').innerText()).includes('122.1'));
  report.assertions.push('Local search filters official rows without changing values');
  const pendingDownload=page.waitForEvent('download');
  await page.locator('[data-export="team-data-table"]').click();
  const download=await pendingDownload;
  await download.saveAs(join(out,'filtered-teams.csv'));
  const csv=readFileSync(join(out,'filtered-teams.csv'),'utf8');
  assert.equal(csv.trim().split('\r\n').length,2);
  assert(csv.includes('Denver Nuggets')&&csv.includes('https://www.nba.com/stats/teams/traditional'));
  report.assertions.push('CSV export downloads filtered values with actual official URLs');
  await page.locator('[data-search-for="team-data-table"]').fill('');
  const pts=teams.getByRole('button',{name:'PTS',exact:false}).first();
  await pts.focus();await page.keyboard.press('Enter');
  assert.equal(await pts.locator('..').getAttribute('aria-sort'),'ascending');
  await page.keyboard.press('Enter');
  assert((await teams.locator('tbody tr').first().innerText()).includes('Denver Nuggets'));
  report.assertions.push('Keyboard table sort is numeric and reports aria-sort');
  await page.locator('h1').click();await page.keyboard.press('/');
  assert.equal(await page.locator('#page-search').evaluate(el=>el===document.activeElement),true);
  await page.keyboard.type('no-such-observation');
  assert.equal(await teams.locator('tbody tr:visible').count(),0);
  assert(await page.locator('[data-empty-for="team-data-table"]').isVisible());
  await page.keyboard.press('Escape');
  assert.equal(await teams.locator('tbody tr:visible').count(),30);
  report.assertions.push('Global search shortcut, empty state and Escape reset work');

  await page.goto(base+'review.html',{waitUntil:'networkidle'});
  await page.locator('[data-status-filter="review-register"]').selectOption('Needs review');
  assert.equal(await page.locator('#review-register tbody tr:visible').count(),catalog.flags.filter(f=>f.status==='Needs review').length);
  await page.locator('[data-status-filter="review-register"]').selectOption('Corrected');
  assert.equal(await page.locator('#review-register tbody tr:visible').count(),catalog.flags.filter(f=>f.status==='Corrected').length);
  report.assertions.push('Review filters match all current open/corrected catalog entries');
  await page.goto(base+'leaderboard.html',{waitUntil:'networkidle'});
  assert.equal(await page.locator('#candidate-status td[data-empty]').count(),40);
  assert((await page.locator('main').innerText()).includes('No eligible strategies'));
  report.assertions.push('No fictional ranks, ROI, CLV or rewards; all 40 missing cells stay blank');

  for(const [old,target] of Object.entries(manifest.legacy_redirects)){
    await page.goto(base+old,{waitUntil:'networkidle'});
    await page.waitForURL(base+target);
  }
  report.assertions.push(`All ${Object.keys(manifest.legacy_redirects).length} historical HTML URLs redirect to the right category/fragment`);
  const noJS=await browser.newContext({javaScriptEnabled:false,viewport:{width:1280,height:900}});
  const plain=await noJS.newPage();await plain.goto(base+'data.html');
  assert.equal(await plain.locator('#team-data-table tbody tr').count(),30);
  assert.equal(await plain.locator('#game-data-table tbody tr').count(),32);
  assert(await plain.locator('#team-data-table tbody tr a').count()>=30);
  report.assertions.push('Data and official links remain readable without JavaScript');
  // Keep the extra context alive until browser.close (serverless single-process build).

  await page.setViewportSize({width:390,height:844});
  for(const slug of visitPages)await visit(slug,'mobile');
  await page.goto(base+'index.html',{waitUntil:'networkidle'});
  await page.screenshot({path:join(out,'dashboard-mobile.png'),fullPage:true});
  assert.equal(await page.locator('#sidebar').getAttribute('aria-hidden'),'true');
  await page.getByRole('button',{name:'Open navigation',exact:true}).click();
  assert.equal(await page.locator('.menu-button').getAttribute('aria-expanded'),'true');
  assert.equal(await page.locator('#sidebar').getAttribute('aria-hidden'),null);
  assert(await page.locator('#sidebar').evaluate(el=>el.contains(document.activeElement)));
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('.menu-button').getAttribute('aria-expanded'),'false');
  assert(await page.locator('.menu-button').evaluate(el=>el===document.activeElement));
  report.assertions.push('Mobile navigation opens accessibly, closes with Escape and restores focus');

  assert.equal(report.runtime_errors.length,0,JSON.stringify(report.runtime_errors));
  assert.equal(report.accessibility_violations.length,0,JSON.stringify(report.accessibility_violations,null,2));
  report.status='passed';
  console.log(`OK: ${report.desktop_pages.length} desktop + ${report.mobile_pages.length} mobile pages, WCAG A/AA, ${report.assertions.length} interaction groups, no runtime errors.`);
}catch(error){report.status='failed';report.failure=String(error.stack||error);console.error(report.failure);process.exitCode=1;}
finally{
  writeFileSync(join(out,'browser-checks.json'),JSON.stringify(report,null,2)+'\n');
  if(browser)await browser.close();
  await new Promise(resolve=>server.close(resolve));
}
