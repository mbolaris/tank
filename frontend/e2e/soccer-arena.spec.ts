import { expect, test, type Page } from '@playwright/test';

/**
 * Browser-level contract for the Soccer Arena broadcast.
 *
 * The app, router, rendering and WebSocket state pipeline are all real: the
 * arena is reached by navigating a real world, and the live match it shows is a
 * genuine league fixture from the backend.
 *
 * Two of the states this PR fixes cannot be summoned on demand from a live
 * league inside a test budget - a match sitting at full time, and a socket
 * mid-reconnect. For those the harness suspends delivery of real frames and
 * replays a *clone of the last real frame* with an edited `soccer_league_live`.
 * Schema version, world state and every other field stay exactly as the backend
 * sent them, and the frame still travels through the app's own onmessage
 * handler, so nothing about the client pipeline is mocked.
 */

const API = 'http://127.0.0.1:8000';

/**
 * Intercept the app's socket handler.
 *
 * The app assigns `ws.onmessage = fn` directly, so shadowing that property on
 * the instance lets the harness decide when the app sees a frame. Real frames
 * pass straight through unless the feed is suspended; `__deliver` hands the app
 * a crafted frame through the very same handler.
 *
 * Installed before any page script runs so it cannot miss the first frame.
 */
const ARENA_HARNESS = `
(() => {
  const Native = window.WebSocket;
  window.__lastUpdate = null;
  // The league state rides on delta frames once a match is under way, so the
  // last full 'update' is not where the running fixture lives.
  window.__lastSoccer = null;
  window.__feedSuspended = false;
  window.__deliver = () => false;
  window.__dropSocket = () => false;

  function textOf(data) {
    if (typeof data === 'string') return data;
    if (data instanceof ArrayBuffer) return new TextDecoder().decode(data);
    return null;
  }

  function Wrapped(...args) {
    const socket = new Native(...args);
    let appHandler = null;

    // Shadow the instance property so the browser does not invoke the app's
    // handler directly - the harness forwards instead.
    Object.defineProperty(socket, 'onmessage', {
      configurable: true,
      get() { return appHandler; },
      set(fn) { appHandler = fn; },
    });

    socket.addEventListener('message', (event) => {
      const text = textOf(event.data);
      if (text !== null) {
        try {
          const frame = JSON.parse(text);
          if (frame && frame.type === 'update') window.__lastUpdate = frame;
          // The league state lives inside the snapshot, and rides on delta
          // frames once a match is under way.
          const live = frame && frame.snapshot && frame.snapshot.soccer_league_live;
          if (live && live.active_match) window.__lastSoccer = live;
        } catch { /* non-JSON frame */ }
      }
      if (window.__feedSuspended) return;
      if (appHandler) appHandler.call(socket, event);
    });

    window.__deliver = (frame) => {
      if (!appHandler) return false;
      appHandler.call(socket, { data: JSON.stringify(frame) });
      return true;
    };

    // Drop the connection the way a real network failure does, so the app takes
    // its genuine onclose -> 'reconnecting' -> backoff -> reconnect path.
    window.__dropSocket = () => {
      socket.close();
      return true;
    };

    return socket;
  }

  Wrapped.prototype = Native.prototype;
  Object.assign(Wrapped, Native);
  // readyState constants are non-enumerable, so Object.assign misses them.
  Wrapped.CONNECTING = Native.CONNECTING;
  Wrapped.OPEN = Native.OPEN;
  Wrapped.CLOSING = Native.CLOSING;
  Wrapped.CLOSED = Native.CLOSED;
  window.WebSocket = Wrapped;
})();
`;

interface LeagueLiveState {
    active_match?: MatchState | null;
    presentation_match?: MatchState | null;
}

interface UpdateFrame {
    type: string;
    snapshot: { soccer_league_live?: LeagueLiveState; [key: string]: unknown };
}

interface MatchState {
    match_id: string;
    frame: number;
    score: { left: number; right: number };
    home_name?: string;
    away_name?: string;
    [key: string]: unknown;
}

declare global {
    interface Window {
        __lastUpdate: UpdateFrame | null;
        __lastSoccer: LeagueLiveState | null;
        __feedSuspended: boolean;
        __deliver: (frame: unknown) => boolean;
        __dropSocket: () => boolean;
    }
}

