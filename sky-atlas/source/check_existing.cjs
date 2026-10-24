// Sky Atlas browser check: run with `node sky-atlas/source/check_existing.cjs` (needs Playwright and Chromium).
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1300, height: 950 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto('file://' + require('path').join(__dirname, '..', 'index.html')); await p.waitForTimeout(800);
  for (const v of ['hijrah_abubakr','badr','first_believers','family','chain']) { await p.selectOption('#obs-preset', v); await p.waitForTimeout(400); }
  await p.click('#obs-trace'); await p.fill('#trace-a', await p.evaluate(()=>document.querySelectorAll('#obs-names option')[23].value));
  await p.fill('#trace-b', await p.evaluate(()=>document.querySelectorAll('#obs-names option')[0].value)); await p.click('.trace-form button[type=submit]');
  await p.waitForTimeout(500); console.log('trace:', (await p.textContent('.trace-out')).slice(0,120));
  await p.click('label[for=lens-discover]'); await p.waitForTimeout(500); await p.click('label[for=lens-research]'); await p.waitForTimeout(500);
  await p.click('#sky-play'); await p.waitForTimeout(2500); await p.click('#sky-play');
  await p.click('#frame-time'); await p.waitForTimeout(900); await p.click('#frame-isnad'); await p.waitForTimeout(900);
  await p.click('#sky-chain'); await p.click('#frame-globe'); await p.waitForTimeout(500); await p.click('#sky-play'); await p.waitForTimeout(1500);
  await p.click('#obs-home'); await p.waitForTimeout(500);
  await p.click('#lang-switch'); await p.click('label[for=lens-study]'); await p.click('#frame-time'); await p.waitForTimeout(900);
  await p.locator('.stage').screenshot({ path: require('path').join(require('os').tmpdir(), 'sky-atlas-15-ar-time.png') });
  console.log('errors:', errs.length ? errs : 'none');
  await b.close();
  process.exitCode = errs.length > 0 ? 1 : 0;
})();
