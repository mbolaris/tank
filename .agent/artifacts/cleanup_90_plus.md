# Path to 90+: Architecture Cleanup Plan

**Score**: 84/100 → Target: 90+
**Created**: 2024-12-24
**Based on**: External code review of ~74k LOC Python across 333 .py files

---

## Executive Summary

The codebase received strong marks for:
- ✅ Real architecture with clear separation of concerns
- ✅ SimulationConfig + nested dataclasses for reproducibility
- ✅ 1k+ tests testing invariants and behavior
- ✅ Honest documentation of nondeterminism (xfail tests)
- ✅ Distributed/network architecture exists and is organized

The gaps preventing 90+ are **operational cleanliness** and **complexity management**:
1. Backend packaging requires `sys.path` surgery
2. Import-time side effects in `backend/main.py`
3. Top 3 large modules are risk multipliers
4. Determinism still not achieved
5. CI runs tests but linting/typing is optional

---

## Priority 1: Backend Packaging (No sys.path Surgery)

### Current State
```python
# backend/main.py line 21-22
sys.path.insert(0, str(Path(__file__).parent.parent))
```

This breaks:
- `pip install -e .`
- Clean entrypoints
- Tooling that expects proper package structure

### Target State
- `backend` as a proper package in `pyproject.toml`
- Clean imports like `from core.config.simulation_config import SimulationConfig`
- No `sys.path` manipulation

### Implementation Steps

#### 1.1 Add `backend/__init__.py` if missing
Check if `backend/__init__.py` exists and contains minimal content.

#### 1.2 Update `pyproject.toml` packages
```toml
[tool.setuptools]
packages = ["core", "backend"]
```

#### 1.3 Remove `sys.path.insert` from `backend/main.py`
Delete lines 21-22 and verify imports still work.

#### 1.4 Verify with `pip install -e .` fresh install
```bash
python -m pip install -e .
python -c "from backend.main import app; print('OK')"
```

---

## Priority 2: Kill Import-Time Side Effects

### Current State
`backend/main.py` initializes at import time:
- Lines 54-66: Global singletons (`tank_registry`, `connection_manager`, `discovery_service`, `server_client`)
- Lines 33-34: Logging configuration
- Lines 37-52: Windows event loop policy
- Lines 68-70, 72-76: More imports that run code

### Target State
- **App factory pattern**: `create_app()` function
- All initialization happens inside `lifespan()` or factory
- Module import is side-effect free

### Implementation Steps

#### 2.1 Create `backend/app_factory.py`
Move app creation logic to a factory function:
```python
def create_app(
    server_id: str | None = None,
    discovery_server_url: str | None = None,
) -> FastAPI:
    # Configure logging
    logger = configure_logging(extra_loggers=("backend",))

    # Create singletons
    tank_registry = TankRegistry(create_default=False)
    connection_manager = ConnectionManager()
    discovery_service = DiscoveryService()
    server_client = ServerClient()

    # Create app with lifespan
    app = FastAPI(...)

    return app
```

#### 2.2 Refactor `backend/main.py`
```python
# backend/main.py - becomes thin entrypoint
from backend.app_factory import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### 2.3 Update tests to use factory
Tests can now create isolated app instances:
```python
def test_something():
    app = create_app(server_id="test-server")
    # Test without cross-test leakage
