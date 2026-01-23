# Record / Replay (Determinism + Time Travel Debugging)

Tank World includes a minimal record/replay mechanism for deterministic regression reproduction.

## Quickstart

```bash
# Record a run (seed is required)
python main.py --headless --seed 42 --max-frames 500 --record run.replay.jsonl

# Replay and verify fingerprints match
python main.py --headless --replay run.replay.jsonl
```

Mode switching can be recorded too:

```bash
python main.py --headless --seed 42 --max-frames 500 --record run.replay.jsonl --switch 200:petri --switch 400:tank
```

## Replay file format

Replay files are **JSONL** (one JSON object per line).

- Line 1 is a `header` record with `seed`, `initial_mode`, and fingerprint config.
- Subsequent lines are `op` records.

Supported ops:
- `init`: fingerprint of the initial snapshot before stepping.
- `step`: advances the simulation by `n` steps, then fingerprints the resulting snapshot.
- `switch_mode`: performs a mode switch (e.g. `tank` ↔ `petri`) and fingerprints the snapshot after the switch.

## Fingerprints

Fingerprints are computed over a canonicalized snapshot:
- known non-deterministic keys are removed
- dict keys are sorted
- lists of dicts are sorted by canonical JSON
- floats are rounded to a fixed precision (currently `6`) to reduce platform jitter

## Tests

The repo includes a small golden replay fixture used as a determinism regression test:
- `tests/fixtures/replays/tank_petri_seed42_v1.jsonl`
- `tests/test_replay_golden.py`
