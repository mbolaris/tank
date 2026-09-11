import { chromium } from 'playwright';
const OUT = process.argv[2];
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const p = await b.newPage({ viewport: { width: 1600, height: 1000 } });
await p.goto('http://127.0.0.1:3000/', { waitUntil: 'networkidle', timeout: 60000 });
await p.waitForTimeout(7000);
// Report what the backend says the feeders are doing right now.
const feeders = await p.evaluate(() => {
  const w = window;
  const ents = w.__lastEntities || [];
  return ents;
});
const box = await (await p.locator('canvas.tank-canvas').first()).boundingBox();
// Zoom into the lower-left reef using the new camera.
await p.mouse.move(box.x + box.width * 0.22, box.y + box.height * 0.85);
for (let i = 0; i < 5; i++) { await p.mouse.wheel(0, -220); await p.waitForTimeout(110); }
await p.waitForTimeout(1500);
await p.screenshot({ path: `${OUT}/reef-zoom.png`, clip: { x: box.x, y: box.y, width: box.width, height: box.height } });
console.log('zoom:', (await p.textContent('[data-testid="camera-controls"] span')).trim());
await b.close();
