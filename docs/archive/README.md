# Documentation Archive

This folder holds historical documentation kept for reference only. **Nothing
here is authoritative.** Snapshots, completed-task summaries, and superseded
analyses live here so the active `docs/` tree stays focused on what's current.

## Retention & deprecation policy

1. **Active docs never link to archived docs as if current.** If an active doc
   needs to reference history, it links here with explicit "(archived)" wording.
2. **Archived docs are not maintained.** They reflect the state of the project at
   the time they were written and may contradict current code. Treat any command
   or file path in them as potentially stale.
3. **Date-stamped batches.** Bulk cleanups go into a dated subfolder (e.g.
   `2025-12-cleanup/`) so the archival date is obvious.
4. **Prefer archiving over deleting.** History is cheap and occasionally useful
   for understanding *why* a decision was made. Delete only true duplicates.
5. **When superseding a doc**, add a one-line banner at the top of the archived
   copy pointing to its current replacement, e.g.
   `> Archived YYYY-MM. Superseded by [docs/ARCHITECTURE.md](../ARCHITECTURE.md).`

## What's here

- Base folder: completed implementation/integration summaries and one-off
  analyses (code quality, structure, evolution improvements).
- `2025-12-cleanup/`: a December 2025 documentation consolidation — earlier
  drafts of the architecture, AI workflow, and roadmap docs.

For the live documentation map, see [../INDEX.md](../INDEX.md).
