#!/usr/bin/env node
/**
 * Browser frame-time probe (IMPROVEMENT_PROPOSALS 13.9).
 *
 * Opens a fresh seed-42 tank world in headless Chromium against a running
 * backend and frontend, then reports over a fixed window:
 *   - requestAnimationFrame intervals (fps, p50/p95/p99, long frames),
 *   - main-thread script/layout/task time per second (CDP Performance),
 *   - React render+commit time per WebSocket message (time under the
 *     scheduler's performWorkUntilDeadline; needs an unminified build or the
 *     dev server - minified bundles rename it),
 *   - the top self-time functions and the top app functions by inclusive time.
 *
 * Headless Chromium rasterizes canvas on the CPU, so native "(program)" time
 * and fps are pessimistic next to a GPU browser. JS costs (script time, React
 * per message) carry over; compare builds with interleaved A/B runs, and pause
 * other worlds first so the backend's message rate stays steady.
 *
 * Usage (backend on :8000, frontend on APP):
 *   node scripts/frame-probe.mjs
 *   APP=http://127.0.0.1:4173 SECONDS=30 node scripts/frame-probe.mjs
 *   CHROME=/opt/pw-browsers/chromium node scripts/frame-probe.mjs  # pin a browser binary
 */
import { chromium } from '@playwright/test';

const API = process.env.API ?? 'http://127.0.0.1:8000';
const APP = process.env.APP ?? 'http://127.0.0.1:5173';
const SECONDS = Number(process.env.SECONDS ?? 20);
const WARMUP = Number(process.env.WARMUP ?? 8);
const TOPN = Number(process.env.TOPN ?? 20);

const browser = await chromium.launch(process.env.CHROME ? { executablePath: process.env.CHROME } : {});
const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
await page.addInitScript(() => {
    const Native = window.WebSocket;
    window.__probeMessages = 0;
    function Counting(...args) {
        const socket = new Native(...args);
        socket.addEventListener('message', () => window.__probeMessages++);
        return socket;
    }
    Counting.prototype = Native.prototype;
    Object.assign(Counting, Native);
    window.WebSocket = Counting;
});

const created = await page.request.post(`${API}/api/worlds`, {
    data: { world_type: 'tank', name: `frame-probe-${Date.now()}`, persistent: false, seed: 42, start_paused: false },
});
const { world_id: worldId } = await created.json();

try {
    await page.goto(`${APP}/tank/${worldId}`);
    await page.waitForSelector('canvas.tank-canvas', { timeout: 30_000 });
    await page.waitForTimeout(WARMUP * 1000);

    const cdp = await page.context().newCDPSession(page);
    const metrics = async () =>
        Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map((m) => [m.name, m.value]));
    await cdp.send('Performance.enable');
    await cdp.send('Profiler.enable');
    await cdp.send('Profiler.setSamplingInterval', { interval: 200 });

    const before = await metrics();
    const messagesBefore = await page.evaluate(() => window.__probeMessages);
    await cdp.send('Profiler.start');
    const intervals = await page.evaluate(async (seconds) => {
        const out = [];
        let last = performance.now();
        const end = last + seconds * 1000;
        await new Promise((resolve) => {
            const tick = (t) => {
                out.push(t - last);
                last = t;
                if (t < end) requestAnimationFrame(tick);
                else resolve();
            };
            requestAnimationFrame(tick);
        });
        return out;
    }, SECONDS);
    const { profile } = await cdp.send('Profiler.stop');
    const after = await metrics();
    const messages = (await page.evaluate(() => window.__probeMessages)) - messagesBefore;

    const sorted = [...intervals].sort((a, b) => a - b);
    const pct = (p) => sorted[Math.min(sorted.length - 1, Math.floor(p * sorted.length))];
    const perSecond = (key) => ((after[key] - before[key]) / SECONDS) * 1000;
    const round = (x, d = 1) => Number(x.toFixed(d));

    const nodes = new Map(profile.nodes.map((n) => [n.id, n]));
    const parent = new Map();
    profile.nodes.forEach((n) => (n.children ?? []).forEach((c) => parent.set(c, n.id)));
    const ancestors = function* (id) {
        for (let cur = id; cur !== undefined; cur = parent.get(cur)) yield nodes.get(cur).callFrame;
    };
    const label = (f) =>
        `${f.functionName || '(anon)'}  ${f.url.replace(/^https?:\/\/[^/]+\//, '').replace(/\?.*$/, '')}:${f.lineNumber + 1}`;

    const self = new Map();
    const inclusive = new Map();
    let reactUs = 0;
    profile.samples.forEach((id, i) => {
        const dt = profile.timeDeltas[i] ?? 0;
        const own = label(nodes.get(id).callFrame);
        self.set(own, (self.get(own) ?? 0) + dt);
        const seen = new Set();
        let inReact = false;
        for (const frame of ancestors(id)) {
            if (frame.functionName === 'performWorkUntilDeadline') inReact = true;
            if (!/\/(src|assets)\//.test(frame.url)) continue;
            const key = label(frame);
            if (seen.has(key)) continue;
            seen.add(key);
            inclusive.set(key, (inclusive.get(key) ?? 0) + dt);
        }
        if (inReact) reactUs += dt;
    });

    console.log(
        JSON.stringify(
            {
                app: APP,
                seconds: SECONDS,
                fps: round(intervals.length / SECONDS),
                frame_ms: { p50: round(pct(0.5)), p95: round(pct(0.95)), p99: round(pct(0.99)), max: round(sorted.at(-1)) },
                long_frames_over_33ms: intervals.filter((x) => x > 33.4).length,
                ws_messages_per_s: round(messages / SECONDS),
                main_thread_ms_per_s: {
                    script: round(perSecond('ScriptDuration'), 0),
                    layout: round(perSecond('LayoutDuration'), 0),
                    task: round(perSecond('TaskDuration'), 0),
                },
                react_ms_per_message: round(reactUs / 1000 / Math.max(1, messages), 2),
            },
            null,
            2
        )
    );
    const table = (title, map) => {
        console.log(`\n${title}`);
        [...map.entries()]
            .sort((a, b) => b[1] - a[1])
            .slice(0, TOPN)
            .forEach(([key, us]) => console.log(`${(us / 1000 / SECONDS).toFixed(1).padStart(7)} ms/s  ${key}`));
    };
    table('self time:', self);
    table('inclusive time, app code:', inclusive);
} finally {
    await page.request.delete(`${API}/api/worlds/${worldId}`).catch(() => {});
    await browser.close();
}
