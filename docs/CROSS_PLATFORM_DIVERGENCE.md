# Cross-platform benchmark divergence: root cause

**Status:** root cause identified. The `gauss`/genetics half is fixed (#914,
2026-07-29) — `core/deterministic_random.normal` replaces `random.gauss` at
all 17 call sites in `core/` with a Marsaglia polar-method sampler that uses
only `random()`, `log()`, and `sqrt()`, all verified bit-identical across
platforms. The four affected champions were re-baselined from CI's own run in
the same PR. The `math.cos` half in movement, steering, and
physics (35 call sites) is **not yet fixed** — see "What remains" below.
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
and Linux**, from the first mutation onward. `math.cos` additionally has 35
call sites in movement, steering, and physics (measured 2026-07-30). `math.tan`
currently has none, so that row is harmless today — it stays in the
fingerprint table because a future call site would silently reopen it.

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
normal sampler is. There are 35 of them across `core/` (movement, steering,
soccer physics, foraging, pursuit, petri geometry, interactions). Not all of
them necessarily cause observable benchmark divergence — the next step is
determining *which* call sites actually move a benchmark trajectory before
deciding whether/how to replace them, rather than blanket-replacing all 35
indiscriminately.

## Reproducing

```bash
python tools/float_fingerprint.py                     # on the dev machine
gh workflow run bench.yml -f float_fingerprint=true   # on CI, then read the log
```

Identical lines exonerate a primitive; differing lines are a concrete
mechanism. The tool checks primitives, not the simulation - matching output
does not prove a benchmark agrees, only that this explanation is not the cause.
