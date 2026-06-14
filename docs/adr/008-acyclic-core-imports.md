# ADR-008: Acyclic Core Module Graph

## Status
Accepted (2026-06)

## Context

`core/` has long carried a large number of **in-function imports** used to route
around circular dependencies (tracked as open item #4 in
`docs/ARCHITECTURE_REVIEW.md`). The standing assumption was that the module graph
was deeply tangled and that untangling it would be a large, risky refactor.

A measurement said otherwise. Building the *module-load* import graph for `core/`
— every import that runs when a module is first imported, **excluding**
`if TYPE_CHECKING:` blocks and function-local imports — and running Tarjan's
algorithm over it revealed only **three** cyclic components, every one the same
shape:

- `core.simulation` ⇄ `core.simulation.engine`
- `core.genetics` ⇄ `core.genetics.genome`
- `core.services.stats` ⇄ `core.services.stats.calculator`

Each cycle was a **submodule importing a sibling through its own package
facade** — e.g. `core/simulation/engine.py` doing
`from core.simulation import diagnostics`, which forces a dependency on the
`core/simulation/__init__.py` aggregator that re-exports `engine`. A fourth
instance of the same pattern existed one level up: deep submodules importing a
subpackage via the top-level `core` facade (`from core import entities`), which
`core/__init__.py`'s own design note already advises against.

The graph was therefore *accidentally* near-acyclic, but nothing guarded it.
Crucially, this is self-reinforcing debt: as long as cycles can reappear
silently, contributors keep reaching for in-function imports "to be safe,"
which is exactly what produced the original sprawl.

## Decision

Treat an **acyclic module-load import graph for `core/`** as an enforced
architectural invariant.

1. **Break the existing cycles** by importing siblings/subpackages directly
   instead of through a package facade:
   `import core.simulation.diagnostics as diagnostics`, not
   `from core.simulation import diagnostics`.

2. **Guard it with a fitness test** — `tests/test_import_acyclic.py` builds the
   module-load graph (AST-based, no external dependencies, consistent with
   `tests/test_import_boundaries.py` and `tests/test_god_class_limits.py`) and
   fails with the offending strongly-connected component(s) if a cycle is
   reintroduced.

3. **Scope precisely.** The invariant covers imports that execute at module
   load. Two escape hatches remain legitimate and are intentionally outside the
   graph:
   - `if TYPE_CHECKING:` imports (type-only, never executed at runtime), and
   - **function-local imports**, the explicit, greppable way to express a
     genuinely mutual runtime dependency.

### Rule of thumb

> A module must not import its own package facade. Import the concrete sibling
> or subpackage directly. Reserve `from core.pkg import name` for consumers
> *outside* `core.pkg`.

## Consequences

### Positive
- The dependency structure is a **verified DAG**, so module-load order is
  well-defined and CI catches re-tangling with a precise SCC report.
- The *need* for defensive in-function imports shrinks. With acyclicity
  guaranteed, the remaining ones can be promoted to module scope
  opportunistically and safely — the test proves no cycle is reintroduced.
  This turns open item #4 from a "large, risky refactor" into incremental,
  test-backed cleanup.

### Negative
- A change that introduces a new cross-module cycle must break it before
  merging. In practice this is a one-line fix (import the sibling/leaf
  directly), or — for a true mutual dependency — a deliberate function-local
  import with a comment.

## Implementation notes

- **Reference fixes:** the three facade cycles in `engine.py`, `genome.py`, and
  `calculator.py`, plus the four top-level `from core import <subpackage>`
  facade imports in `entity_manager.py`, `entity_factory.py`, `registry.py`,
  and `ecosystem.py`.
- **The graph models module-load imports only.** Function-local and
  `TYPE_CHECKING` imports are excluded by construction; relative imports
  (`from . import x`) are fully resolved so the graph stays sound.
- **The test is necessary, not sufficient.** The graph captures *static*
  module-load imports; it does not trace functions that execute *at* import
  time (e.g. `core/worlds/registry.py` eagerly self-registers built-in modes at
  module load, so its function-local backend imports run eagerly and reach back
  into `core.simulation`). Such a path can form a real runtime cycle the static
  graph cannot see. Therefore promoting a deferred import to module scope must
  be validated by actually importing the module and running the suite -- not by
  the acyclicity test alone.

## Related
- ADR-002: Protocol-Based Design (loose coupling reduces the pressure toward cycles)
- ADR-003: Phase-Based Execution
- `tests/test_import_acyclic.py` — the enforcing fitness test
- `tests/test_import_boundaries.py` — sibling layering guards (core ⊥ backend/frontend)
- `docs/ARCHITECTURE_REVIEW.md` — open item #4 (in-function import debt)
