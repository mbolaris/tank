# Key Code Snippets & Entry Points

## MAIN ENTRY POINT

**File:** /home/user/tank/fishtank.py (lines 549-559)

```python
def main() -> None:
    """Entry point for the simulation."""
    pygame.init()
    game = FishTankSimulator()
    try:
        game.run()
    finally:
        pygame.quit()

if __name__ == "__main__":
    main()
```

**To run:** `python fishtank.py`


## MAIN SIMULATOR CLASS

**File:** /home/user/tank/fishtank.py (lines 16-45)

```python
class FishTankSimulator:
    """A simulation of a fish tank with full ecosystem dynamics."""

    def __init__(self) -> None:
        """Initialize the simulation."""
        self.clock = pygame.time.Clock()
        self.frame_count = 0
        self.agents = pygame.sprite.Group()  # All game entities
        self.environment = None  # Spatial queries interface
        self.ecosystem = None    # Population & statistics tracker
        self.time_system = TimeSystem()  # Day/night cycle
        self.paused = False
        self.show_stats_hud = True
```

**Key Methods:**
- `setup_game()` - Initialize pygame display and create initial agents
- `create_initial_agents()` - Spawn fish (4 species), plants, crab, castle
- `update()` - Main simulation loop (update all entities, handle collisions)
- `render()` - Draw everything to screen
- `handle_events()` - Process user input
- `run()` - Infinite game loop


## MAIN SIMULATION LOOP

**File:** /home/user/tank/fishtank.py (lines 160-254)

```python
def update(self) -> None:
    """Update the state of the simulation."""
    if self.paused:
        return

    elapsed_time = pygame.time.get_ticks() - self.start_ticks
    self.frame_count += 1

    # Update time system (day/night)
    self.time_system.update()
    time_modifier = self.time_system.get_activity_modifier()

    # Track new agents (births, food production)
    new_agents = []

    # Update all agents
    for sprite in list(self.agents):
        if isinstance(sprite, agents.Fish):
            # Fish update returns potential newborn
            newborn = sprite.update(elapsed_time, time_modifier)
            if newborn is not None and self.ecosystem is not None:
                fish_count = len([a for a in self.agents if isinstance(a, agents.Fish)])
                if self.ecosystem.can_reproduce(fish_count):
                    new_agents.append(newborn)

            # Handle fish death
            if sprite.is_dead():
                if self.ecosystem is not None:
                    algorithm_id = None
                    if sprite.genome.behavior_algorithm is not None:
                        algorithm_id = get_algorithm_index(sprite.genome.behavior_algorithm)
                    self.ecosystem.record_death(
                        sprite.fish_id,
                        sprite.generation,
                        sprite.age,
                        sprite.get_death_cause(),
                        sprite.genome,
                        algorithm_id=algorithm_id
                    )
                sprite.kill()

        elif isinstance(sprite, agents.Plant):
            food = sprite.update(elapsed_time, time_modifier)
            if food is not None:
                new_agents.append(food)
        else:
            sprite.update(elapsed_time)

        self.keep_sprite_on_screen(sprite)
        
        # Remove off-screen food
        if isinstance(sprite, agents.Food) and sprite.rect.y >= SCREEN_HEIGHT:
            sprite.kill()

    # Add new agents
    if new_agents:
        self.agents.add(*new_agents)

    # Auto food spawning
    if AUTO_FOOD_ENABLED and self.environment is not None:
        self.auto_food_timer += 1
        if self.auto_food_timer >= AUTO_FOOD_SPAWN_RATE:
            self.auto_food_timer = 0
            x = random.randint(0, SCREEN_WIDTH)
            food = agents.Food(self.environment, x, 0, allow_stationary_types=False)
            food.pos.y = 0
            food.rect.y = 0
            self.agents.add(food)

    # Handle collisions
    self.handle_collisions()

    # Handle reproduction (mate finding)
    self.handle_reproduction()

    # Update ecosystem stats
    if self.ecosystem is not None:
        fish_list = [a for a in self.agents if isinstance(a, agents.Fish)]
        self.ecosystem.update_population_stats(fish_list)
        self.ecosystem.update(self.frame_count)
```

**Key Points:**
- Called once per frame (30 FPS)
- Updates each agent's position, energy, age
- Handles births and deaths
- Tracks all statistics in ecosystem manager
- Auto-spawns food every 45 frames


## RENDERING

**File:** /home/user/tank/fishtank.py (lines 436-465)

