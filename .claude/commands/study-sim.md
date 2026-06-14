---
description: Study the running simulation's evolution health and recommend (or implement) improvements
argument-hint: "[url | probe | stats <file> | history <file>] [improve]"
---

You are helping the user study a Tank World simulation that is (usually) running
right now, and answer: **how well are the fish evolving, and what should we change
to improve it?** The end goal is improving evolution on a long-running sim (days+).

Arguments (optional): `$ARGUMENTS`
- A URL (e.g. `http://127.0.0.1:8000`) selects a live server. Default when no
  source is given: `http://127.0.0.1:8000`.
- `probe` runs a fresh deterministic probe instead of attaching to a server.
- `stats <file>` analyses an exported stats JSON; `history <file>` analyses a
  metrics-history payload or watch-journal (JSONL).
- `improve` (may be combined with a source) means: don't stop at the report -
  carry the top recommendation through to an implemented, validated change.

## 1. Assess (always do this first)

Run the read-only report tool with structured output and read its JSON:

```bash
python tools/evolution_report.py --url http://127.0.0.1:8000 --json
```

(Substitute `--probe`, `--stats <file>`, or `--history <file>` per the arguments.)
If a live server was requested but is unreachable, say so and offer to run
`--probe` instead rather than silently switching.

Then give the user a **concise** assessment, not a raw dump:
- the overall **verdict** and the per-axis grades;
- the **trait-drift** highlights - call out which traits are under directional
  selection (>=5%) vs flat. Flat traits despite generation turnover = churn
  without selection (the thing we most want to fix);
- the top 1-3 **recommendations**, each with the file to change and the
  diagnostic that confirms it.

Reference `AGENTS.md` -> "Studying a Running Simulation" and the "Healthy
Ecosystem Indicators" table for what the numbers mean. For a multi-day run,
suggest leaving a watch-journal running so the long-horizon trend survives the
in-memory buffer wrap (`--watch --interval 300 --journal evolution_journal.jsonl`).

## 2. Improve (only when the user asks, or `improve` was passed)

Drive the top-ranked recommendation through the **Evolution Loop** - never
hand-wave a fix:

1. Reproduce the problem with the diagnostic the report named
   (e.g. `scripts/diagnose_food_seeking.py`, `scripts/diagnose_evolution.py`).
2. Make the **smallest** change. Keep Layer 1 (algorithm/config in `core/`)
   separate from any Layer 2 change (this tool, benchmarks, telemetry, gates).
3. `python tools/smoke_gate.py`, then `python tools/fast_gate.py`.
4. Benchmark the candidate and compare against `champions/`. The
   evolution-quality benchmark is `benchmarks/tank/ecosystem_health_10k.py`;
   confirm trait drift actually moved with `scripts/diagnose_evolution.py`.
   ecosystem_health is trajectory-sensitive on one seed - verify on a couple of
   extra seeds (e.g. 7, 123) before trusting a win.
5. Only claim an improvement with a reproduction command, seed, score, and
   metadata. Commit on a feature branch with that evidence in the message, then
   open a PR.

## Guardrails

- The report tool is read-only; it never perturbs the running sim. Keep it that way.
- Determinism is non-negotiable - benchmarks use fixed seeds.
- Do not claim a benchmark improvement without reproduction evidence.
- If a recommendation is ambiguous or would require a large refactor, summarize
  the options and ask the user before implementing.
