WIP: Dev auto-purge and purge button

This file stashes the experimental dev-only auto-purge/watchdog and UI helpers that were added to Canvas.tsx for investigating native memory growth.

What was added (summary):

- A dev-only auto-purge useEffect in `Canvas.tsx` that periodically calls `renderer.purgeSurfaces()`, `clearAllFractalPlantCaches()`, and `ImageLoader.clearCache()` every 20s. Enabled by default via `window.__TANK_DEV_AUTO_PURGE = true`.
- A dev-only "Purge Canvases (DEV)" button alongside the cache controls that calls `renderer.purgeSurfaces()`.
- A dev-only getter exposed on `window.__TANK_GET_RENDERER` to access the active `Renderer` instance.

Why stash:
- These helpers are useful for debugging but are noisy and risky to land in main. We'll keep them in this WIP file so they can be re-applied by a developer when needed.

How to re-apply:
- Copy the relevant useEffect and UI button code back into `frontend/src/components/Canvas.tsx` under the `process.env.NODE_ENV === 'development'` guard.

Notes:
- The auto-purge interval and toggle are configurable via `window.__TANK_DEV_AUTO_PURGE` and the code comments.
- Keep this file for now; it should be removed before any production release.