```python
def render(self) -> None:
    """Render the current state of the simulation to the screen."""
    if self.screen is None:
        return

    # Fill with base color (dark water)
    self.screen.fill((10, 30, 50))

    # Apply day/night tint
    brightness = self.time_system.get_brightness()
    tint_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    tint_color = self.time_system.get_screen_tint()
    tint_surface.fill(tint_color)
    tint_surface.set_alpha(int((1.0 - brightness) * 100))
    self.screen.blit(tint_surface, (0, 0))

    # Draw all sprites
    self.agents.draw(self.screen)

    # Draw health bars and stats panel (if HUD is enabled)
    if self.show_stats_hud:
        # Draw health bars for fish
        for sprite in self.agents:
            if isinstance(sprite, agents.Fish):
                self.draw_health_bar(sprite)

        # Draw stats panel
        self.draw_stats_panel()

    pygame.display.flip()
```

**Note:** Rendering is separate from simulation logic but tightly coupled in the same class.


## INITIAL AGENT CREATION

**File:** /home/user/tank/fishtank.py (lines 64-158)

```python
def create_initial_agents(self) -> None:
    """Create initial sprites in the fish tank with multiple species."""
    if self.environment is None or self.ecosystem is None:
        return

    # Species 1: Solo fish with traditional AI (rule-based)
    solo_fish = agents.Fish(
        self.environment,
        movement_strategy.SoloFishMovement(),
        FILES['solo_fish'],
        *INIT_POS['fish'],
        3,
        generation=0,
        ecosystem=self.ecosystem
    )

    # Species 2: Algorithmic fish with parametrizable behavior algorithms
    algorithmic_fish = []
    for i in range(2):
        x = INIT_POS['school'][0] + random.randint(-80, 80)
        y = INIT_POS['school'][1] + random.randint(-50, 50)
        genome = Genome.random(use_brain=False, use_algorithm=True)
        fish = agents.Fish(
            self.environment,
            movement_strategy.AlgorithmicMovement(),
            FILES['schooling_fish'],
            x, y, 4,
            genome=genome,
            generation=0,
            ecosystem=self.ecosystem
        )
        algorithmic_fish.append(fish)

    # Species 3: Schooling fish with neural network brains (learning AI)
    neural_schooling_fish = []
    for i in range(2):
        x = INIT_POS['school'][0] + random.randint(-50, 50)
        y = INIT_POS['school'][1] + random.randint(-30, 30)
        genome = Genome.random(use_brain=True, use_algorithm=False)
        fish = agents.Fish(
            self.environment,
            movement_strategy.NeuralMovement(),
            FILES['schooling_fish'],
            x, y, 4,
            genome=genome,
            generation=0,
            ecosystem=self.ecosystem
        )
        neural_schooling_fish.append(fish)

    # Species 4: Traditional schooling fish (rule-based AI)
    schooling_fish = []
    for i in range(2):
        x = INIT_POS['school'][0] + random.randint(-50, 50)
        y = INIT_POS['school'][1] + random.randint(-30, 30)
        genome = Genome.random(use_brain=False, use_algorithm=False)
        fish = agents.Fish(
            self.environment,
            movement_strategy.SchoolingFishMovement(),
            FILES['schooling_fish'],
            x, y, 4,
            genome=genome,
            generation=0,
            ecosystem=self.ecosystem
        )
        schooling_fish.append(fish)

    # Add all agents
    self.agents.add(
        solo_fish,
        *algorithmic_fish,
        *neural_schooling_fish,
        *schooling_fish,
        agents.Crab(self.environment),
        agents.Plant(self.environment, 1),
        agents.Plant(self.environment, 2),
        agents.Plant(self.environment, 1),  # plant3
        agents.Castle(self.environment),
    )
```


## ECOSYSTEM STATISTICS TRACKING

**File:** /home/user/tank/core/ecosystem.py (lines 275-327)

```python
def record_death(self, fish_id: int, generation: int, age: int,
                 cause: str = 'unknown', genome: Optional['genetics.Genome'] = None,
                 algorithm_id: Optional[int] = None) -> None:
    """Record a death event."""
    self.total_deaths += 1

    # Update generation stats
    if generation in self.generation_stats:
        stats = self.generation_stats[generation]
        stats.deaths += 1
        stats.population = max(0, stats.population - 1)
        
        # Update average age at death
        total_fish = stats.deaths
        stats.avg_age = (stats.avg_age * (total_fish - 1) + age) / total_fish

    # Track death causes
    self.death_causes[cause] += 1

    # Update algorithm stats
    if algorithm_id is not None and algorithm_id in self.algorithm_stats:
        algo_stats = self.algorithm_stats[algorithm_id]
        algo_stats.total_deaths += 1
        algo_stats.current_population = max(0, algo_stats.current_population - 1)
        algo_stats.total_lifespan += age

        # Track death cause by algorithm
        if cause == 'starvation':
            algo_stats.deaths_starvation += 1
        elif cause == 'old_age':
            algo_stats.deaths_old_age += 1
        elif cause == 'predation':
            algo_stats.deaths_predation += 1

    # Log event
    details = f"Age: {age}, Generation: {generation}"
    if algorithm_id is not None:
        details += f", Algorithm: {algorithm_id}"
    self._add_event(EcosystemEvent(
        frame=self.frame_count,
        event_type=cause,
        fish_id=fish_id,
        details=details
    ))
```


