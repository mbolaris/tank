"""Predator entity logic for crabs."""

from typing import TYPE_CHECKING, Optional

from core.config.entities import (CRAB_ATTACK_COOLDOWN,
                                  CRAB_ATTACK_ENERGY_TRANSFER,
                                  CRAB_IDLE_CONSUMPTION, CRAB_INITIAL_ENERGY)
from core.entities.base import Agent, EntityUpdateResult
from core.entities.fish import Fish
from core.entities.resources import Food
from core.genetics import Genome

if TYPE_CHECKING:
    from core.world import World
    from core.worlds.petri.dish import PetriDish

PETRI_CRAB_SPEED_MULTIPLIER = 2.5


class Crab(Agent):
    """A predator crab that hunts fish and food (pure logic, no rendering)."""

    def __init__(
        self,
        environment: "World",
        genome: Optional["Genome"] = None,
        x: float = 100,
        y: float = 550,
    ) -> None:
        """Initialize a crab."""
        # Use require_rng for deterministic genome creation
        from core.util.rng import require_rng

        # Crabs are slower and less aggressive now
        if genome is not None:
            self.genome: Genome = genome
        else:
            rng = require_rng(environment, "Crab.__init__.genome")
            self.genome = Genome.random(rng=rng)
        base_speed = 1.5  # Much slower than before (was 2)
        speed = base_speed * self.genome.speed_modifier

        super().__init__(environment, x, y, speed)
        self._base_speed = speed

        self.is_predator = True

        # Energy system - max energy based on size
        self.max_energy: float = CRAB_INITIAL_ENERGY * self.genome.physical.size_modifier.value
        self.energy: float = self.max_energy

        # Hunting mechanics
        self.hunt_cooldown: int = 0

        # Petri mode orbit state (for perimeter movement)
        self._orbit_theta: Optional[float] = None
        self._orbit_dir: Optional[int] = None  # +1 or -1

    def can_hunt(self) -> bool:
        """Check if crab can hunt (cooldown expired)."""
        return self.hunt_cooldown <= 0

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        """Modify energy and record delta."""
        old_energy = self.energy
        new_energy = self.energy + amount
        self.energy = max(0.0, min(self.max_energy, new_energy))

        delta = self.energy - old_energy
        if delta != 0 and hasattr(self.environment, "record_energy_delta"):
            self.environment.record_energy_delta(self, delta, source)
        return delta

    def consume_energy(self) -> None:
        """Consume energy based on metabolism."""
        metabolism = CRAB_IDLE_CONSUMPTION * self.genome.metabolism_rate
        self.modify_energy(-metabolism, source="metabolism")

    def eat_fish(self, fish: Fish) -> None:
        """Eat a fish and gain energy."""
        self.modify_energy(CRAB_ATTACK_ENERGY_TRANSFER, source="ate_fish")
        self.hunt_cooldown = CRAB_ATTACK_COOLDOWN

    def eat_food(self, food: "Food") -> None:
        """Eat food and gain energy."""
        energy_gained = food.get_energy_value()
        self.modify_energy(energy_gained, source="ate_food")

    def update(
        self, frame_count: int, time_modifier: float = 1.0, time_of_day: Optional[float] = None
    ) -> "EntityUpdateResult":
        """Update the crab state.

        Movement is world-aware:
        - Tank mode: patrol back and forth across the tank bottom
        - Petri mode: orbit along the circular dish perimeter
        """
        import math

        # Update cooldown
        if self.hunt_cooldown > 0:
            self.hunt_cooldown -= 1

        # Consume energy
        self.consume_energy()

        # Determine movement mode based on world type
        world_type = getattr(self.environment, "world_type", None)
        dish = getattr(self.environment, "dish", None)

        if world_type == "petri" and dish is not None:
            # Petri mode: orbit the dish perimeter
            petri_speed = self._base_speed * PETRI_CRAB_SPEED_MULTIPLIER
            self._update_petri_orbit(time_modifier, dish, math, petri_speed)
        else:
            # Tank mode: patrol bottom
            self._update_tank_patrol()

        # Call parent update which handles position updates and boundary bouncing
        super().update(frame_count, time_modifier, time_of_day)

        return EntityUpdateResult()

    def _update_tank_patrol(self) -> None:
        """Tank mode: patrol back and forth on the bottom."""
        from core.util.rng import require_rng

        # If no horizontal velocity, pick a random direction
        if abs(self.vel.x) < 0.1:
            rng = require_rng(self.environment, "Crab.update.patrol")
            direction = rng.choice([-1, 1])
            self.vel.x = direction * self.speed

        # Stay on bottom (no vertical movement)
        self.vel.y = 0
        target_y = None
        bounds = self.environment.get_bounds()
        (_, min_y), (_, max_y) = bounds
        bottom_y = max_y - self.height

        # Prefer the configured crab lane if available (keeps visuals consistent).
        sim_config = getattr(self.environment, "simulation_config", None)
        display = getattr(sim_config, "display", None)
        init_pos = getattr(display, "init_pos", None)
        if isinstance(init_pos, dict):
            crab_pos = init_pos.get("crab")
            if isinstance(crab_pos, (list, tuple)) and len(crab_pos) > 1:
                try:
                    target_y = float(crab_pos[1])
                except (TypeError, ValueError):
                    target_y = None

        if target_y is None:
            target_y = bottom_y
        else:
            target_y = min(target_y, bottom_y)
        target_y = max(target_y, min_y)

        if abs(self.pos.y - target_y) > 0.1:
            self.pos.y = target_y
            if hasattr(self, "rect"):
                self.rect.y = self.pos.y

    def _update_petri_orbit(
        self, time_modifier: float, dish: "PetriDish", math, orbit_speed: float
    ) -> None:
        """Petri mode: orbit along the dish perimeter."""
        from core.util.rng import require_rng

        # Calculate agent radius (approximate as half of width)
        agent_r = self.width / 2
        orbit_radius = dish.r - agent_r - 2.0  # 2px margin from edge

        if orbit_radius <= 0:
            # Dish too small, stay at center
            return

        # Initialize theta from current position if not set
        if self._orbit_theta is None:
            dx = self.pos.x + agent_r - dish.cx
            dy = self.pos.y + agent_r - dish.cy
            self._orbit_theta = math.atan2(dy, dx)

        # Initialize orbit direction if not set (deterministic via RNG)
        if self._orbit_dir is None:
            rng = require_rng(self.environment, "Crab.orbit_dir")
            self._orbit_dir = rng.choice([-1, 1])

        # Calculate angular velocity: omega = speed / radius
        omega = (orbit_speed / orbit_radius) * self._orbit_dir * time_modifier * 0.1

        # Update theta
        self._orbit_theta += omega

        # Set position on perimeter (top-left corner, not center)
        cx = dish.cx + orbit_radius * math.cos(self._orbit_theta)
        cy = dish.cy + orbit_radius * math.sin(self._orbit_theta)
        self.pos.x = cx - agent_r
        self.pos.y = cy - agent_r

        # Set velocity tangent to circle for physics coherence
        tangent_x = -math.sin(self._orbit_theta) * self._orbit_dir
        tangent_y = math.cos(self._orbit_theta) * self._orbit_dir
        self.vel.x = tangent_x * orbit_speed
        self.vel.y = tangent_y * orbit_speed

        # Sync rect if present
        if hasattr(self, "rect"):
            self.rect.x = self.pos.x
            self.rect.y = self.pos.y
