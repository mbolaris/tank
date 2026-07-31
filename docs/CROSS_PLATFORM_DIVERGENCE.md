# Cross-platform benchmark divergence: root cause

**Status:** root cause identified. The `gauss`/genetics half is fixed (#914,
2026-07-29) — `core/deterministic_random.normal` replaces `random.gauss` at
all 17 call sites in `core/` with a Marsaglia polar-method sampler that uses
only `random()`, `log()`, and `sqrt()`, all verified bit-identical across
platforms. The four affected champions were re-baselined from CI's own run in
the same PR. The `math.cos` half in movement, steering, and
physics (34 call sites) is **not yet fixed** — see "What remains" below.
Champions must still be re-baselined from CI artifacts (see
`tools/float_fingerprint.py` and the `rebaseline-tank-champions` job in
`bench.yml`), since local runs still diverge for anything that exercises
those call sites.

## The symptom

Tank benchmarks reproduce bit-for-bit *within* a machine and not *across*
machines. For the same commit, with matching `config_hash`, and with
`PYTHONHASHSEED` explicitly ruled out:

| environment | `tank/ecosystem_health_10k` seed 42 |
| --- | --- |
| Windows, CPython 3.14 | `10.150218544250826` |
| CI Linux, CPython 3.10 | `9.967411959401476` |

The practical costs: a champion can only be re-baselined from a CI artifact, a
local run can never confirm a champion reproduces, and a "regression" can be
nothing but a change of machine.

## The cause

IEEE 754 requires correctly-rounded results for `+ - * /` and `sqrt`. It says
nothing about transcendental functions, so `sin`, `cos`, `exp` and friends come
from the platform's libm and may differ in the last ulp.

`tools/float_fingerprint.py` hashes each primitive so two environments can be
diffed directly. Comparing Windows/CPython 3.14 against CI's Linux/CPython
3.10, **exactly two independent primitives differ**:

| primitive | agrees? |
| --- | --- |
| `sqrt`, `sin`, `atan`, `atan2`, `hypot`, `exp`, `log`, `asin`, `pow` | identical |
| `random()`, `uniform`, `randint`, `sum`, `fsum` | identical |
| **`cos`** | **differs** |
| **`tan`** | **differs** |
| **`gauss`** | **differs - see below** |

`gauss` is not a third cause. CPython implements it with Box-Muller:

```python
x2pi = random() * TWOPI
g2rad = _sqrt(-2.0 * _log(1.0 - random()))
z = _cos(x2pi) * g2rad
```

It differs *because* `cos` does. Note that `sin` agrees while `cos` does not,
which is why this could not be guessed - only measured.

## Why it matters more than "a last-ulp difference"

`random.gauss` is the mutation sampler. It has 17 call sites in `core/`, and
they are the genetics:

- `core/evolution/mutation.py`
- `core/algorithms/base.py`, `core/algorithms/composable/behavior.py`
- `core/behavior/graph.py`, `core/behavior/target_memory.py`
- `core/code_pool/pool.py`, `core/code_pool/genome_code_pool.py`

So the divergence is not a rounding error that slowly accumulates in the
physics. **Every genetic mutation draws a number that differs between Windows
and Linux**, from the first mutation onward. `math.cos` additionally has 34
call sites in movement, steering, and physics (`grep -rn 'math\.cos(' core/`,
measured 2026-07-30). `math.tan` currently has none, so that row is harmless
today — it stays in the fingerprint table because a future call site would
silently reopen it.

## The fix, applied to the mutation sampler (#914)

The mutation half was cleanly fixable. The Marsaglia polar method samples a
normal deviate using only `random()`, `log()` and `sqrt()` - all three verified
bit-identical above:

```python
while True:
    u = 2.0 * rng.random() - 1.0
    v = 2.0 * rng.random() - 1.0
    s = u * u + v * v
    if 0.0 < s < 1.0:
        break
return mu + sigma * u * math.sqrt(-2.0 * math.log(s) / s)
```