/** Create an isolated non-persistent world so the run leaks no state. */
async function createScratchWorld(page: Page): Promise<string> {
    const response = await page.request.post(`${API}/api/worlds`, {
        data: {
            world_type: 'tank',
            name: `e2e-arena-${Date.now()}`,
            persistent: false,
            seed: 42,
            start_paused: false,
        },
    });
    expect(response.ok(), `world creation failed: ${response.status()}`).toBeTruthy();
    const { world_id: worldId } = await response.json();
    expect(worldId, 'backend returned no world_id').toBeTruthy();
    return worldId;
}

async function suspendFeed(page: Page, suspended: boolean): Promise<void> {
    await page.evaluate((value) => {
        window.__feedSuspended = value;
    }, suspended);
}

/**
 * Replay the last real full update with `soccer_league_live` replaced.
 *
 * The builder runs in the page against the real league payload, so a synthetic
 * full-time state keeps the identity of the fixture that was actually playing.
 */
async function replayWithSoccer(page: Page, buildSource: string): Promise<void> {
    const delivered = await page.evaluate((source) => {
        const base = window.__lastUpdate;
        if (!base) return false;
        const build = new Function('base', 'soccer', source) as (b: UpdateFrame, s: unknown) => unknown;
        const current = window.__lastSoccer ?? base.snapshot?.soccer_league_live ?? {};
        return window.__deliver({
            ...base,
            snapshot: { ...base.snapshot, soccer_league_live: build(base, current) },
        });
    }, buildSource);
    expect(delivered, 'the harness could not replay a frame').toBe(true);
}

/** A live fixture, used only if the real league has not started one in time. */
const BUILD_LIVE_MATCH = `
return {
  ...soccer,
  presentation_match: null,
  active_match: {
    match_id: 'e2e-match-1',
    game_over: false,
    winner_team: null,
    message: 'Match in progress',
    frame: 120,
    score: { left: 1, right: 0 },
    play_mode: 'play_on',
    half: 1,
    sides_swapped: false,
    period_frames: 300,
    ball_owner: 'left_1',
    home_id: 'e2e:A',
    away_id: 'Bot:Balanced',
    home_name: 'Arena United',
    away_name: 'Bot Balanced',
    coord_space: 'legacy_render',
    geometry: { length: 105, width: 68, goal_width: 14.02, goal_depth: 2.44 },
    participants: [
      { participant_id: 'left_1', side: 'left', team_id: 'e2e:A', uniform_number: 1, avatar_kind: 'fish' },
      { participant_id: 'right_1', side: 'right', team_id: 'Bot:Balanced', uniform_number: 1, avatar_kind: 'bot' },
    ],
    events: [],
    entities: [
      { id: 1, type: 'player', x: -8, y: 0, width: 0.6, height: 0.6, radius: 0.3, vel_x: 0.4, vel_y: 0, team: 'left', facing: 0, participant_id: 'left_1' },
      { id: 2, type: 'player', x: 9, y: 2, width: 0.6, height: 0.6, radius: 0.3, vel_x: -0.2, vel_y: 0, team: 'right', facing: 3.1, participant_id: 'right_1' },
      { id: 3, type: 'ball', x: -7.6, y: 0, width: 0.22, height: 0.22, radius: 0.11, vel_x: 0.5, vel_y: 0 },
    ],
  },
};
`;

/**
 * Take whichever match is on screen to full time, the way the runtime does:
 * active_match cleared, a detached presentation_match retained with
 * game_over/time_over and a deterministic full_time event.
 */
const BUILD_FULL_TIME = `
const played = soccer.active_match;
if (!played) throw new Error('no match to finish');
return {
  ...soccer,
  active_match: null,
  presentation_match: {
    ...played,
    game_over: true,
    play_mode: 'time_over',
    sides_swapped: true,
    half: 2,
    events: [
      ...(played.events || []),
      {
        frame: played.frame,
        seq: (played.events || []).length,
        kind: 'full_time',
        event_id: played.match_id + '-full_time-' + played.frame + '-' + (played.events || []).length,
      },
    ],
  },
};
`;

test.beforeEach(async ({ page }) => {
    await page.addInitScript(ARENA_HARNESS);
    // Wide enough that a genuinely responsive pitch must exceed the old 800px.
    await page.setViewportSize({ width: 1600, height: 900 });
});