## MOVEMENT STRATEGY EXECUTION

**File:** /home/user/tank/movement_strategy.py (lines 92-123)

```python
class AlgorithmicMovement(MovementStrategy):
    """Movement strategy controlled by a behavior algorithm."""

    def move(self, sprite: 'Fish') -> None:
        """Move using the fish's behavior algorithm."""
        # Check if fish has a behavior algorithm
        if sprite.genome.behavior_algorithm is None:
            # Fallback to simple random movement
            sprite.add_random_velocity_change(RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR)
            super().move(sprite)
            return

        # Execute the algorithm to get desired velocity
        desired_vx, desired_vy = sprite.genome.behavior_algorithm.execute(sprite)

        # Apply algorithm decision
        target_vx = desired_vx * sprite.speed
        target_vy = desired_vy * sprite.speed

        # Smoothly interpolate toward desired velocity
        sprite.vel.x += (target_vx - sprite.vel.x) * ALGORITHMIC_MOVEMENT_SMOOTHING
        sprite.vel.y += (target_vy - sprite.vel.y) * ALGORITHMIC_MOVEMENT_SMOOTHING

        # Normalize velocity to maintain consistent speed
        vel_length = sprite.vel.length()
        if vel_length > 0:
            target_speed = min(sprite.speed * ALGORITHMIC_MAX_SPEED_MULTIPLIER, vel_length)
            sprite.vel = sprite.vel.normalize() * target_speed

        super().move(sprite)
```

**Note:** Each algorithm is a class that implements `execute(fish)` method


## FISH ENTITY CORE LOGIC

**File:** /home/user/tank/core/entities.py (partial)

```python
class Fish(Agent):
    """Pure entity representing a fish (no pygame dependencies)."""
    
    BABY_AGE = 100
    JUVENILE_AGE = 500
    ADULT_AGE = 2000
    ELDER_AGE = 5000
    BASE_MAX_AGE = 8000
    BASE_MAX_ENERGY = 300.0
    ENERGY_FROM_FOOD = 50.0
    BASE_METABOLISM = 0.3
    
    def update(self, elapsed_time: int, time_modifier: float = 1.0) -> Optional['Fish']:
        """Update fish state and return potential newborn."""
        # Apply movement strategy
        self.movement_strategy.move(self)
        
        # Update position
        self.update_position()
        
        # Consume energy
        energy_cost = self.BASE_METABOLISM * self.metabolism_rate * time_modifier
        self.energy -= energy_cost
        
        # Age the fish
        self.age += 1
        
        # Check for reproduction
        if self.can_reproduce():
            return self.attempt_reproduction()
        
        return None
    
    def can_reproduce(self) -> bool:
        """Check if fish is ready to reproduce."""
        return (self.life_stage == LifeStage.ADULT and 
                self.energy >= self.REPRODUCTION_ENERGY_THRESHOLD and
                self.reproduction_cooldown <= 0)
    
    def is_dead(self) -> bool:
        """Check if fish should die."""
        return (self.energy <= 0 or self.age >= self.max_age)
    
    def get_death_cause(self) -> str:
        """Determine cause of death."""
        if self.energy <= 0:
            return 'starvation'
        elif self.age >= self.max_age:
            return 'old_age'
        return 'unknown'
```


## GENOME & GENETIC EVOLUTION

**File:** /home/user/tank/core/genetics.py (partial)

