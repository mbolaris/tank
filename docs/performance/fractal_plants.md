# Fractal plant performance review

This note summarizes the most expensive parts of the fractal plant pipeline across the simulation engine and renderer, plus a small targeted optimization.

## Backend lifecycle
- Passive growth increases plant size and genetic fitness every frame, so the `_update_size` and `genome.update_fitness` calls run per plant on each tick. The work scales linearly with plant count and affects nectar spawning eligibility via `get_fractal_iterations` (iteration count controls render detail).【F:core/entities/fractal_plant.py†L88-L157】【F:core/entities/fractal_plant.py†L237-L291】
- Fractal iteration decisions use hysteresis but still rely on size recomputation after every energy change, meaning frequent `_collect_energy` updates indirectly influence renderer complexity (1–3 iterations).【F:core/entities/fractal_plant.py†L157-L206】【F:core/entities/fractal_plant.py†L208-L236】

## Frontend renderer
- Plants cache their generated L-system geometry per column, but they previously re-sorted segments by depth on every frame before drawing. That per-frame sort cost grows with iteration depth and plant count.【F:frontend/src/utils/fractalPlant.ts†L283-L365】
- Render-time color conversions and leaf/stem strokes happen for each segment; these operations scale with the generated segment list size that depends on iteration count and genome rules.【F:frontend/src/utils/fractalPlant.ts†L283-L408】

## Applied optimization
- Segment depth ordering is now cached alongside the generated geometry so repeated renders reuse the sorted list instead of cloning and sorting every frame. This removes an `O(n log n)` cost per plant per frame when iterations remain stable, reducing CPU time during animation-heavy scenes.【F:frontend/src/utils/fractalPlant.ts†L44-L52】【F:frontend/src/utils/fractalPlant.ts†L305-L323】【F:frontend/src/utils/fractalPlant.ts†L351-L394】

## Next steps
- Profile render times while varying the iteration count (1–3) and population size to confirm the new cache eliminates sorting overhead and to quantify the cost of color conversions and leaf fills.
- Consider moving other deterministic calculations (e.g., color selection) into the cache when genomes are stable to further reduce per-frame work.
