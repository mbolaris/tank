"""Behavioral learning system for fish.

This module implements within-lifetime learning where fish can improve their
behavior based on experience. Learned behaviors are stored in the genome and
can influence behavior algorithm parameters.

Learning Types:
- Food Finding: Learn better food-seeking patterns
- Predator Avoidance: Learn better escape routes
- Poker Playing: Learn opponent tendencies and optimal strategies
- Energy Management: Learn optimal energy conservation

Learned behaviors can:
1. Modify algorithm parameters within lifetime
2. Be partially inherited by offspring (cultural evolution)
3. Decay over time if not reinforced
"""

import random
from typing import Dict, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

if TYPE_CHECKING:
    from core.entities import Fish
    from core.genetics import Genome


class LearningType(Enum):
    """Types of learnable behaviors."""
    FOOD_FINDING = "food_finding"
    PREDATOR_AVOIDANCE = "predator_avoidance"
    POKER_STRATEGY = "poker_strategy"
    ENERGY_MANAGEMENT = "energy_management"
    SPATIAL_NAVIGATION = "spatial_navigation"


@dataclass
class LearningEvent:
    """Represents a learning experience."""
    learning_type: LearningType
    success: bool  # Whether the action was successful
    reward: float  # Magnitude of the reward/punishment
    context: Dict[str, float] = field(default_factory=dict)  # Context info