```python
@dataclass
class Genome:
    """Represents the genetic makeup of a fish."""
    
    # Performance traits
    speed_modifier: float = 1.0
    size_modifier: float = 1.0
    vision_range: float = 1.0
    
    # Metabolic traits
    metabolism_rate: float = 1.0
    max_energy: float = 1.0
    fertility: float = 1.0
    
    # Behavioral traits
    aggression: float = 0.5
    social_tendency: float = 0.5
    
    # Visual traits
    color_hue: float = 0.5
    
    # Neural brain (optional)
    brain: Optional['NeuralBrain'] = None
    
    # Behavior algorithm (NEW: algorithmic evolution system)
    behavior_algorithm: Optional['BehaviorAlgorithm'] = None
    
    @classmethod
    def random(cls, use_brain: bool = True, use_algorithm: bool = True) -> 'Genome':
        """Create a random genome with traits within normal ranges."""
        brain = None
        if use_brain:
            from core.neural_brain import NeuralBrain
            brain = NeuralBrain.random()
        
        algorithm = None
        if use_algorithm:
            from core.behavior_algorithms import get_random_algorithm
            algorithm = get_random_algorithm()
        
        return cls(
            speed_modifier=random.uniform(0.5, 1.5),
            size_modifier=random.uniform(0.7, 1.3),
            vision_range=random.uniform(0.7, 1.3),
            metabolism_rate=random.uniform(0.7, 1.3),
            max_energy=random.uniform(0.7, 1.5),
            fertility=random.uniform(0.6, 1.4),
            aggression=random.uniform(0.0, 1.0),
            social_tendency=random.uniform(0.0, 1.0),
            color_hue=random.uniform(0.0, 1.0),
            brain=brain,
            behavior_algorithm=algorithm
        )
```


## ALGORITHM PERFORMANCE REPORT

**File:** /home/user/tank/fishtank.py (lines 486-498)

```python
elif event.key == pygame.K_r:
    # Print algorithm performance report
    if self.ecosystem is not None:
        print("\n" + "=" * 80)
        print("GENERATING ALGORITHM PERFORMANCE REPORT...")
        print("=" * 80)
        report = self.ecosystem.get_algorithm_performance_report()
        print(report)
        # Also save to file
        with open('algorithm_performance_report.txt', 'w') as f:
            f.write(report)
        print("\nReport saved to: algorithm_performance_report.txt")
        print("=" * 80 + "\n")
```

**Press 'R' during simulation to generate a detailed report of:**
- Each algorithm's survival rate
- Average lifespan
- Reproduction success
- Current population
- Death causes


## COLLISION HANDLING

**File:** /home/user/tank/fishtank.py (lines 261-293)

```python
def handle_fish_collisions(self) -> None:
    """Handle collisions involving fish."""
    for fish in list(self.agents.sprites()):
        if isinstance(fish, agents.Fish):
            collisions = pygame.sprite.spritecollide(fish, self.agents, False, pygame.sprite.collide_mask)
            for collision_sprite in collisions:
                if isinstance(collision_sprite, agents.Crab):
                    # Crab can only kill if hunt cooldown is ready
                    if collision_sprite.can_hunt():
                        # Record death from predation
                        if self.ecosystem is not None:
                            algorithm_id = None
                            if fish.genome.behavior_algorithm is not None:
                                algorithm_id = get_algorithm_index(fish.genome.behavior_algorithm)
                            self.ecosystem.record_death(
                                fish.fish_id,
                                fish.generation,
                                fish.age,
                                'predation',
                                fish.genome,
                                algorithm_id=algorithm_id
                            )
                        collision_sprite.eat_fish(fish)
                        fish.kill()
                elif isinstance(collision_sprite, agents.Food):
                    fish.eat(collision_sprite)
                elif isinstance(collision_sprite, agents.Fish):
                    # Fish-to-fish poker interaction
                    poker = PokerInteraction(fish, collision_sprite)
                    poker.play_poker()
```


## GAME CONTROLS

**File:** /home/user/tank/fishtank.py (lines 467-502)

```python
def handle_events(self) -> bool:
    """Handle user input and other events."""
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                # Drop food manually
                if self.environment is not None:
                    x = random.randint(0, SCREEN_WIDTH)
                    y = 0
                    food = agents.Food(self.environment, x, y, allow_stationary_types=False)
                    self.agents.add(food)
            elif event.key == pygame.K_p:
                # Toggle pause
                self.paused = not self.paused
            elif event.key == pygame.K_h:
                # Toggle stats and health bars HUD
                self.show_stats_hud = not self.show_stats_hud
            elif event.key == pygame.K_r:
                # Print algorithm performance report
                if self.ecosystem is not None:
                    report = self.ecosystem.get_algorithm_performance_report()
                    print(report)
            elif event.key == pygame.K_ESCAPE:
                # Quit
                return False
    return True
```

**Controls:**
- SPACE: Manually drop food
- P: Pause/Resume simulation
- H: Toggle HUD (health bars, stats panel)
- R: Generate algorithm performance report to file
- ESC: Quit simulation
