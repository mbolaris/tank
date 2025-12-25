Safe fixes to commit (dev-focused):

1) `frontend/src/utils/fractalPlant.ts`
   - Ensure global shared caches on `globalThis.__FRACTAL_PLANT_MODULE_CACHE_v1`.
   - Wire `sweepOrphanFractalCaches()` to run on module load and from `clearAllFractalPlantCaches()`.
   - Add `DEV_SUPPRESS_FRACTAL_CACHING` flag and setter.
   - Add canvas creation/clear diagnostics and export `devRecordCanvasCreatedForDiagnostics()` and `devMarkCanvasClearedForDiagnostics()` hooks.
   - Reduce MAX_ENTRIES from 32 to 8 to cap growth conservatively.

2) `frontend/src/utils/renderer.ts`
   - Add `purgeSurfaces()` method to reset main/tint canvases to drop GPU/ImageBitmap backings.
   - Use `devRecordCanvasCreatedForDiagnostics()` and `devMarkCanvasClearedForDiagnostics()` where safe (tint canvas creation/clear).

3) `frontend/src/components/Canvas.tsx`
   - Expose `Renderer.exposeDiagnostics()` and a safe dev-only `__TANK_GET_RENDERER` getter.
   - Add (and stash) WIP dev helpers in `frontend/src/dev_helpers/DEV_WIP_PURGE.md` for later manual re-application.

Notes for commit:
- These are dev-only and safe: guarded by `process.env.NODE_ENV === 'development'` where applicable.
- Avoid landing auto-purge watch in production; WIP is stashed in a helper markdown file.

Suggested local git commands:

```bash
git add frontend/src/utils/fractalPlant.ts frontend/src/utils/renderer.ts frontend/src/components/Canvas.tsx frontend/src/dev_helpers/DEV_WIP_PURGE.md FRAGMENTED_CHANGELOG_DEV.md
git commit -m "Dev: add fractal cache safeguards, canvas purge helper, and diagnostics; stash auto-purge WIP"
```
