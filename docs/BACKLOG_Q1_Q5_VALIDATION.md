# Q1–Q5 validation record

Validated on Windows with Python 3.14.3 in the repository's `.venv`.
The Windows `python` launcher resolved to a Store alias; commands below use the
actual environment interpreter. All commands run from the repository root
except Playwright, which runs from `frontend`.

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe tools/smoke_gate.py` | PASS: lint, formatting, 101 smoke tests |
| `.\.venv\Scripts\python.exe tools/agent_gate.py` | PASS: smoke, mypy across 569 source files, 596 curated tests |
| `.\.venv\Scripts\python.exe tools/pre_pr_gate.py` | PASS: all five broad non-slow shards; three intentional skips |
| `npm --prefix frontend test -- --run` | PASS: 69 files, 537 tests |
| `npm --prefix frontend run build` | PASS |
| `npm --prefix frontend run lint` | PASS |
| `npx playwright test e2e/activity-isolation.spec.ts e2e/pause-pending.spec.ts e2e/pause-state.spec.ts` | PASS: all three browser scenarios, including a real two-client backend path |
| `npx playwright test e2e/pause-state.spec.ts --repeat-each=3` | PASS: three repeated two-client scenarios |
| `.\.venv\Scripts\python.exe -m pytest tests/core/test_transfer_report_freshness.py tests/test_study_provenance.py -q` | PASS: 13 tests |
| `.\.venv\Scripts\python.exe tools/check_transfer_report.py` | PASS: unchanged v4 source JSON, fresh negative report |
| `.\.venv\Scripts\python.exe tools/check_transfer_report.py research/target_memory_transfer/selection_replication.json` | PASS: retained rows and registered inconclusive headline agree |
| `.\.venv\Scripts\python.exe -m pre_commit run` | PASS: all applicable hooks on staged PR files |
| `git diff --check` and `git diff --cached --check` | PASS |

The Q5 experiment command, seeds, budget, scores, provenance and limitations are
in the [replication analysis](../research/target_memory_transfer/selection_replication_analysis.md).
No champion reproduction or ecosystem improvement claim applies: this PR changes
observer tooling, persistence/measurement contracts and research reporting,
without changing behavior algorithms or champion files.

During development, the broad gate exposed obsolete pause return assertions,
the central frontend type-file size ratchet and mocked identity serialization;
these were fixed before the passing run. The real two-client browser check also
exposed same-frame pause broadcasts being suppressed; a deterministic backend
regression test and repeated browser checks cover that fix.

`pre_commit run --all-files` found pre-existing whitespace/import-order failures
outside this PR. Its unrelated automatic edits were reverted. The staged-file
run above passes; the baseline-wide cleanup is outside Q1–Q5.

## PR #971 reconnect regression follow-up

The initial CI browser run found that disconnect handling cleared the last
received WebSocket frame. That conflicted with Soccer Arena's reconnect contract,
which keeps the pitch visible with a stale label while the socket retries. The
hook now retains the frame during a same-world reconnect; switching worlds still
clears state. Validation after this fix:

| Command | Result |
|---|---|
| From `frontend`: `npx playwright test e2e/soccer-arena.spec.ts --reporter=line` | PASS: complete real-backend arena and reconnect scenario |
| From `frontend`: `npm test -- --run` | PASS: 69 files, 537 tests |
| From `frontend`: `npm run lint` | PASS |
