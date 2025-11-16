# Detailed Architecture Relationships

## COMPLETE FILE DEPENDENCY MAP

```
EXECUTION FLOW (What runs first):
═════════════════════════════════

START
  │
  └─> fishtank.py
      └─> main() [line 549]
          │
          ├─> pygame.init()
          │
          ├─> FishTankSimulator()
          │   └─> __init__() [line 31]
          │       ├─ self.agents = pygame.sprite.Group()
          │       ├─ self.environment = Environment()
          │       ├─ self.ecosystem = EcosystemManager()
          │       ├─ self.time_system = TimeSystem()
          │       └─ self.stats_font = pygame.font.Font()
          │
          └─> game.run() [line 504]
              │
              ├─> setup_game() [line 46]
              │   ├─ pygame.display.set_mode()
              │   ├─ environment.Environment(self.agents)
              │   ├─ EcosystemManager(max_population=100)
              │   └─ create_initial_agents()
              │       │
              │       ├─ Create Solo Fish
              │       │   └─> agents.Fish(..., SoloFishMovement())
              │       │
              │       ├─ Create Algorithmic Fish (2)
              │       │   ├─> genome = Genome(use_brain=False, use_algorithm=True)
              │       │   │   ├─> Brain = None
              │       │   │   └─> algorithm = get_random_algorithm()
              │       │   │       └─> core/algorithms/*.py (48 choices)
              │       │   └─> agents.Fish(..., AlgorithmicMovement(), genome)
              │       │
              │       ├─ Create Neural Fish (2)
              │       │   ├─> genome = Genome(use_brain=True, use_algorithm=False)
              │       │   │   ├─> NeuralBrain.random()
              │       │   │   │   ├─ core/neural_brain.py
              │       │   │   │   └─ 2-layer neural network
              │       │   │   └─> algorithm = None
              │       │   └─> agents.Fish(..., NeuralMovement(), genome)
              │       │
              │       ├─ Create Schooling Fish (2)
              │       │   └─> agents.Fish(..., SchoolingFishMovement())
              │       │
              │       ├─ Create Plants (3)
              │       │   └─> agents.Plant(environment)
              │       │
              │       ├─ Create Crab
              │       │   └─> agents.Crab(environment)
              │       │
              │       └─ Create Castle
              │           └─> agents.Castle(environment)
              │
              └─> MAIN LOOP (while handle_events()) [line 532]
                  │
                  ├─> self.update() [line 533]
                  │   │
                  │   ├─ time_system.update()
                  │   │   └─> core/time_system.py
                  │   │       ├─ Calculate day/night cycle
                  │   │       └─ Get activity_modifier, brightness, tint
                  │   │
                  │   ├─ For each sprite in self.agents:
                  │   │   │
                  │   │   ├─ if Fish:
                  │   │   │   ├─ newborn = sprite.update(elapsed_time, time_modifier)
                  │   │   │   │   │
                  │   │   │   │   ├─ agents.Fish.update()
                  │   │   │   │   │   └─> core/entities.Fish.update()
                  │   │   │   │   │       ├─ movement_strategy.move()
                  │   │   │   │   │       │   ├─ NeuralMovement.move()
                  │   │   │   │   │       │   │   ├─ genome.brain.think(inputs)
                  │   │   │   │   │       │   │   │   └─ core/neural_brain.py
                  │   │   │   │   │       │   │   └─ Adjust velocity smoothly
                  │   │   │   │   │       │   │
                  │   │   │   │   │       │   └─ AlgorithmicMovement.move()
                  │   │   │   │   │       │       ├─ genome.behavior_algorithm.execute()
                  │   │   │   │   │       │       │   └─> core/algorithms/*.py
                  │   │   │   │   │       │       └─ Adjust velocity smoothly
                  │   │   │   │   │       │
                  │   │   │   │   │       ├─ update_position()
                  │   │   │   │   │       │   └─ pos += vel
                  │   │   │   │   │       │
                  │   │   │   │   │       ├─ Consume energy (metabolism)
                  │   │   │   │   │       ├─ Age fish
                  │   │   │   │   │       ├─ Check if can reproduce
                  │   │   │   │   │       │   └─ Return newborn if ready
                  │   │   │   │   │       └─ Check if dead (old_age/starvation)
                  │   │   │   │   │
                  │   │   │   │   ├─ if newborn not None:
                  │   │   │   │   │   └─ ecosystem.can_reproduce()
                  │   │   │   │   │       └─ Check carrying capacity < max_population
                  │   │   │   │   │
                  │   │   │   │   └─ if is_dead():
                  │   │   │   │       ├─ ecosystem.record_death()
                  │   │   │   │       │   └─ core/ecosystem.py
                  │   │   │   │       │       ├─ Track death cause
                  │   │   │   │       │       ├─ Update generation stats
                  │   │   │   │       │       ├─ Update algorithm stats
                  │   │   │   │       │       └─ Log event
                  │   │   │   │       └─ sprite.kill()
                  │   │   │   │
                  │   │   │   └─ keep_sprite_on_screen()
                  │   │   │
                  │   │   ├─ if Plant:
                  │   │   │   └─ food = sprite.update()
                  │   │   │       └─ Produce food at intervals
                  │   │   │
                  │   │   ├─ if Food or Crab:
                  │   │   │   └─ sprite.update(elapsed_time)
                  │   │   │
                  │   │   └─ Remove off-screen food
                  │   │
                  │   ├─ Auto-spawn food (if AUTO_FOOD_ENABLED)
                  │   │   └─> agents.Food(environment, x, 0)
                  │   │       └─ core/entities.Food (pure logic)
                  │   │
                  │   ├─ handle_collisions()
                  │   │   │
                  │   │   ├─ handle_fish_collisions()
                  │   │   │   │
                  │   │   │   └─ For each Fish:
                  │   │   │       └─ pygame.sprite.spritecollide()
                  │   │   │           ├─ Crab collision:
                  │   │   │           │   ├─ Can crab hunt? (cooldown check)
                  │   │   │           │   ├─ ecosystem.record_death('predation')
                  │   │   │           │   └─ crab.eat_fish(fish)
                  │   │   │           │
                  │   │   │           ├─ Food collision:
                  │   │   │           │   └─ fish.eat(food)
                  │   │   │           │
                  │   │   │           └─ Fish-Fish collision:
                  │   │   │               └─ PokerInteraction(fish1, fish2)
                  │   │   │                   └─ core/fish_poker.py
                  │   │   │                       ├─ Simulate poker game
                  │   │   │                       ├─ Winner gets energy
                  │   │   │                       └─ ecosystem.record_poker()
                  │   │   │
                  │   │   └─ handle_food_collisions()
                  │   │       └─ Similar collision detection
                  │   │
                  │   ├─ handle_reproduction()
                  │   │   │
                  │   │   ├─ Get all fish ready to reproduce
                  │   │   └─ For each fish:
                  │   │       └─ Find nearby compatible mate
                  │   │           └─ fish.try_mate(mate)
                  │   │               ├─ Genome.crossover()
                  │   │               │   ├─ Blend traits
                  │   │               │   ├─ Mutate genes
                  │   │               │   └─ core/genetics.py
                  │   │               └─ Create offspring
                  │   │
                  │   └─ ecosystem.update_population_stats()
                  │       └─ core/ecosystem.py
                  │           └─ Update per-generation statistics
                  │
                  ├─> self.render() [line 534]
                  │   │
                  │   ├─ screen.fill((10, 30, 50))  # Dark water
                  │   │
                  │   ├─ Apply day/night tint
                  │   │   ├─ Get brightness from time_system
                  │   │   ├─ Get tint color from time_system
                  │   │   └─ Render overlay surface with alpha
                  │   │
                  │   ├─ self.agents.draw(screen)
                  │   │   │
                  │   │   └─ For each sprite:
                  │   │       ├─ Get current image
                  │   │       │   ├─ If Fish:
                  │   │       │   │   ├─ Get animation frame
                  │   │       │   │   ├─ Flip if moving left
                  │   │       │   │   ├─ Scale by genetic size_modifier
                  │   │       │   │   └─ Apply genetic color tint
                  │   │       │   │
                  │   │       │   ├─ If Plant:
                  │   │       │   │   └─ Apply swaying effect
                  │   │       │   │
                  │   │       │   └─ Other sprites (static images)
                  │   │       │
                  │   │       └─ screen.blit() to display
                  │   │
                  │   ├─ if show_stats_hud:
                  │   │   │
                  │   │   ├─ For each Fish:
                  │   │   │   └─ draw_health_bar()
                  │   │   │       ├─ Draw energy bar above fish
                  │   │   │       ├─ Color: green (high) -> yellow -> red (low)
                  │   │   │       └─ Display algorithm number if fish has one
                  │   │   │
                  │   │   └─ draw_stats_panel()
                  │   │       ├─ Semi-transparent panel (top-left)
                  │   │       ├─ Display time of day
                  │   │       ├─ Display population stats
                  │   │       ├─ Display generation
                  │   │       ├─ Display births/deaths
                  │   │       ├─ Display death causes
                  │   │       └─ Show PAUSED if paused
                  │   │
                  │   └─ pygame.display.flip()
                  │
                  └─> clock.tick(FRAME_RATE)
                      └─ Cap at 30 FPS


DATA FLOW STRUCTURE:
═══════════════════

INPUT (User Controls in handle_events())
  │
  ├─> SPACE: Spawn food
  │   └─> agents.Food()
  │
  ├─> P: Toggle pause
  │   └─> self.paused = not self.paused
  │
  ├─> H: Toggle HUD
  │   └─> self.show_stats_hud = not self.show_stats_hud
  │
  ├─> R: Generate performance report
  │   └─> ecosystem.get_algorithm_performance_report()
  │       └─ Detailed analysis saved to file
  │
  └─> ESC: Quit


SIMULATION STATE FLOW:
════════════════════

Agents (pygame.sprite.Group)
  │
  ├─> Fish (inherits agents.Fish which wraps core/entities.Fish)
  │   ├─ Genome (speed, size, vision, metabolism, fertility, brain, algorithm)
  │   ├─ Movement Strategy (Neural/Algorithmic/Solo/Schooling)
  │   ├─ Life stage (Baby/Juvenile/Adult/Elder)
  │   ├─ Energy (current and max)
  │   ├─ Age and reproduction state
  │   └─ Collision detection (pygame.sprite.spritecollide)
  │
  ├─> Plants
  │   ├─ Food production timer
  │   └─ Plant type (affects appearance)
  │
  ├─> Crab (predator)
  │   ├─ Hunt cooldown
  │   └─ Prey detection
  │
  ├─> Food (physics)
  │   ├─ Type (algae, protein, vitamin, energy, rare, nectar)
  │   ├─ Energy value
  │   ├─ Sink rate (how fast it falls)
  │   └─ Position (falling from top)
  │
  └─> Castle (static decoration)


ECOSYSTEM STATS FLOW:
═══════════════════

EcosystemManager
  │
  ├─> event_log (last 1000 events)
  │   └─ Births, deaths, deaths-by-cause
  │
  ├─> algorithm_stats[0-47]
  │   ├─ Per-algorithm performance
  │   ├─ Deaths by cause
  │   ├─ Population tracking
  │   ├─ Average lifespan
  │   ├─ Survival rate
  │   └─ Reproduction rate
  │
  ├─> generation_stats
  │   ├─ Population per generation
  │   ├─ Births/deaths per generation
  │   ├─ Average traits (speed, size, energy)
  │   └─ Average age at death
  │
  ├─> poker_stats[0-52]
  │   ├─ Win/loss rates
  │   ├─ Energy gained/lost
  │   ├─ Best hand rank
  │   └─ Average hand rank
  │
  └─> death_causes
      ├─ starvation count
      ├─ old_age count
      ├─ predation count
      └─ unknown count


ALGORITHMS AVAILABLE:
═══════════════════

48 BEHAVIOR ALGORITHMS (48 choices for genetic evolution):

Food Seeking (12):
  1. GreedyFoodSeeker
  2. EnergyAwareFoodSeeker
  3. OpportunisticFeeder
  4. FoodQualityOptimizer
  5. AmbushFeeder
  6. PatrolFeeder
  7. SurfaceSkimmer
  8. BottomFeeder
  9. ZigZagForager
  10. CircularHunter
  11. FoodMemorySeeker
  12. CooperativeForager

Predator Avoidance (10):
  13. PanicFlee
  14. StealthyAvoider
  15. FreezeResponse
  16. ErraticEvader
  17. VerticalEscaper
  18. GroupDefender
  19. SpiralEscape
  20. BorderHugger
  21. PerpendicularEscape
  22. DistanceKeeper

Schooling/Social (10):
  23. TightScholer
  24. LooseScholer
  25. LeaderFollower
  26. AlignmentMatcher
  27. SeparationSeeker
  28. FrontRunner
  29. PerimeterGuard
  30. MirrorMover
  31. BoidsBehavior
  32. DynamicScholer

Energy Management (8):
  33. EnergyConserver
  34. BurstSwimmer
  35. OpportunisticRester
  36. EnergyBalancer
  37. SustainableCruiser
  38. StarvationPreventer
  39. MetabolicOptimizer
  40. AdaptivePacer

Territory/Exploration (8):
  41. TerritorialDefender
  42. RandomExplorer
  43. WallFollower
  44. CornerSeeker
  45. CenterHugger
  46. RoutePatroller
  47. BoundaryExplorer
  48. NomadicWanderer

Each algorithm has:
  ├─ execute(fish) -> (velocity_x, velocity_y)
  ├─ Tunable parameters (bounds defined in base.py)
  ├─ Parameter inheritance with mutation
  └─ Performance tracking (wins, energy, survival)


KEY METRICS TRACKED:
═══════════════════

Per Fish:
  ├─ ID (unique identifier)
  ├─ Generation
  ├─ Age
  ├─ Energy (current/max)
  ├─ Life stage (Baby/Juvenile/Adult/Elder)
  ├─ Genome (all traits)
  ├─ Movement strategy
  ├─ Behavior algorithm (if applicable)
  ├─ Position
  ├─ Velocity
  └─ Size (grows with nutrition)

Per Algorithm:
  ├─ Total births
  ├─ Total deaths
  ├─ Deaths by cause
  ├─ Current population
  ├─ Average lifespan
  ├─ Survival rate
  ├─ Reproduction rate
  ├─ Total food eaten
  ├─ Poker games played
  ├─ Poker wins/losses
  └─ Net energy from poker

Per Generation:
  ├─ Population count
  ├─ Birth count
  ├─ Death count
  ├─ Average age at death
  ├─ Average speed modifier
  ├─ Average size modifier
  └─ Average max energy

Global:
  ├─ Current time (day/night)
  ├─ Total births
  ├─ Total deaths
  ├─ Current generation
  ├─ Frame count
  ├─ Death causes histogram
  └─ Event log (last 1000)