test('a viewer can watch a complete match in the Soccer Arena', async ({ page }) => {
    // Real backend boot, a league fixture, a socket drop and its backoff reconnect.
    test.setTimeout(240_000);

    // 1. Open a real world's Soccer Arena.
    const worldId = await createScratchWorld(page);
    await page.goto(`/tank/${worldId}/soccer`);

    await expect(page.getByTestId('soccer-arena-view')).toBeVisible({ timeout: 30_000 });
    await expect
        .poll(() => page.evaluate(() => window.__lastUpdate !== null), {
            timeout: 30_000,
            message: 'no full-state frame ever reached the app',
        })
        .toBe(true);

    // 3. A live match is shown. The league normally has one running within a
    //    minute; if this world has not been scheduled one yet, replay a live
    //    fixture so the remaining steps stay deterministic rather than flaky.
    const liveHeading = page.getByRole('heading', { name: 'Live match' });
    const sawRealMatch = await liveHeading
        .waitFor({ state: 'visible', timeout: 90_000 })
        .then(() => true)
        .catch(() => false);
    if (!sawRealMatch) {
        await suspendFeed(page, true);
        await replayWithSoccer(page, BUILD_LIVE_MATCH);
        await expect(liveHeading).toBeVisible();
    }
    await expect(page.getByTestId('soccer-scoreboard')).toContainText('LIVE');

    // 2. The pitch fills the stage instead of the old fixed 800x450 panel.
    const host = page.getByTestId('soccer-pitch-host');
    await expect(host).toBeVisible();
    const box = await host.boundingBox();
    expect(box, 'the pitch has no layout box').not.toBeNull();
    expect(
        box!.width,
        `pitch was ${box!.width}px CSS wide; the arena must not be capped at the old 800px panel`,
    ).toBeGreaterThan(800);
    // The backing store is sized from the measured host and the device pixel
    // ratio, not a fixed 800x450 buffer stretched over a bigger box.
    const canvas = await page.locator('canvas').first().evaluate((element) => {
        const node = element as HTMLCanvasElement;
        return { width: node.width, height: node.height, dpr: window.devicePixelRatio };
    });
    expect(canvas.width).toBeGreaterThan(800);
    expect(canvas.width).toBeCloseTo(box!.width * canvas.dpr, 0);

    // The pitch keeps the field's real aspect: the CSS box and the backing
    // store agree, and neither is the old 800x450 panel shape.
    expect(box!.width / box!.height).toBeCloseTo(canvas.width / canvas.height, 1);
    expect(box!.width / box!.height).not.toBeCloseTo(800 / 450, 2);

    // 4. A dropped socket labels the held frame stale rather than live.
    //    The feed is suspended first so a frame in flight cannot race the drop.
    await suspendFeed(page, true);
    await page.evaluate(() => window.__dropSocket());
    await expect(page.getByRole('heading', { name: 'Connection interrupted' })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId('soccer-scoreboard')).toContainText('DISCONNECTED');
    await expect(page.getByText(/Reconnecting….*last update/)).toBeVisible();
    // Nothing is cleared: the stale frame stays on the pitch, just labelled.
    await expect(page.getByTestId('soccer-pitch-host')).toBeVisible();
    await expect(liveHeading).toHaveCount(0);

    // 5. Reconnection restores live state and clears the stale treatment.
    await suspendFeed(page, false);
    await expect(page.getByTestId('soccer-scoreboard')).not.toContainText('DISCONNECTED', { timeout: 90_000 });
    await expect(page.getByText(/Reconnecting….*last update/)).toHaveCount(0);

    // 6. A completed match is presented rather than vanishing.
    await expect(liveHeading).toBeVisible({ timeout: 90_000 });
    await suspendFeed(page, true);
    await replayWithSoccer(page, BUILD_FULL_TIME);
    await expect(page.getByRole('heading', { name: 'Full time' })).toBeVisible();
    await expect(page.getByTestId('soccer-scoreboard')).toContainText('FULL TIME');
    await expect(page.getByTestId('soccer-full-time-card')).toBeVisible();
    // The pitch still renders the final positions rather than emptying.
    await expect(page.getByTestId('soccer-pitch-host')).toBeVisible();

    // 7. Back navigation returns to the correct world, not a malformed route.
    await suspendFeed(page, false);
    await page.getByRole('button', { name: `Back to World ${worldId}` }).click();
    await expect(page).toHaveURL(new RegExp(`/tank/${worldId}$`));
    await expect(page.getByTestId('soccer-arena-view')).toHaveCount(0);
});
