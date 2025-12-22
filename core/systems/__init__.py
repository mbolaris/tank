"""Simulation systems package.

This package contains all systems that operate on the simulation.
Each system has a single responsibility and follows the BaseSystem contract.

Systems vs Components
=====================
- **Components** store data and state (e.g., EnergyComponent stores energy)
- **Systems** contain logic and operate on entities (e.g., CollisionSystem detects collisions)

This separation follows the Entity-Component-System (ECS) pattern, allowing:
- Independent testing of logic (systems) and state (components)
- Easy addition of new behaviors without modifying entities
- Clear data flow: Systems read/write Components, emit Events


System Execution Order
======================
Systems execute in phases, ensuring predictable behavior. The simulation
processes one complete frame in this order:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRAME START                                       │
│  Reset per-frame counters, prepare caches                                   │
│  └── (Internal engine setup - no explicit system)                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TIME UPDATE                                        │
│  Advance simulation clock, update day/night cycle                           │
│  └── TimeSystem: Updates time_of_day, detection modifiers, activity levels │
│                                                                             │
│  After this phase:                                                          │
│    - time_of_day is current (0.0=midnight, 0.5=noon)                       │
│    - Detection range modifiers reflect lighting conditions                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ENVIRONMENT                                        │
│  Update spatial grid, environmental factors                                 │
│  └── SpatialGrid rebuild (if entities moved significantly)                  │
│  └── Environment modifiers (future: temperature, currents)                  │
│                                                                             │
│  After this phase:                                                          │
│    - Spatial queries (nearby_evolving_agents, nearby_resources) are accurate               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ENTITY THINK                                       │
│  AI decision-making: fish choose their next action                          │
│  └── BehaviorSystem: Each fish's algorithm decides movement direction      │
│                                                                             │
│  Fish use spatial queries to:                                               │
│    - Find nearest food (affected by detection modifiers)                   │
│    - Detect predators (crabs)                                              │
│    - Locate potential mates                                                 │
│    - Sense nearby schoolmates                                               │
│                                                                             │
│  After this phase:                                                          │
│    - Each fish has a desired velocity vector                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ENTITY ACT                                         │
│  Execute decided actions: movement, energy consumption                      │
│  └── MovementSystem: Apply velocity, handle boundary collisions            │
│  └── EnergySystem: Deduct movement costs based on speed and turning        │
│                                                                             │
│  After this phase:                                                          │
│    - Entity positions are updated                                           │
│    - Energy has been consumed for movement                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           COLLISION                                          │
│  Detect and resolve entity overlaps                                         │
│  └── CollisionSystem: Fish-Food (eating), Fish-Crab (damage)               │
│                                                                             │
│  Collision types:                                                           │
│    - Fish + Food → Fish gains energy, Food removed                         │
│    - Fish + Crab → Fish takes damage, Crab gains energy                    │
│    - Fish + Fish → No collision (pass through)                             │
│                                                                             │
│  After this phase:                                                          │
│    - Eaten food is marked for removal                                       │
│    - Damaged fish have reduced energy                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INTERACTION                                        │
│  Social interactions between entities                                        │
│  └── PokerSystem: Nearby fish play poker for energy stakes                 │
│  └── (Future: CommunicationSystem, TerritorySystem)                        │
│                                                                             │
│  Poker triggers when fish are within FISH_POKER_MAX_DISTANCE.              │
│  Winners gain energy, losers lose energy, house takes a cut.               │
│                                                                             │
│  After this phase:                                                          │
│    - Poker results recorded                                                 │
│    - Energy transferred between players                                     │
│    - Post-poker reproduction may be initiated                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           REPRODUCTION                                       │
│  Handle mating and offspring creation                                        │
│  └── ReproductionSystem: Check pregnancy timers, create offspring          │
│                                                                             │
│  Reproduction requires:                                                      │
│    - Sufficient energy (REPRODUCTION_MIN_ENERGY)                            │
│    - Cooldown expired (REPRODUCTION_COOLDOWN frames)                        │
│    - For sexual: nearby compatible mate                                     │
│                                                                             │
│  After this phase:                                                          │
│    - New fish may be spawned                                                │
│    - Parent energy reduced                                                  │
│    - Birth events emitted                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LIFECYCLE                                          │
│  Process deaths, age transitions, state changes                             │
│  └── LifecycleSystem: Check starvation, old age, life stage transitions    │
│                                                                             │
│  Death causes:                                                               │
│    - Starvation (energy < STARVATION_THRESHOLD)                             │
│    - Old age (exceeded genetic max_age)                                     │
│    - Predation (crab attack)                                                │
│                                                                             │
│  Life stages: Baby → Juvenile → Young Adult → Adult → Mature → Elder       │
│                                                                             │
│  After this phase:                                                          │
│    - Dead entities marked for removal                                       │
│    - Life stage transitions applied                                         │
│    - Death events emitted                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SPAWN                                              │
│  Create new entities to maintain ecosystem health                           │
│  └── FoodSpawningSystem: Spawn food based on ecosystem energy levels       │
│  └── EmergencySpawnSystem: Spawn fish if population critically low         │
│  └── PlantSystem: Handle plant growth and nectar production                │
│                                                                             │
│  Spawn rates adapt to ecosystem state:                                      │
│    - Low total energy → increased food spawning                            │
│    - Low population → emergency fish spawning                              │
│    - High population → reduced spawning                                     │
│                                                                             │
│  After this phase:                                                          │
│    - New food/entities added to simulation                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLEANUP                                            │
│  Remove dead entities, return resources to pools                            │
│  └── EntityCleanupSystem: Remove entities marked for deletion              │
│                                                                             │
│  After this phase:                                                          │
│    - Dead entities removed from entities list                               │
│    - Spatial grid updated                                                   │
│    - Memory reclaimed                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRAME END                                          │
│  Statistics, snapshots, state serialization                                 │
│  └── StatsSystem: Update rolling statistics                                 │
│  └── (Backend: Serialize state for WebSocket broadcast)                    │
│                                                                             │
│  After this phase:                                                          │
│    - Frame counter incremented                                              │
│    - Statistics updated                                                     │
│    - Frame ready for rendering                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

Why This Order Matters
----------------------
1. **TIME before ENVIRONMENT**: Time affects detection modifiers used in spatial queries.
2. **THINK before ACT**: Fish decide direction before moving.
3. **ACT before COLLISION**: Positions must be updated before checking overlaps.
4. **COLLISION before INTERACTION**: Eating happens before poker (can't play if just died).
5. **LIFECYCLE before SPAWN**: Count deaths before deciding if emergency spawn needed.
6. **CLEANUP last**: Don't remove entities that other systems might reference.


Available Systems
-----------------
- `FoodSpawningSystem`: Handles automatic food spawning based on ecosystem needs
- `CollisionSystem`: (in collision_system.py) Handles collision detection and response
- `PokerSystem`: (in poker_system.py) Manages poker game initiation and resolution
- `ReproductionSystem`: (in reproduction_system.py) Handles mating and offspring creation
- `TimeSystem`: (in time_system.py) Manages day/night cycle and time-based modifiers


Future Systems to Extract from SimulationEngine
-----------------------------------------------
- `EmergencySpawnSystem`: Handle emergency fish spawning when population is critical
- `PlantPropagationSystem`: Handle plant reproduction and sprouting
- `EntityCleanupSystem`: Handle removing dead/expired entities
- `BehaviorSystem`: Run fish behavior algorithms (currently inline in SimulationEngine)
- `MovementSystem`: Apply movement and boundary handling (currently in Fish.update)


Usage
-----
```python
from core.systems import BaseSystem, System

class MySystem(BaseSystem):
    def _do_update(self, frame: int) -> None:
        # System logic here
        pass
```

See Also
--------
- `core/update_phases.py`: Phase enum definitions and PhaseRunner
- `core/systems/base.py`: BaseSystem abstract class and SystemResult
"""

from core.systems.base import BaseSystem, System, SystemResult
from core.systems.food_spawning import FoodSpawningSystem, SpawnRateConfig

__all__ = ["BaseSystem", "System", "SystemResult", "FoodSpawningSystem", "SpawnRateConfig"]
