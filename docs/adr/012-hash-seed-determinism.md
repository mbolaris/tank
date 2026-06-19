# ADR-012: Cross-Process Determinism (Hash-Seed Independence)

## Status

Accepted (2026-06)

## Context

Determinism is "non-negotiable" (`CLAUDE.md`): a benchmark at a fixed seed must
reproduce exactly. It did not — *across processes*.

The same code at the same seed produced different scores in separate Python
processes:

```
ecosystem_health_10k, seed 42, identical code:
  process A: 4.675340
  process B: 4.791812
```

With `PYTHONHASHSEED` pinned the score was stable and reproducible; unset (the
default), it varied run to run. The in-process determinism check
(`run_bench --verify-determinism`, two runs in one interpreter) passed, which is
exactly why this hid for so long — it never crossed a process boundary.

**This was the real reason the champions did not reproduce.** A champion
recorded in one process (one hash seed) failed `verify_all_champions` in another
(`ecosystem_health_10k` champion 5.70 vs ~4.68–4.79 on reproduction). It looked
like a stale-champion bookkeeping problem; it was a determinism bug.

### Root cause

Python randomizes `hash(str)` per process unless `PYTHONHASHSEED` is fixed.
Several genome **code-policy** inheritance/mutation paths iterated
string-keyed collections **and consumed RNG per key** in that hash-dependent
order:

- `code_policy_traits.py` — `mutate_policy_params` over `params.items()`
  (`rng.random()` / `rng.gauss()` per key)
- `policy_inheritance.py` — `mutate_code_policy_params` over `dict(params)`
- the parameter-blend unions `set(p1) | set(p2)` in `code_policy_traits.py` and
  `genome_code_pool.py`, which baked a hash-ordered key sequence into the
  offspring genome that later mutation then walked

Because the *order* of RNG draws determined the offspring, hash order →
RNG sequence → divergent trajectory. The paths activate only once code
policies proliferate through several generations, so short runs (≤1500 frames)
agreed and the divergence only emerged deep into a 10k-frame run.

`ComposableBehavior.mutate` already iterated with `sorted(...)` for exactly this
reason — these sibling paths simply missed the same guard.

> **Principle:** any RNG-consuming iteration over a `set` or `dict` must use a
> stable order (sort the keys). Hash order is not a stable order — it is
> per-process random for strings. In-process reproduction is necessary but not
> sufficient; the determinism contract is cross-process.

## Decision

Sort the keys at every RNG-consuming iteration over a string-keyed collection in
the genome code-policy paths (and at the blend unions that feed them, so genome
param dicts are canonically ordered):

```python
for key in sorted(mutated):                  # policy_inheritance.py
for key, value in sorted(params.items()):    # code_policy_traits.py
for key in sorted(all_keys):                 # code_policy_traits.py, genome_code_pool.py
```

## Consequences

**Positive**
- The simulation reproduces across processes: `ecosystem_health_10k` seed 42
  now yields `4.791812` under `PYTHONHASHSEED` 0/7/999/12345 (verified);
  `survival_5k` likewise stable.
- Champions become genuinely reproducible, so `verify_all_champions` /
  `validate_reproduction` are meaningful again.
- Removes a class of CI flakiness whose cause would have been near-impossible to
  guess from the symptom.

**Negative**
- The fix changes the RNG draw order, so the single canonical trajectory differs
  from any one prior hash-seeded run. **Champions must be re-baselined** under
  the fixed behavior (done as a separate, isolated Layer-2 step — ADR notes it
  here, the re-baseline commit records the evidence).

**Follow-up**
- Consider a CI guard that runs a benchmark under two different
  `PYTHONHASHSEED` values and asserts identical output, so a future
  hash-order regression fails loudly instead of silently.

## Related
- [ADR-003: Phase-Based Execution](003-phase-based-execution.md) (determinism contract)
- [ADR-010: Unify Movement Drive Arbitration](010-movement-arbitration.md)
  (in-process determinism care; this ADR is the cross-process complement)
