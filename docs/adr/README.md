# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) documenting significant
architectural choices made during development.

> **Historical note:** ADRs are point-in-time records and are not updated after
> acceptance. Verification notes in older ADRs may cite `fast_gate` — the
> pre-rename name for [`tools/pre_pr_gate.py`](../../tools/pre_pr_gate.py). For the
> current validation tier names and commands, see [CLAUDE.md](../../CLAUDE.md) or
> [AGENTS.md](../../AGENTS.md), not historical ADR text.

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-001](001-systems-architecture.md) | Systems Architecture | Accepted | 2024-12 |
| [ADR-002](002-protocol-based-design.md) | Protocol-Based Design | Accepted | 2024-12 |
| [ADR-003](003-phase-based-execution.md) | Phase-Based Execution | Accepted | 2024-12 |
| [ADR-004](004-component-composition.md) | Component Composition | Accepted | 2024-12 |
| [ADR-005](005-energy-state-pattern.md) | Energy State Pattern | Accepted | 2024-12 |
| [ADR-006](006-deprecate-monolithic-food-seekers.md) | Deprecate Monolithic Food-Seekers | Accepted | 2026-06 |
| [ADR-007](007-error-handling-strategy.md) | Error Handling Strategy | Accepted | 2026-06 |
| [ADR-008](008-acyclic-core-imports.md) | Acyclic Core Module Graph | Accepted | 2026-06 |
| [ADR-009](009-generic-agent-model-reconciliation.md) | Reconcile the GenericAgent Component Model | Accepted | 2026-06 |
| [ADR-010](010-movement-arbitration.md) | Unify Movement Drive Arbitration | Accepted | 2026-06 |
| [ADR-011](011-minigames-out-of-core.md) | Keep Minigames Out of the Generic Core | Accepted | 2026-06 |
| [ADR-012](012-hash-seed-determinism.md) | Cross-Process Determinism (Hash-Seed Independence) | Accepted | 2026-06 |
| [ADR-013](013-collapse-generic-agent-state-layer.md) | Collapse the GenericAgent State Layer | Accepted | 2026-06 |
| [ADR-014](014-deterministic-algorithm-ids.md) | Deterministic Algorithm / Diversity IDs | Accepted | 2026-06 |
| [ADR-015](015-per-algorithm-stats-keying.md) | Per-Algorithm Stats Keyed by Composable behavior_id | Accepted | 2026-06 |

## What is an ADR?

An Architecture Decision Record captures:
- **Context**: The situation and forces at play
- **Decision**: What we decided to do
- **Consequences**: The results of the decision (positive and negative)

## Template

```markdown
# ADR-XXX: Title

## Status
Proposed | Accepted | Deprecated | Superseded

## Context
What is the issue that we're seeing that is motivating this decision?

## Decision
What is the change that we're proposing?

## Consequences
What becomes easier or more difficult because of this change?
```
