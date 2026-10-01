/* Run against the local preview. Optional dependency: playwright-core in .tools/browser. */
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || '../.tools/browser/node_modules/playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const project = path.basename(path.resolve(__dirname, '..'));
const base = process.env.PREVIEW_URL || (project === 'BMatic' ? 'http://127.0.0.1:4000' : 'http://127.0.0.1:4174');
const routes = project === 'BMatic' ? ['/', '/designs/', '/404.html'] : ['/', '/not-a-real-link'];
const output = path.resolve(__dirname, '../.tools/theme-check');
fs.mkdirSync(output, {recursive:true});
(async () => {
  const browser = await chromium.launch({channel:'chrome',headless:true});
  try {
    for (const width of [320,390,1440]) {
      const context = await browser.newContext({viewport:{width,height:900},colorScheme:'dark',reducedMotion:'reduce'});
      const page = await context.newPage();
      const failures=[];
      page.on('pageerror',e=>failures.push(e.message));
      for (const route of routes) {
        await page.goto(base + route);
        const toggle=page.getByRole('button',{name:'Dark mode',exact:true});
        await toggle.waitFor({state:'visible'});
        assert.equal(await toggle.getAttribute('aria-pressed'),'true');
        assert.equal(await page.evaluate(()=>getComputedStyle(document.body).backgroundColor),'rgb(8, 19, 39)');
        assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'no overflow');
        assert((await toggle.boundingBox()).height>=44,'44px toggle');
        if(route==='/') await page.screenshot({path:path.join(output,`dark-${width}.png`),fullPage:true});
        await toggle.focus();
        assert.notEqual(await toggle.evaluate(e=>getComputedStyle(e).outlineStyle),'none');
        await page.keyboard.press('Space');
        assert.equal(await toggle.getAttribute('aria-pressed'),'false');
        assert.equal(await page.evaluate(()=>getComputedStyle(document.body).backgroundColor),'rgb(244, 246, 250)');
        await page.reload();
        assert.equal(await toggle.getAttribute('aria-pressed'),'false','saved choice on reload');
        if(route==='/') await page.screenshot({path:path.join(output,`light-${width}.png`),fullPage:true});
        await toggle.press('Enter');
        assert.equal(await toggle.getAttribute('aria-pressed'),'true');
      }
      assert.deepEqual(failures,[]);
      // Same-origin tabs share manual choices; distinct site domains stay independent.
      const second=await context.newPage(); await second.goto(base);
      await page.getByRole('button',{name:'Dark mode',exact:true}).click();
      await second.waitForFunction(()=>document.documentElement.dataset.theme==='light');
      await context.close();
      console.log(`PASS ${project} ${width}px: dark/light layouts, keyboard, reload, navigation and tab sync`);
    }
    const system=await browser.newContext({colorScheme:'light'});
    const page=await system.newPage(); await page.goto(base);
    await page.emulateMedia({colorScheme:'dark'});
    await page.waitForFunction(()=>document.documentElement.dataset.theme==='dark');
    await page.getByRole('button',{name:'Dark mode',exact:true}).click();
    await page.emulateMedia({colorScheme:'light'}); await page.emulateMedia({colorScheme:'dark'});
    assert.equal(await page.locator('html').getAttribute('data-theme'),'light','manual override beats system');
    await system.close();
    for(const scheme of ['dark','light']) {
      const nojs=await browser.newContext({javaScriptEnabled:false,colorScheme:scheme});
      const p=await nojs.newPage(); await p.goto(base);
      assert(await p.locator('[data-theme-toggle]').isHidden());
      assert.equal(await p.evaluate(()=>getComputedStyle(document.body).backgroundColor),scheme==='dark'?'rgb(8, 19, 39)':'rgb(244, 246, 250)');
      await nojs.close();
    }
    const blocked=await browser.newContext({colorScheme:'light'});
    await blocked.addInitScript(()=>{Storage.prototype.getItem=()=>{throw new Error('blocked')};Storage.prototype.setItem=()=>{throw new Error('blocked')};});
    const p=await blocked.newPage();await p.goto(base);await p.getByRole('button',{name:'Dark mode',exact:true}).click();
    assert.equal(await p.locator('html').getAttribute('data-theme'),'dark');
    await blocked.close();
    console.log(`PASS ${project}: live system changes, manual override, no-JS fallback and blocked storage`);
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
