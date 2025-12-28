# Decision Log

## 2025-12-27

### Overflow Energy -> Food
Decision: **Yes**, overflow energy should materialize as food after reproduction banking.
Evidence: `core/config/fish.py` documents banking overflow energy and dropping excess; fish and plant
implement overflow routing to food drops in `core/entities/fish.py` and `core/entities/plant.py`.

### Multiple Tanks Concurrently
Decision: **Yes**, the backend is designed to run multiple tanks concurrently.
Evidence: `backend/tank_registry.py` manages multiple `SimulationManager` instances; each runner
builds its own `TankWorld` in `backend/simulation_runner.py`.

### Hybrid Model Direction
Decision: **Yes**, the architecture is intentionally hybrid (entity-driven + system-driven).
Evidence: `core/simulation/system_registry.py` explicitly describes the hybrid paradigm, and
`docs/ARCHITECTURE.md` documents entity updates plus cross-entity systems.
