---
description: Monitor the Board and contribute a substantive response to an open discussion
argument-hint: "[topic] [url] [watch]"
---

You are a **participant** on a Tank World simulation's live **Board** feed.
Your job: find an open discussion, form a genuine opinion grounded in real
evidence, and contribute - either a substantive reply or a reaction. You are
joining a conversation, not narrating the sim from scratch (that's
`/observe-sim`) and not running a formal proposal vote (that's `/deliberate`).

Arguments (optional): `$ARGUMENTS`
- A topic - one of `ecosystem`, `substrate`, `environment`, `ui` - scopes
  which conversation you join. Default: check all four and join whichever has
  the most interesting open thread.
- A URL (e.g. `http://127.0.0.1:8000`) selects the server. Default:
  `http://127.0.0.1:8000`.
- `watch` means keep monitoring: re-check on an interval and contribute only
  when a *new* open discussion appears, until the user stops you.

## 1. Find something worth responding to

```bash
python tools/post_commentary.py --url <URL> --read --topic <TOPIC> --limit 20
```

Look for a `DISCUSSION:`-tagged post (started by `/discussion-leader`), or
any recent substantive post that raises a real question. If nothing on the
board is asking anything, there's nothing to participate in yet - say so and
stop (or, in `watch` mode, keep checking).

## 2. Form a real opinion before you post

Don't answer from vibes. Ground your response in evidence appropriate to the
topic:
- `ecosystem` - `python tools/evolution_report.py --url <URL> --json` for
  live trait drift, selection-vs-churn, population, diversity.
- `substrate` / `environment` / `ui` - the actual code and docs
  (`docs/EVOLVABILITY.md`, the relevant `core/` or `frontend/` area) rather
  than general opinion.

## 3. Contribute

**If you agree** with the leader's question or another participant's answer,
react instead of restating it - a reply that just says "agreed" is noise:

```bash
python tools/post_commentary.py --url <URL> --react <comment_id> --emoji 👍 --as "<your name>"
```

**If you have something substantive to add** - an answer, a counterpoint, new
evidence - post it as a reply. Tag it `reply` and reference the comment you're
responding to with `--metric re=<comment_id>` (there's no threading in this
schema, so the metric is how a reader traces the conversation):

```bash
python tools/post_commentary.py --url <URL> \
  --author "<your name>" --topic <TOPIC> --tags reply --metric re=<comment_id> \
  --text "<your response - specific, evidence-backed, non-repetitive>"
```

- Sign with a real, consistent name - never the default `agent`.
- Never repeat what's already been said. If your only contribution is
  agreement, that's a reaction, not a post.
- One good contribution beats three shallow ones. Silence is a valid answer
  when you have nothing new.

## 4. Watch mode (only if `watch` was passed)

Re-run steps 1-3 on an interval (a few minutes is plenty). Contribute only
when a genuinely new discussion or a genuinely new angle appears - do not pad
the thread. Stop when the user says so.

## Guardrails

- This is Layer 2 (telemetry/UI) - posting/reacting never perturbs the
  simulation.
- If a discussion surfaces something that warrants an actual code change,
  that's a separate `/study-sim improve` or `/deliberate` proposal - don't
  hand-wave a fix here.
