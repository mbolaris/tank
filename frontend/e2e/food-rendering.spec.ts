import { expect, test } from '@playwright/test';

/**
 * Food is drawn from cached sprites (renderer_food_halo.ts,
 * renderer_live_food.ts) instead of fresh gradients and paths per item per
 * frame. Only a real canvas can confirm that still looks the same, so this
 * draws the same scene both ways in Chromium - at several canvas scales and
 * animation times, over the continuous sizes live food takes as it is bitten -
 * and bounds the per-pixel difference. Resampling a sprite at fractional
 * positions costs a few levels per channel; a wrong gradient, alpha or
 * geometry costs far more.
 */

const MAX_CHANNEL_DIFF = 8;

interface DiffResult {
    scale: number;
    time: number;
    maxChannelDiff: number;
    stateAfter: string;
}

test('sprite-drawn food matches the direct drawing', async ({ page }) => {
    await page.goto('/');
    const results: Record<string, DiffResult[]> = await page.evaluate(async () => {
        // Served by the Vite dev server the e2e config starts.
        const liveUrl = '/src/utils/renderer_live_food.ts';
        const haloUrl = '/src/utils/renderer_food_halo.ts';
        const live = await import(/* @vite-ignore */ liveUrl);
        const halo = await import(/* @vite-ignore */ haloUrl);
        type Draw = (
            ctx: CanvasRenderingContext2D,
            x: number,
            y: number,
            w: number,
            h: number,
            sw: number,
            sh: number,
            t: number
        ) => void;
        const cases: Record<string, { direct: Draw; fast: Draw; sizes: number[]; scale: number }> = {
            live: {
                direct: live.drawLiveFoodDirect,
                fast: live.drawLiveFood,
                sizes: [10.69, 15.55, 21.46, 25.82, 27.9, 34.7, 41.79, 50],
                scale: 0.35,
            },
            halo: {
                direct: (c, x, y, w, h, sw, sh) => halo.drawFoodHaloDirect(c, x, y, w, h, sw, sh),
                fast: (c, x, y, w, h, sw, sh) => halo.drawFoodHalo(c, x, y, w, h, sw, sh),
                sizes: [10, 18.17, 38.27, 50],
                scale: 0.7,
            },
        };
        const W = 600;
        const H = 400;
        const out: Record<string, DiffResult[]> = {};
        for (const [name, { direct, fast, sizes, scale: foodScale }] of Object.entries(cases)) {
            out[name] = [];
            for (const scale of [0.83, 1, 1.4706, 2]) {
                for (const time of [0, 317, 1234.5, 99999]) {
                    const make = () => {
                        const canvas = document.createElement('canvas');
                        canvas.width = W;
                        canvas.height = H;
                        const ctx = canvas.getContext('2d')!;
                        ctx.fillStyle = '#0b3d5c';
                        ctx.fillRect(0, 0, W, H);
                        ctx.scale(scale, scale);
                        return ctx;
                    };
                    const a = make();
                    const b = make();
                    for (let i = 0; i < 40; i++) {
                        const s = sizes[i % sizes.length];
                        const x = 17.3 + (i % 8) * 34.71;
                        const y = 13.9 + Math.floor(i / 8) * 43.37;
                        direct(a, x, y, s, s, s * foodScale, s * foodScale, time);
                        fast(b, x, y, s, s, s * foodScale, s * foodScale, time);
                    }
                    const da = a.getImageData(0, 0, W, H).data;
                    const db = b.getImageData(0, 0, W, H).data;
                    let maxChannelDiff = 0;
                    for (let p = 0; p < da.length; p += 4) {
                        for (let ch = 0; ch < 3; ch++) {
                            maxChannelDiff = Math.max(maxChannelDiff, Math.abs(da[p + ch] - db[p + ch]));
                        }
                    }
                    const stateAfter = [b.globalAlpha, b.lineWidth, b.fillStyle, b.strokeStyle].join(',');
                    out[name].push({ scale, time, maxChannelDiff, stateAfter });
                }
            }
        }
        return out;
    });

    for (const [name, rows] of Object.entries(results)) {
        for (const row of rows) {
            const label = `${name} at scale ${row.scale}, t=${row.time}`;
            expect(row.maxChannelDiff, label).toBeLessThanOrEqual(MAX_CHANNEL_DIFF);
            // The fast path must hand the context back as it found it.
            expect(row.stateAfter, label).toBe('1,1,#0b3d5c,#000000');
        }
    }
});