`core/deterministic_random.normal` now implements this and replaces
`random.gauss` at all 17 call sites in `core/` (the 16 genetics ones plus
soccer's kick noise, which feeds a champion). `tests/test_deterministic_random.py`
pins both halves: the sampler is monkeypatched against
`math.cos`/`sin`/`tan`/`exp`/`pow` so it can never regain a transcendental
call, and a tree scan fails if `core/` reintroduces `.gauss(`.

This consumed a different number of RNG draws than `gauss` (a rejection loop
with a ~21.5% reject rate, versus `gauss`'s fixed two draws), so every
downstream random decision reshuffled and every benchmark score moved. The
four affected champions were re-baselined from CI's own run
(`tank/survival_5k`, `tank/ecosystem_health_10k`, `soccer/training_3k`,
`soccer/training_5k`) in a follow-up commit in the same PR, not from a local
re-run — consistent with the divergence this fix exists to remove.
`config_hash` was unchanged for all four: this was code behavior, not
configuration.

## What remains

The `math.cos` call sites in movement and steering are the harder half and
have no equally clean answer — `cos` is load-bearing there (rotation, facing
angles, wave motion), not swappable for an algebraic equivalent the way a
normal sampler is. There are 34 of them across `core/` (movement, steering,
soccer physics, foraging, pursuit, petri geometry, interactions). Not all of
them necessarily cause observable benchmark divergence, so `tools/audit_cos_call_sites.py`
(2026-07-31) answers the question directly instead of guessing: for each call
site, does it ever execute during a real run of each benchmark (AST-located
call sites, `math.cos` monkeypatched with a frame-inspecting wrapper), and if
so, does perturbing its return value by 1e-9 relative (far larger than a
real last-ulp difference of ~1e-16, so a call site insensitive at 1e-9 is
certainly insensitive at 1e-16) change that benchmark's final score.

**Results, run against 8 benchmarks (seed 42, one platform):**

| Tier | Call sites | Where | Reachability |
| --- | --- | --- | --- |
| 1 — CI-gated, confirmed sensitive | 8 | `behavior/primitives/steering.py` (3: `wander_step`, `circling_target`, `blend_patrol_steering`), `movement_strategy.py` (1), `tank_interactions.py` (2, tank-object rotation), `minigames/soccer/engine.py` (2, kick physics) | Reached by `tank/survival_5k`, `tank/ecosystem_health_10k`, and/or `soccer/training_5k` \| `ladder_5k` — the benchmarks CI verify-determinism-gates or champion-tracks. Perturbing any of them changed every one of those four benchmarks' final score. |
| 2 — reached, not CI-gated | 19 | `pursuit/transfer_gym.py` (15), `behavior/target_memory_transfer_scenarios.py` (3), `foraging/gym.py` (1 — plus that benchmark also reuses tier-1's `wander_step`) | Reached only by `tank/pursuit_transfer`, `tank/target_memory_transfer`, `tank/foraging_gym` — real research benchmarks, but none of the three is in `bench.yml`'s `--verify-determinism` set or has a `champions/` entry, so their `cos` usage doesn't currently block CI or a champion re-baseline. |
| 3 — unreached by any benchmark | 7 | `algorithms/food_seeking/cooperative.py`, `algorithms/food_seeking/opportunistic.py`, `entities/predators.py` (2), `worlds/petri/dish.py` (2), `worlds/petri/geometry.py` (1) | `CooperativeForager`/`OpportunisticFeeder` are two of the three surviving food-seeking algorithms (`core/algorithms/registry.py::ALL_ALGORITHMS`) but are comparison candidates for `tools/benchmark_algorithms.py`, not the genome's default `ComposableBehavior` — no CI job runs that tool. `Predator._update_petri_orbit` and both petri files are petri-world-only, and no benchmark in `benchmarks/` exercises petri at all. |

`poker/ladder_20k` never touches `math.cos` (zero hits) — confirms the
existing "poker rulers unaffected" claim from #914 empirically rather than by
inspection.

**Conclusion:** cross-machine reproducibility of the two benchmarks CI
actually gates and re-baselines (`tank/survival_5k`, `tank/ecosystem_health_10k`)
depends on exactly 6 of the 34 sites (steering's 3 + `movement_strategy.py`'s
1 + `tank_interactions.py`'s 2); soccer's `training_5k`/`ladder_5k` depend on
2 more (`minigames/soccer/engine.py`). Fixing those 8 would close the
remaining gap for every currently CI-gated benchmark without touching the
other 26 sites, which either serve non-gated research benchmarks (tier 2 —
worth revisiting if/when those benchmarks get champion-tracked, not before)
or are provably unreached today (tier 3). None of the 8 has a clean
algebraic substitute the way `gauss` did — an actual fix would mean a
portable correctly-rounded `cos` (expensive) or accepting these as the
permanent re-baseline-from-CI boundary and documenting it as such. That
decision is unmade; this investigation's job was narrowing the scope, not
picking the fix.

## Reproducing

```bash
python tools/float_fingerprint.py                     # on the dev machine
gh workflow run bench.yml -f float_fingerprint=true   # on CI, then read the log
```

Identical lines exonerate a primitive; differing lines are a concrete
mechanism. The tool checks primitives, not the simulation - matching output
does not prove a benchmark agrees, only that this explanation is not the cause.
