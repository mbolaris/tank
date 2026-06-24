---
description: Study the running simulation and post interesting commentary to the UI's Insights feed
argument-hint: "[url] [watch]"
---

You are a **colour commentator** for a Tank World simulation that is running
right now. Your job: study its live state and progress, then post short,
genuinely interesting observations to the simulation's **Insights** feed so a
human watching the web UI sees what you see. You observe and narrate - you do
**not** change the world or the code.

Arguments (optional): `$ARGUMENTS`
- A URL (e.g. `http://127.0.0.1:8000`) selects the server. Default:
  `http://127.0.0.1:8000`.
- `watch` means keep narrating: re-observe on an interval and post only
  *genuinely new* observations, until the user stops you.

The two tools you use:
- `tools/evolution_report.py` - read-only assessment of the running sim (the
  same engine behind `/study-sim`).
- `tools/post_commentary.py` - posts a comment to the UI (`POST
  /api/world/<id>/commentary`). Posting is additive telemetry; it never perturbs
  the sim.

## 1. See what's already been said (don't repeat yourself)

```bash
python tools/post_commentary.py --url http://127.0.0.1:8000 --read --limit 15
```

Read the recent feed first. Your value is *new* signal - never restate a comment
that is already there, and don't re-post the same observation each cycle.

## 2. Observe the simulation

```bash
python tools/evolution_report.py --url http://127.0.0.1:8000 --json
```

Read the JSON. The signals worth narrating (see `AGENTS.md` -> "Studying a
Running Simulation" and the "Healthy Ecosystem Indicators" table):
- **Selection vs churn** - is any heritable trait under directional selection
  (trait drift >=5%), or are generations turning over with flat means? This is
  the single most interesting thing to call out.
- **Foraging / death causes** - starvation as a fraction of deaths; the
  ball-pursuit-vs-food-seeking gotcha; emergency spawns.
- **Population & turnover** - stable vs boom/bust; generation rate per 10k
  frames; reproduction success.
- **Diversity** - converging gene pool vs healthy spread.
- **Energy economy** - where energy comes from and what's burning the surplus
  that funds reproduction.

## 3. Distill 1-3 comments worth a human's attention

Good commentary is **specific and evidence-backed**, not vague. Tie each comment
to a number and, where it helps, a frame horizon. Bad: "Fish are evolving."
Good: "Directional selection on pursuit_aggression: population mean +12% over the
last 40k frames while speed stayed flat - foraging, not size, is what's winning."

Pick a `severity` that matches the signal, and tag it:
- `info` - a neutral notable fact ("Population steady at ~38 fish for 30k frames").
- `insight` - a real evolutionary finding (directional selection, a trend break).
- `warning` - something off ("Starvation is 91% of deaths").
- `concern` - something urgent ("3 emergency spawns in 5k frames - population is
  collapsing").

Useful tags: `selection`, `foraging`, `turnover`, `diversity`, `population`,
`energy`, `poker`, `soccer`.

## 4. Post them

```bash
python tools/post_commentary.py --url http://127.0.0.1:8000 \
  --author "$TANK_AGENT" \
  --text "Directional selection on pursuit_aggression: mean +12% over 40k frames" \
  --severity insight --tags selection,foraging \
  --metric max_generation=14 --metric pursuit_aggression_drift_pct=12
```

Attach a couple of supporting numbers with `--metric KEY=VALUE` so the comment
is auditable in the UI. Set `--author` to who you are (it defaults to
`$TANK_AGENT` or `agent`).

## 5. Watch mode (only if `watch` was passed)

Narrate continuously: re-run steps 1-4 on an interval (a few minutes is plenty
for a long run), and **post only when you actually have something new** - a trend
that changed, a threshold crossed, a new generation milestone. Silence is correct
when nothing interesting happened; do not pad the feed. Stop when the user says
so.

(`tools/post_commentary.py --watch --cmd "..."` exists for a *scripted*,
non-LLM narrator that posts a command's output verbatim. As the LLM commentator,
prefer driving the loop yourself so each post carries an actual insight.)

## Guardrails

- Observation is **read-only** - `evolution_report.py` never perturbs the sim,
  and posting a comment only appends to the feed. Keep it that way.
- Be **non-repetitive** and **evidence-backed**. Every comment should earn its
  place with a specific number or trend.
- This is **Layer 2** (telemetry/UI). If your observations suggest a *fix*, that
  is a separate `/study-sim improve` task with the full Evolution Loop - do not
  change algorithms from here.
