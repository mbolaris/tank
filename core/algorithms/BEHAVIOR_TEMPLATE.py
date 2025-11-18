"""
Behavior Algorithm Template

Copy this file and rename it to create your new behavior.
Follow the structure and comments below for best practices.

File naming: Use descriptive names like 'food_seeking.py' or 'energy_management.py'
"""

from core.algorithms.base import BehaviorAlgorithm
from typing import Tuple


class BehaviorTemplate(BehaviorAlgorithm):
    """
    [ONE-LINE SUMMARY: What does this behavior do in 10 words or less?]

    [DETAILED DESCRIPTION: Explain the core strategy in 1-2 sentences. What makes
    this behavior unique compared to existing algorithms?]

    Evolutionary Advantage:
        - [Scenario 1]: [Why this helps survival/reproduction in this situation]
        - [Scenario 2]: [Why this helps survival/reproduction in this situation]
        - [Scenario 3]: [Why this helps survival/reproduction in this situation]

    Evolutionary Disadvantage:
        - [Scenario 1]: [What vulnerabilities or costs this creates]
        - [Scenario 2]: [What trade-offs exist]
        - [Scenario 3]: [When this strategy fails]

    Parameters:
        parameter_1_name (float): [What this controls]. Range: [min-max], Default: [value]
        parameter_2_name (float): [What this controls]. Range: [min-max], Default: [value]
        parameter_3_name (float): [What this controls]. Range: [min-max], Default: [value]

    Example Scenarios:
        - [Condition combo 1]: [Expected behavior/movement]
        - [Condition combo 2]: [Expected behavior/movement]
        - [Condition combo 3]: [Expected behavior/movement]

    Implementation Notes:
        - [Any special considerations for this algorithm]
        - [Dependencies on environmental factors]
        - [Interaction with other systems]
    """

    def __init__(self, **kwargs):
        """
        Initialize the behavior with its unique ID and default parameters.

        The algorithm_id must be:
        - Unique across all algorithms
        - Lowercase with underscores
        - Descriptive of the behavior
        """
        # REQUIRED: Set unique algorithm identifier
        algorithm_id = "behavior_template"  # CHANGE THIS to your unique ID

        # REQUIRED: Define all evolvable parameters with defaults
        default_parameters = {
            # Movement parameters (common)
            "speed_multiplier": 1.0,           # How fast to move (0.5-2.0 typical range)
            "detection_range_factor": 1.0,     # Vision range multiplier (0.5-2.0)

            # Decision thresholds (common)
            "energy_threshold": 30.0,          # Energy level for behavior switches (10-60)
            "activation_distance": 150.0,      # Distance to trigger behavior (50-300)

            # Behavior-specific parameters
            "custom_parameter_1": 1.0,         # [Describe what this does]
            "custom_parameter_2": 0.5,         # [Describe what this does]
        }

        # Call parent constructor
        super().__init__(algorithm_id, default_parameters, **kwargs)

    def execute(self, fish) -> Tuple[float, float]:
        """
        Main decision-making method called each simulation frame.

        This method determines the fish's desired movement direction based on:
        - Current energy state
        - Nearby entities (food, other fish, predators)
        - Environmental conditions
        - Behavior-specific logic

        Args:
            fish: The Fish entity executing this behavior

                Key attributes available:
                    fish.position (Vector2)       - Current position (x, y)
                    fish.velocity (Vector2)       - Current velocity vector
                    fish.energy (float)           - Current energy (0-100)
                    fish.genome                   - Genetic traits (speed, size, vision_range, etc.)
                    fish.visible_food (list)      - Food entities in vision range
                    fish.visible_fish (list)      - Other fish in vision range
                    fish.life_stage (str)         - "baby", "juvenile", "adult", "mature"
                    fish.environment              - Access to Environment object

                Key methods available:
                    fish.is_low_energy() -> bool       - Energy < LOW_ENERGY_THRESHOLD (30)
                    fish.is_critical_energy() -> bool  - Energy < STARVATION_THRESHOLD (15)
                    fish.is_safe_energy() -> bool      - Energy > SAFE_ENERGY_THRESHOLD (60)

                Helper methods (from base class):
                    self._find_nearest(position, entities) -> entity or None
                    self._safe_normalize(dx, dy) -> (normalized_x, normalized_y)
                    self._get_predator_threat(fish) -> (threat_x, threat_y) or (0, 0)

        Returns:
            Tuple[float, float]: Normalized direction vector (velocity_x, velocity_y)
                - Must be normalized (magnitude ≈ 1.0)
                - Will be multiplied by fish's actual speed stat
                - Return (0, 0) for no movement

        Implementation Steps:
            1. GATHER CONTEXT: Assess current state (energy, position, nearby entities)
            2. MAKE DECISIONS: Use parameters to choose behavior mode
            3. CALCULATE DIRECTION: Compute desired movement vector
            4. RETURN NORMALIZED: Always normalize before returning
        """

        # ==================================================================
        # STEP 1: GATHER CONTEXT
        # ==================================================================

        # Get current state
        current_energy = fish.energy
        position = fish.position
        velocity = fish.velocity

        # Access parameters (these evolve over generations)
        speed_mult = self.parameters["speed_multiplier"]
        detection_range = fish.genome.vision_range * self.parameters["detection_range_factor"]
        energy_threshold = self.parameters["energy_threshold"]

        # Find relevant entities using helper methods
        nearest_food = self._find_nearest(position, fish.visible_food)
        nearest_fish = self._find_nearest(position, fish.visible_fish)

        # Check for threats (predators, aggressive fish)
        threat_vector = self._get_predator_threat(fish)
        has_threat = (threat_vector[0] != 0 or threat_vector[1] != 0)

        # Environmental context (optional)
        # time_of_day = fish.environment.time_system.get_time_of_day()
        # is_night = time_of_day in ["night", "dusk"]

        # ==================================================================
        # STEP 2: MAKE DECISIONS
        # ==================================================================

        # Default: no movement
        dx, dy = 0.0, 0.0

        # CRITICAL ENERGY: Override all other behavior
        # When near starvation, survival is the only priority
        if fish.is_critical_energy():
            # SURVIVAL CRITICAL: Must find food immediately
            if nearest_food:
                # Direct path to nearest food, ignore all else
                dx = nearest_food.position.x - position.x
                dy = nearest_food.position.y - position.y
                # Return immediately, bypassing all other logic
                return self._safe_normalize(dx, dy)
            else:
                # No food visible: search desperately (random movement)
                import random
                dx = random.uniform(-1.0, 1.0)
                dy = random.uniform(-1.0, 1.0)
                return self._safe_normalize(dx, dy)

        # THREAT AVOIDANCE: High priority but not above critical energy
        if has_threat:
            # Predator threat detected - evasion takes priority
            # threat_vector points AWAY from threat (already calculated)
            dx = threat_vector[0]
            dy = threat_vector[1]

            # Can still opportunistically grab food if on escape path
            if nearest_food and current_energy < energy_threshold:
                # Blend threat avoidance with food seeking (70% avoid, 30% food)
                food_dx = nearest_food.position.x - position.x
                food_dy = nearest_food.position.y - position.y
                food_dx, food_dy = self._safe_normalize(food_dx, food_dy)

                dx = 0.7 * dx + 0.3 * food_dx
                dy = 0.7 * dy + 0.3 * food_dy

            return self._safe_normalize(dx, dy)

        # LOW ENERGY: Prioritize food seeking
        if fish.is_low_energy():
            if nearest_food:
                # Calculate distance to food
                distance_to_food = ((nearest_food.position.x - position.x) ** 2 +
                                    (nearest_food.position.y - position.y) ** 2) ** 0.5

                # Only pursue if within detection range (parameter-controlled)
                if distance_to_food < detection_range:
                    dx = nearest_food.position.x - position.x
                    dy = nearest_food.position.y - position.y
                    return self._safe_normalize(dx, dy)

        # SAFE ENERGY: Implement your custom behavior logic here
        if fish.is_safe_energy():
            # Example: At safe energy, do something else (explore, socialize, etc.)
            # This is where your unique behavior strategy goes

            # Example: Social behavior - move toward nearest fish
            if nearest_fish:
                dx = nearest_fish.position.x - position.x
                dy = nearest_fish.position.y - position.y

                # Use custom parameter to control approach distance
                distance_to_fish = ((dx ** 2) + (dy ** 2)) ** 0.5
                if distance_to_fish < self.parameters["activation_distance"]:
                    # Close enough, apply custom behavior
                    # (modify dx, dy based on your algorithm logic)
                    pass

            # Example: Exploratory behavior
            else:
                # No nearby fish, explore using custom pattern
                # This is behavior-specific - implement your strategy here
                import random
                dx = random.uniform(-0.5, 0.5)
                dy = random.uniform(-0.5, 0.5)

        # ==================================================================
        # STEP 3: CALCULATE DIRECTION (if not already returned)
        # ==================================================================

        # At this point, dx and dy should be set by one of the above conditions
        # If still (0, 0), fish will not move this frame (which is valid)

        # Optional: Apply parameter-based modifications
        # dx *= self.parameters["custom_parameter_1"]
        # dy *= self.parameters["custom_parameter_2"]

        # ==================================================================
        # STEP 4: RETURN NORMALIZED DIRECTION
        # ==================================================================

        # ALWAYS normalize before returning (handles zero vectors safely)
        return self._safe_normalize(dx, dy)


