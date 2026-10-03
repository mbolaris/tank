# Live skill evidence identity (schema 1)

Foraging samples are completed live-population Observatory evaluations, not
benchmark runs. They reside in the world's `foraging_history` snapshot section,
through the existing atomic world-save lifecycle. The history retains at most
60 fixed-size records. It is durable when the containing world is saved; an
unsaved non-persistent world has no restart guarantee.

Each successful record carries world ID, run ID, evaluator content hash,
effective simulation-config hash, benchmark/rung hash, capture frame, capture
generation, status, and measured population/floor/ceiling scores. Run IDs use
OS randomness independently of the simulation RNG. Reset begins a new ID;
save/reload preserves it. A completion from an earlier run is rejected both
by the evaluation cache and history. Frame plus identity deduplicates samples.
Failed or incomplete evaluations supply no measurement, rather than zero skill.

Compatibility requires all five identity fields to agree in a contiguous
segment, and the evaluator/config to match the running server. Only the most
recent segment supplies a trend; a reset, changed evaluator, configuration or
ruler introduces a break. Evaluator hashes conservatively include production
core, benchmark and Observatory source; any included source change requires
fresh evidence. Frame age and coverage are simulation-frame units, not wall
clock durations. Generation span is context, not a skill metric.

The progress response displays sample count, frame age/coverage, breaks and
unknown/incompatible identity. Old saves without a history section begin with
no evidence; old/malformed history sections show an unknown record count and
no trend. Unknown provenance is never populated from today's checkout. Loading
a saved section twice is idempotent. Benchmark `research/skill_history.jsonl`
retains its separate purpose and is not used for this live series.

Pause/resume uses request-ID correlated WebSocket replies containing `success`
and accepted `paused`. Full state and periodic stats deltas carry `paused` for
other clients and reloads; the UI label follows that authoritative state.
Pending controls disable repeated clicks and clear on world change/disconnect.
Older servers without a pause acknowledgement time out or return an explicit
unacknowledged error; sending alone never changes the label. Legacy replies
without IDs can serve a single pending legacy command, but cannot acknowledge
pause or several outstanding commands. Speed/reset remain separate follow-up
work as prescribed by Q3.