```

---

## Priority 3: Split Top 3 Large Modules

### Current State
| Module | Lines | Concern |
|--------|-------|---------|
| `core/mixed_poker/interaction.py` | ~960 | Too many responsibilities |
| `core/simulation/engine.py` | ~918 | Orchestration + some logic |
| `core/algorithms/composable.py` | ~877 | All behaviors in one file |

### Target State
Split each into 3-5 focused files, not 50 tiny ones.

### Implementation Steps

#### 3.1 Split `core/mixed_poker/interaction.py`
```
core/mixed_poker/
├── __init__.py          # Re-exports for backward compat
├── types.py             # Already exists
├── state.py             # Already exists
├── interaction.py       # Core interaction logic (~200 lines)
├── betting_round.py     # _play_betting_round (~150 lines)
├── showdown.py          # Showdown logic (~150 lines)
├── player_actions.py    # _decide_player_action, helpers (~200 lines)
└── effects.py           # Visual effects, logging (~100 lines)
```

#### 3.2 Split `core/simulation/engine.py`
Already well-separated with systems. Focus on:
```
core/simulation/
├── __init__.py
├── engine.py            # Core orchestration (~400 lines)
├── entity_spawning.py   # Emergency spawn, initial entities (~150 lines)
├── serialization.py     # Snapshot/restore (~150 lines)
└── diagnostics.py       # Debug, phase tracking (~100 lines)
```

#### 3.3 Split `core/algorithms/composable.py`
```
core/algorithms/
├── __init__.py
├── composable.py        # Main ComposableBehavior class (~200 lines)
├── behaviors/
│   ├── __init__.py
│   ├── threat_response.py  # _execute_threat_response (~100 lines)
│   ├── food_approach.py    # _execute_food_approach (~150 lines)
│   ├── social_mode.py      # _execute_social_mode (~100 lines)
│   └── poker_engagement.py # _execute_poker_engagement (~50 lines)
└── boids.py             # _boids_behavior, flocking logic
```

---

## Priority 4: Thread RNG Everywhere

### Current State
- ~50+ files in `core/` still have `import random`
- Many use `random.random()` directly instead of `world.rng`
- `test_determinism.py` and `test_parity.py` are marked `@pytest.mark.xfail`

### Target State
- All randomness flows through `world.rng` or explicit RNG parameter
- `test_determinism.py` passes (remove xfail)
- Research reproducibility achieved

### Implementation Steps

#### 4.1 Audit remaining global random usage
Find all files with `import random` that aren't using it correctly:
```bash
grep -r "random\." core/ | grep -v "rng\." | grep -v "random.Random"
```

#### 4.2 Fix remaining modules systematically
Priority files (from grep search):
- `core/algorithms/composable.py`
- `core/poker/betting/decision.py`
- `core/entities/fish.py`
- `core/movement_strategy.py`
- `core/environment.py`

Pattern to apply:
```python
# Before
import random
def foo():
    return random.random()

# After
def foo(rng: random.Random):
    return rng.random()
```

#### 4.3 Remove xfail from determinism tests
Once all modules are fixed, update:
- `tests/test_determinism.py` - remove `@pytest.mark.xfail`
- `tests/test_parity.py` - remove `@pytest.mark.xfail`

---

## Priority 5: Strengthen CI

### Current State
- CI runs tests ✅
- Formatting/linting has `continue-on-error: true` ⚠️
- mypy excludes `backend/` entirely ⚠️

### Target State
- All checks are non-optional (fail the build)
- mypy covers backend too
- Quick feedback loop

### Implementation Steps

#### 5.1 Remove `continue-on-error` from CI
```yaml
# .github/workflows/ci.yml
- name: Check code formatting with black
  run: |
    black --check core/ tests/ *.py --exclude="frontend|node_modules|.venv|venv"
  # Remove: continue-on-error: true

- name: Lint with ruff
  run: |
    ruff check core/ tests/ *.py
  # Remove: continue-on-error: true
```

#### 5.2 Include backend in mypy
```toml
# pyproject.toml
[tool.mypy]
exclude = [
    "frontend/",
    # Remove: "backend/",
    ".venv/",
    "venv/",
]
```

#### 5.3 Fix any resulting type errors
Add type hints to backend modules as needed.

---

## Implementation Order

Recommended sequence (each can be committed independently):

| Phase | Task | Effort | Impact |
|-------|------|--------|--------|
| 1 | Backend proper package | 1-2 hours | High |
| 2 | Kill import-time side effects | 2-4 hours | High |
| 3A | Split mixed_poker/interaction.py | 2-3 hours | Medium |
| 3B | Split simulation/engine.py | 1-2 hours | Medium |
| 3C | Split algorithms/composable.py | 2-3 hours | Medium |
| 4 | Thread RNG everywhere | 3-4 hours | High |
| 5 | Strengthen CI | 1-2 hours | Medium |

**Total estimated effort**: 12-20 hours

---

## Success Criteria

After completing all phases:

1. ✅ `pip install -e .` works cleanly
2. ✅ `python -c "import backend.main"` has no side effects
3. ✅ No single file in `core/` exceeds ~500 lines
4. ✅ `pytest tests/test_determinism.py` passes (no xfail)
5. ✅ CI fails on formatting/linting/typing violations
6. ✅ External re-review scores 90+

---

## Which Phase Should We Start With?

I recommend starting with **Priority 1 (Backend Packaging)** because:
1. It's the quickest win
2. Unblocks proper testing of other changes
3. Most visible improvement for "operational cleanliness"

Ready to begin?
