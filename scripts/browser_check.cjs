/* Local UI test only. Start scripts/preview.py first; no production JS. */
const { chromium } = require('../.tools/browser/node_modules/playwright-core');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const output = path.resolve(__dirname, '../.tools/screenshots');
fs.mkdirSync(output, {recursive: true});
(async () => {
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  try {
    for (const width of [320, 390, 768, 1440]) {
      const context = await browser.newContext({viewport:{width,height:900},javaScriptEnabled:false,reducedMotion:'reduce'});
      const page = await context.newPage();
      for (const [name, route, status] of [['home','/',200],['404','/not-a-real-link',404]]) {
        const response = await page.goto('http://127.0.0.1:4174' + route, {waitUntil:'networkidle'});
        assert.equal(response.status(), status);
        const state = await page.evaluate(() => ({
          width:innerWidth, scroll:document.documentElement.scrollWidth,
          broken:[...document.images].filter(x=>!x.complete||!x.naturalWidth).map(x=>x.src),
          scripts:document.scripts.length,
          small:[...document.querySelectorAll('a:not(.skip-link)')].filter(x=>x.getBoundingClientRect().height < 44).map(x=>x.textContent)
        }));
        assert(state.scroll <= state.width, `${name} at ${width}: horizontal overflow`);
        assert.deepEqual(state.broken, []);
        assert.deepEqual(state.small, [], 'Comfortable 44px touch targets');
        assert.equal(state.scripts, 1);
        await page.screenshot({path:path.join(output,`${name}-${width}.png`),fullPage:true});
        console.log(`PASS ${name} ${width}px: status ${status}, no overflow, images loaded, 44px links, JS disabled`);
      }
      await page.goto('http://127.0.0.1:4174/');
      await page.keyboard.press('Tab');
      assert.equal(await page.locator(':focus').textContent(), 'Skip to links');
      const focus = await page.locator(':focus').evaluate(x=>({top:x.getBoundingClientRect().top,outline:getComputedStyle(x).outlineStyle}));
      assert(focus.top >= 0 && focus.outline !== 'none');
      await page.keyboard.press('Enter');
      assert.equal(await page.locator(':focus').getAttribute('id'), 'main');
      await page.keyboard.press('Tab');
      assert.equal(await page.locator(':focus').getAttribute('href'), '/designs');
      const cardOutline = await page.locator(':focus').evaluate(x=>getComputedStyle(x).outlineStyle);
      assert.equal(cardOutline,'solid');
      await page.screenshot({path:path.join(output,`focus-${width}.png`)});
      // Inspect the actual 302 without visiting the external destination.
      const redirect = await context.request.get('http://127.0.0.1:4174/designs', {maxRedirects:0});
      assert.equal(redirect.status(),302);
      assert.equal(redirect.headers().location,'https://bmatic.xyz/');
      await context.close();
    }
    console.log('PASS: 8 page/viewport combinations plus keyboard, focus and real local HTTP redirects.');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