class BehavioralLearningSystem:
    """Manages learning and behavioral adaptation within a fish's lifetime.

    This system allows fish to improve their behavior through experience,
    storing learned behaviors in the genome's learned_behaviors dictionary.

    Learning Parameters:
    - learning_rate: How quickly fish learn from experiences (0.0-1.0)
    - decay_rate: How quickly learned behaviors fade without reinforcement
    - max_adjustment: Maximum parameter adjustment from learning
    """

    # Learning rates for different types
    DEFAULT_LEARNING_RATE = 0.05  # 5% adjustment per learning event
    DEFAULT_DECAY_RATE = 0.001  # 0.1% decay per frame
    MAX_LEARNED_ADJUSTMENT = 0.3  # Max 30% parameter adjustment from learning

    # Inheritance rates (how much learned behavior passes to offspring)
    CULTURAL_INHERITANCE_RATE = 0.25  # 25% of learned behaviors inherited

    def __init__(self, genome: 'Genome', learning_rate: float = DEFAULT_LEARNING_RATE,
                 decay_rate: float = DEFAULT_DECAY_RATE):
        """Initialize the learning system.

        Args:
            genome: The fish's genome (stores learned_behaviors)
            learning_rate: Base learning rate
            decay_rate: Rate at which learned behaviors decay
        """
        self.genome = genome
        self.learning_rate = learning_rate
        self.decay_rate = decay_rate

        # Initialize learned_behaviors - ensure all required keys exist
        # This handles both empty dicts and partially populated ones from inheritance
        required_keys = {
            'food_finding_efficiency': 0.0,  # -0.3 to +0.3 adjustment
            'predator_escape_skill': 0.0,
            'poker_hand_selection': 0.0,
            'poker_positional_awareness': 0.0,
            'poker_aggression_tuning': 0.0,
            'energy_conservation': 0.0,
            'spatial_memory_strength': 0.0,
            'successful_food_finds': 0.0,  # Counter
            'successful_predator_escapes': 0.0,  # Counter
            'poker_games_won': 0.0,  # Counter
            'poker_games_lost': 0.0,  # Counter
        }

        # Add any missing keys while preserving existing values
        for key, default_value in required_keys.items():
            if key not in self.genome.learned_behaviors:
                self.genome.learned_behaviors[key] = default_value

    def learn_from_event(self, event: LearningEvent) -> None:
        """Process a learning event and update learned behaviors.

        Args:
            event: The learning event to process
        """
        if event.learning_type == LearningType.FOOD_FINDING:
            self._learn_food_finding(event)
        elif event.learning_type == LearningType.PREDATOR_AVOIDANCE:
            self._learn_predator_avoidance(event)
        elif event.learning_type == LearningType.POKER_STRATEGY:
            self._learn_poker_strategy(event)
        elif event.learning_type == LearningType.ENERGY_MANAGEMENT:
            self._learn_energy_management(event)
        elif event.learning_type == LearningType.SPATIAL_NAVIGATION:
            self._learn_spatial_navigation(event)

    def _learn_food_finding(self, event: LearningEvent) -> None:
        """Learn from food-finding experiences.

        Args:
            event: Food finding event (success=found food, reward=energy gained)
        """
        if event.success:
            # Successful food find - reinforce current behavior
            adjustment = self.learning_rate * event.reward
            self.genome.learned_behaviors['food_finding_efficiency'] += adjustment
            self.genome.learned_behaviors['successful_food_finds'] += 1
        else:
            # Failed to find food - slightly reduce efficiency
            adjustment = self.learning_rate * 0.5
            self.genome.learned_behaviors['food_finding_efficiency'] -= adjustment

        # Clamp to max adjustment range
        self.genome.learned_behaviors['food_finding_efficiency'] = max(
            -self.MAX_LEARNED_ADJUSTMENT,
            min(self.MAX_LEARNED_ADJUSTMENT,
                self.genome.learned_behaviors['food_finding_efficiency'])
        )

    def _learn_predator_avoidance(self, event: LearningEvent) -> None:
        """Learn from predator encounters.

        Args:
            event: Predator event (success=escaped, reward=damage avoided)
        """
        if event.success:
            # Successfully escaped - reinforce escape behavior
            adjustment = self.learning_rate * event.reward * 2.0  # Higher learning from danger
            self.genome.learned_behaviors['predator_escape_skill'] += adjustment
            self.genome.learned_behaviors['successful_predator_escapes'] += 1
        else:
            # Failed to escape (took damage) - adjust behavior
            adjustment = self.learning_rate * 1.5
            self.genome.learned_behaviors['predator_escape_skill'] += adjustment

        # Clamp to range
        self.genome.learned_behaviors['predator_escape_skill'] = max(
            -self.MAX_LEARNED_ADJUSTMENT,
            min(self.MAX_LEARNED_ADJUSTMENT,
                self.genome.learned_behaviors['predator_escape_skill'])
        )

    def _learn_poker_strategy(self, event: LearningEvent) -> None:
        """Learn from poker game outcomes.

        Args:
            event: Poker event (success=won, reward=energy won/lost)
        """
        if event.success:
            # Won poker game
            self.genome.learned_behaviors['poker_games_won'] += 1

            # Learn from context (hand strength, position, etc.)
            if 'hand_strength' in event.context:
                hand_strength = event.context['hand_strength']
                if hand_strength > 0.7:
                    # Won with strong hand - reinforce aggressive play with good hands
                    self.genome.learned_behaviors['poker_hand_selection'] += self.learning_rate * 0.5
                elif hand_strength < 0.3:
                    # Won with weak hand (bluff success) - slightly increase aggression
                    self.genome.learned_behaviors['poker_aggression_tuning'] += self.learning_rate * 0.3

            if 'position' in event.context:
                position = event.context['position']  # 0=button, 1=off-button
                if position == 0:
                    # Won from button position - learn positional advantage
                    self.genome.learned_behaviors['poker_positional_awareness'] += self.learning_rate * 0.4
        else:
            # Lost poker game
            self.genome.learned_behaviors['poker_games_lost'] += 1

            # Learn from losses
            if 'hand_strength' in event.context:
                hand_strength = event.context['hand_strength']
                if hand_strength < 0.4:
                    # Lost with weak hand - reduce aggression with weak hands
                    self.genome.learned_behaviors['poker_hand_selection'] -= self.learning_rate * 0.3
                    self.genome.learned_behaviors['poker_aggression_tuning'] -= self.learning_rate * 0.2

        # Clamp learned poker behaviors
        for key in ['poker_hand_selection', 'poker_positional_awareness', 'poker_aggression_tuning']:
            self.genome.learned_behaviors[key] = max(
                -self.MAX_LEARNED_ADJUSTMENT,
                min(self.MAX_LEARNED_ADJUSTMENT, self.genome.learned_behaviors[key])
            )

    def _learn_energy_management(self, event: LearningEvent) -> None:
        """Learn from energy management experiences.

        Args:
            event: Energy event (success=maintained energy, reward=efficiency)
        """
        if event.success:
            # Successfully maintained energy - reinforce conservation
            adjustment = self.learning_rate * event.reward
            self.genome.learned_behaviors['energy_conservation'] += adjustment
        else:
            # Energy depletion - learn to conserve more
            adjustment = self.learning_rate * 0.5
            self.genome.learned_behaviors['energy_conservation'] += adjustment

        # Clamp
        self.genome.learned_behaviors['energy_conservation'] = max(
            -self.MAX_LEARNED_ADJUSTMENT,
            min(self.MAX_LEARNED_ADJUSTMENT,
                self.genome.learned_behaviors['energy_conservation'])
        )

    def _learn_spatial_navigation(self, event: LearningEvent) -> None:
        """Learn from spatial navigation experiences.

        Args:
            event: Navigation event (success=reached goal, reward=efficiency)
        """
        if event.success:
            # Successfully navigated - improve spatial memory
            adjustment = self.learning_rate * event.reward
            self.genome.learned_behaviors['spatial_memory_strength'] += adjustment

        # Clamp
        self.genome.learned_behaviors['spatial_memory_strength'] = max(
            -self.MAX_LEARNED_ADJUSTMENT,
            min(self.MAX_LEARNED_ADJUSTMENT,
                self.genome.learned_behaviors['spatial_memory_strength'])
        )

    def apply_decay(self) -> None:
        """Apply decay to learned behaviors (called each frame).

        Learned behaviors gradually fade if not reinforced, preventing
        overfitting to outdated patterns.
        """
        for key in self.genome.learned_behaviors:
            if key.endswith('_finds') or key.endswith('_escapes') or key.endswith('_won') or key.endswith('_lost'):
                # Don't decay counters
                continue

            current_value = self.genome.learned_behaviors[key]
            if current_value > 0:
                self.genome.learned_behaviors[key] = max(0, current_value - self.decay_rate)
            elif current_value < 0:
                self.genome.learned_behaviors[key] = min(0, current_value + self.decay_rate)

    def get_learned_parameter_adjustment(self, parameter_name: str, learning_category: str) -> float:
        """Get the learned adjustment for a behavior algorithm parameter.

        Args:
            parameter_name: Name of the algorithm parameter
            learning_category: Category of learning (e.g., 'food_finding', 'poker')

        Returns:
            Adjustment multiplier to apply to the parameter (-0.3 to +0.3)
        """
        if learning_category == 'food_finding':
            return self.genome.learned_behaviors.get('food_finding_efficiency', 0.0)
        elif learning_category == 'predator_avoidance':
            return self.genome.learned_behaviors.get('predator_escape_skill', 0.0)
        elif learning_category == 'energy_management':
            return self.genome.learned_behaviors.get('energy_conservation', 0.0)
        elif learning_category == 'spatial_navigation':
            return self.genome.learned_behaviors.get('spatial_memory_strength', 0.0)
        else:
            return 0.0

    def get_poker_learned_adjustments(self) -> Dict[str, float]:
        """Get all learned poker strategy adjustments.

        Returns:
            Dictionary of poker-related learned behaviors
        """
        return {
            'hand_selection': self.genome.learned_behaviors.get('poker_hand_selection', 0.0),
            'positional_awareness': self.genome.learned_behaviors.get('poker_positional_awareness', 0.0),
            'aggression_tuning': self.genome.learned_behaviors.get('poker_aggression_tuning', 0.0),
            'games_won': self.genome.learned_behaviors.get('poker_games_won', 0.0),
            'games_lost': self.genome.learned_behaviors.get('poker_games_lost', 0.0),
        }

    @staticmethod
    def inherit_learned_behaviors(parent1: 'Genome', parent2: 'Genome',
                                  offspring: 'Genome') -> None:
        """Transfer some learned behaviors to offspring (cultural evolution).

        This represents cultural transmission of learned strategies,
        where offspring benefit from parents' experience.

        Args:
            parent1: First parent's genome
            parent2: Second parent's genome
            offspring: Offspring's genome to modify
        """
        # Average parents' learned behaviors
        for key in parent1.learned_behaviors:
            if key in parent2.learned_behaviors:
                # Don't inherit counters
                if key.endswith('_finds') or key.endswith('_escapes') or key.endswith('_won') or key.endswith('_lost'):
                    continue

                parent1_val = parent1.learned_behaviors[key]
                parent2_val = parent2.learned_behaviors[key]
                avg_val = (parent1_val + parent2_val) / 2.0

                # Offspring inherits a fraction of parents' learning
                inherited_val = avg_val * BehavioralLearningSystem.CULTURAL_INHERITANCE_RATE
                offspring.learned_behaviors[key] = inherited_val

    def get_learning_summary(self) -> Dict[str, any]:
        """Get a summary of learned behaviors for debugging/display.

        Returns:
            Dictionary with learning statistics
        """
        total_games = (self.genome.learned_behaviors.get('poker_games_won', 0) +
                      self.genome.learned_behaviors.get('poker_games_lost', 0))
        win_rate = (self.genome.learned_behaviors.get('poker_games_won', 0) / total_games
                   if total_games > 0 else 0.0)

        return {
            'food_finding_efficiency': self.genome.learned_behaviors.get('food_finding_efficiency', 0.0),
            'predator_escape_skill': self.genome.learned_behaviors.get('predator_escape_skill', 0.0),
            'energy_conservation': self.genome.learned_behaviors.get('energy_conservation', 0.0),
            'spatial_memory_strength': self.genome.learned_behaviors.get('spatial_memory_strength', 0.0),
            'poker_skill': {
                'hand_selection': self.genome.learned_behaviors.get('poker_hand_selection', 0.0),
                'positional_awareness': self.genome.learned_behaviors.get('poker_positional_awareness', 0.0),
                'aggression_tuning': self.genome.learned_behaviors.get('poker_aggression_tuning', 0.0),
                'games_played': total_games,
                'win_rate': win_rate,
            },
            'successful_food_finds': self.genome.learned_behaviors.get('successful_food_finds', 0),
            'successful_predator_escapes': self.genome.learned_behaviors.get('successful_predator_escapes', 0),
        }