# ==================================================================
# INTEGRATION CHECKLIST
# ==================================================================
"""
After implementing your behavior:

1. ✅ Rename the class from BehaviorTemplate to YourBehaviorName
2. ✅ Set a unique algorithm_id in __init__
3. ✅ Define meaningful parameters with good defaults
4. ✅ Fill out complete docstring with advantages/disadvantages
5. ✅ Implement execute() method with your logic
6. ✅ Add to core/algorithms/__init__.py:
      from core.algorithms.your_file import YourBehaviorName
      ALL_ALGORITHMS.append(YourBehaviorName)

7. ✅ Add parameter bounds to core/algorithms/base.py:
      ALGORITHM_PARAMETER_BOUNDS = {
          "your_algorithm_id": {
              "parameter_1": (min, max),
              "parameter_2": (min, max),
          },
      }

8. ✅ Update TOTAL_ALGORITHM_COUNT in core/constants.py (increment by 1)

9. ✅ Test with: python main.py --headless --max-frames 5000 --seed 42

10. ✅ Analyze results and iterate!
"""

# ==================================================================
# COMMON PATTERNS
# ==================================================================
"""
Pattern 1: Distance-Based Behavior
    target = self._find_nearest(position, entities)
    if target:
        distance = ((target.position.x - position.x)**2 +
                   (target.position.y - position.y)**2)**0.5
        if distance < self.parameters["threshold_distance"]:
            # Do something

Pattern 2: Energy-Gated Behavior
    if fish.is_low_energy():
        # Survival mode
    elif fish.is_safe_energy():
        # Opportunistic mode
    else:
        # Normal mode

Pattern 3: Weighted Blending
    direction_1 = self._calculate_food_direction(fish)
    direction_2 = self._calculate_social_direction(fish)

    weight_1 = self.parameters["priority_1"]
    weight_2 = 1.0 - weight_1

    dx = direction_1[0] * weight_1 + direction_2[0] * weight_2
    dy = direction_1[1] * weight_1 + direction_2[1] * weight_2

Pattern 4: State Machine
    if self.state == "searching":
        # Search logic
        if found_target:
            self.state = "pursuing"
    elif self.state == "pursuing":
        # Pursuit logic
        if lost_target:
            self.state = "searching"

Pattern 5: Memory-Based
    # Store positions in fish.memory (if using memory system)
    # Return to successful locations
    if hasattr(fish, 'memory') and fish.memory.food_locations:
        best_location = fish.memory.food_locations[0]
        dx = best_location.x - position.x
        dy = best_location.y - position.y
"""
