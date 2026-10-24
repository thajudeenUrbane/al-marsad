// Sky Atlas browser check: run with `node sky-atlas/source/check_features.cjs` (needs Playwright and Chromium).
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 1400, height: 1000 } });
  const errs = [];
  p.on('pageerror', e => errs.push('pageerror: ' + e.message));
  p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errs.push(m.type() + ': ' + m.text()); });
  await p.goto('file://' + require('path').join(__dirname, '..', 'index.html'));
  await p.waitForTimeout(1200);
  const shot = async (name) => { await p.waitForTimeout(1500); await p.locator('.stage').screenshot({ path: require('path').join(require('os').tmpdir(), 'sky-atlas-') + '' + name + '.png' }); };
  await shot('01-start');
  // journey: Badr
  await p.selectOption('#journey-pick', 'badr'); await p.click('#journey-start');
  await shot('02-badr-1');
  console.log('bar:', await p.textContent('#jb-title'), '|', await p.textContent('#jb-stop'));
  await p.click('#jb-next'); await p.click('#jb-next');
  await shot('03-badr-3');
  console.log('panel note:', (await p.textContent('.journey-note')).slice(0, 200));
  await p.click('#jb-end');
  // hijrah
  await p.selectOption('#journey-pick', 'hijrah'); await p.click('#journey-start');
  console.log('hijrah stops:', await p.textContent('#jb-stop'));
  await p.click('#jb-next'); await p.click('#jb-next'); await shot('04-hijrah');
  await p.click('#jb-end');
  // who was there: focus Battle of Badr by search
  await p.fill('#obs-search', 'Battle of Badr'); await p.press('#obs-search', 'Enter');
  await shot('05-badr-event');
  console.log('presence:', (await p.textContent('.presence')).slice(0, 400));
  await p.click('#obs-home');
  // chain light
  await p.click('#sky-chain'); await shot('06-chain');
  console.log('gen pressed', await p.getAttribute('#sky-generation', 'aria-pressed'));
  await p.click('#sky-generation');
  // test load + clusters + gpu
  await p.selectOption('#scale-pick', '50000'); await shot('07-test-cpu');
  await p.click('#sky-gpu'); 
  const c = p.locator('#obs-canvas'); const bb = await c.boundingBox();
  await p.mouse.move(bb.x + 300, bb.y + 300); await p.mouse.down(); await p.mouse.move(bb.x + 420, bb.y + 340, { steps: 20 }); await p.mouse.up();
  await shot('08-test-gpu');
  console.log('perf:', await p.textContent('#sky-perf'));
  await p.selectOption('#scale-pick', '0'); await p.click('#sky-gpu'); await p.click('#sky-cluster');
  // globe
  await p.click('#frame-globe'); await shot('09-globe'); await p.fill('#obs-search','al-Madina'); await p.press('#obs-search','Enter'); await shot('09b-globe-madina');
  await p.mouse.move(bb.x + 500, bb.y + 400); await p.mouse.down(); await p.mouse.move(bb.x + 420, bb.y + 380, { steps: 10 }); await p.mouse.up();
  await p.mouse.wheel(0, 500); await shot('10-globe-out');
  console.log('textalt globe:', (await p.textContent('#obs-textalt-body')).slice(0, 300));
  await p.click('#frame-network'); await shot('11-back-sky');
  // arabic
  await p.click('#lang-switch'); await p.waitForTimeout(500);
  await p.screenshot({ path: require('path').join(require('os').tmpdir(), 'sky-atlas-12-arabic-page.png') });
  console.log('dir', await p.getAttribute('html', 'dir'), 'title', await p.title());
  await p.fill('#obs-search', 'Battle of Badr'); await p.press('#obs-search', 'Enter');
  await p.waitForTimeout(1500);
  await p.screenshot({ path: require('path').join(require('os').tmpdir(), 'sky-atlas-13-arabic-focus.png') });
  // phone
  await p.click('#lang-switch');
  await p.setViewportSize({ width: 390, height: 844 });
  await p.click('#obs-home');
  await p.selectOption('#journey-pick', 'first_believers'); await p.click('#journey-start');
  await p.waitForTimeout(1600);
  await p.screenshot({ path: require('path').join(require('os').tmpdir(), 'sky-atlas-14-phone.png') });
  const sw = await p.evaluate(() => document.documentElement.scrollWidth);
  console.log('phone scrollWidth', sw);
  console.log('ERRORS:', errs.length ? errs.join('\n') : 'none');
  await b.close();
  process.exitCode = errs.some((e) => e.startsWith('pageerror')) ? 1 : 0;
})();
