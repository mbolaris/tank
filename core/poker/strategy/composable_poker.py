"""Composable poker strategy system.

This module provides a composable approach to poker strategies where the genome
encodes selections from multiple sub-behavior categories plus continuous parameters.

Instead of 10 monolithic strategies (TAG, LAG, etc.), behaviors are composed from:
- HandSelection: How tight/loose to play (4 options)
- BettingStyle: How to size bets (4 options)
- BluffingApproach: When and how to bluff (4 options)
- PositionAwareness: How position affects play (3 options)
- ShowdownTendency: How to handle contested pots (3 options)

This gives 4 × 4 × 4 × 3 × 3 = 576 strategy combinations, each with tunable
continuous parameters - enabling much richer evolutionary exploration.

The design mirrors ComposableBehavior for fish movement, using:
- Mendelian inheritance for discrete sub-behavior choices
- Blended inheritance for continuous parameters
"""

import random
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple

from core.poker.betting.actions import BettingAction


# =============================================================================
# Sub-behavior Enums - Each category has discrete options
# =============================================================================


class HandSelection(IntEnum):
    """How tight/loose to play pre-flop."""

    ULTRA_TIGHT = 0   # Only premium hands (AA, KK, QQ, AK) - ~5% of hands
    TIGHT = 1         # Strong hands - ~15% of hands
    BALANCED = 2      # Standard range - ~25% of hands
    LOOSE = 3         # Wide range - ~50% of hands


class BettingStyle(IntEnum):
    """How to size bets and raises."""

    SMALL_BALL = 0     # Small bets, pot control, minimize risk
    VALUE_HEAVY = 1    # Big bets with strong hands, extract value
    POLARIZED = 2      # Either big or check, rarely medium (GTO-like)
    POT_GEOMETRIC = 3  # Mathematical pot-ratio sizing for SPR


class BluffingApproach(IntEnum):
    """When and how to bluff."""

    NEVER_BLUFF = 0      # Only bet with made hands (exploitable but safe)
    OCCASIONAL = 1       # Low frequency, calculated bluffs
    BALANCED = 2         # GTO-inspired bluff-to-value ratio
    AGGRESSIVE = 3       # Frequent bluffs, apply maximum pressure


class PositionAwareness(IntEnum):
    """How much position affects strategic decisions."""

    IGNORE = 0           # Same play regardless of position
    SLIGHT_ADJUSTMENT = 1 # Minor adjustments (+5-10% range IP)
    HEAVY_EXPLOIT = 2    # Major strategy shift by position (+20%+ range IP)


class ShowdownTendency(IntEnum):
    """How to handle contested pots at showdown."""

    FOLD_EASILY = 0      # Give up with medium hands, avoid close spots
    CALL_STATION = 1     # Call down liberally, catch bluffs
    AGGRESSIVE_DENY = 2  # Raise or fold, rarely call (polarized response)


# Category counts for inheritance bounds
SUB_BEHAVIOR_COUNTS = {
    "hand_selection": len(HandSelection),
    "betting_style": len(BettingStyle),
    "bluffing_approach": len(BluffingApproach),
    "position_awareness": len(PositionAwareness),
    "showdown_tendency": len(ShowdownTendency),
}


# =============================================================================
# Sub-behavior Parameter Bounds
# =============================================================================

POKER_SUB_BEHAVIOR_PARAMS = {
    # Hand selection thresholds
    "premium_threshold": (0.75, 0.95),      # Minimum strength for premium play
    "playable_threshold": (0.20, 0.55),     # Minimum strength to enter pot
    "position_range_expand": (0.05, 0.20),  # How much position widens range

    # Betting parameters
    "value_bet_sizing": (0.4, 1.2),         # Pot fraction for value bets
    "bluff_sizing": (0.3, 0.9),             # Pot fraction for bluffs
    "continuation_bet_freq": (0.4, 0.85),   # C-bet frequency

    # Bluffing parameters
    "bluff_frequency": (0.05, 0.45),        # Base bluff rate
    "semibluff_threshold": (0.15, 0.40),    # Hand strength for semibluffs

    # Position parameters
    "ip_aggression_boost": (0.05, 0.30),    # Extra aggression in position
    "oop_tightening": (0.05, 0.25),         # How much tighter OOP

    # Pot odds and risk
    "pot_odds_sensitivity": (0.8, 1.6),     # How strictly to follow pot odds
    "risk_tolerance": (0.15, 0.55),         # Energy fraction willing to risk
    "desperation_threshold": (0.12, 0.35),  # Energy ratio triggering desperate play

    # Opponent modeling weights
    "opponent_model_weight": (0.0, 0.5),    # How much to adjust based on opponent history
}


def _random_params(rng: random.Random) -> Dict[str, float]:
    """Generate random parameters within bounds."""
    return {key: rng.uniform(low, high) for key, (low, high) in POKER_SUB_BEHAVIOR_PARAMS.items()}


# =============================================================================
# CFR Learning Constants
# =============================================================================

# Action space for CFR learning (4 actions as approved)
CFR_ACTIONS = ("fold", "call", "raise_small", "raise_big")

# Inheritance decay for Lamarckian learning (80% as approved)
CFR_INHERITANCE_DECAY = 0.80

# Maximum number of info sets to track (memory cap)
CFR_MAX_INFO_SETS = 100

# Minimum visits before an info set is inheritable
CFR_MIN_VISITS_FOR_INHERITANCE = 3

# Info set discretization buckets
CFR_HAND_STRENGTH_BUCKETS = 5  # 0-4: trash, weak, medium, strong, monster
CFR_POT_RATIO_BUCKETS = 5      # 0-4: tiny, small, medium, large, huge


def _blend_regret_tables(
    table1: Dict[str, Dict[str, float]],
    table2: Dict[str, Dict[str, float]],
    weight1: float,
    decay: float,
    min_visits: int,
    visit_count1: Dict[str, int],
    visit_count2: Dict[str, int],
) -> Dict[str, Dict[str, float]]:
    """Blend two regret/strategy_sum tables with weighting and decay.

    This implements Lamarckian inheritance for learned poker knowledge.
    Only info sets with sufficient visits are inherited.

    Args:
        table1: First parent's regret table
        table2: Second parent's regret table
        weight1: Weight for parent1 (0.0-1.0)
        decay: Decay factor (0.8 = offspring gets 80% of parent knowledge)
        min_visits: Minimum visits for an info set to be inherited
        visit_count1: Parent 1's visit counts
        visit_count2: Parent 2's visit counts

    Returns:
        Blended and decayed regret table
    """
    blended: Dict[str, Dict[str, float]] = {}

    # Collect all info sets from both parents that meet minimum visits
    all_info_sets = set()
    for k in table1:
        if visit_count1.get(k, 0) >= min_visits:
            all_info_sets.add(k)
    for k in table2:
        if visit_count2.get(k, 0) >= min_visits:
            all_info_sets.add(k)

    for info_set in all_info_sets:
        actions1 = table1.get(info_set, {})
        actions2 = table2.get(info_set, {})
        all_actions = set(actions1.keys()) | set(actions2.keys())

        blended[info_set] = {}
        for action in all_actions:
            val1 = actions1.get(action, 0.0)
            val2 = actions2.get(action, 0.0)
            # Weighted blend with decay
            blended_val = (val1 * weight1 + val2 * (1 - weight1)) * decay
            blended[info_set][action] = blended_val

    return blended


# =============================================================================
# Opponent Model - Simple tracking of opponent tendencies
# =============================================================================


@dataclass
class SimpleOpponentModel:
    """Lightweight opponent tracking for composable strategy."""

    opponent_id: str = ""
    games_played: int = 0
    times_folded: int = 0
    times_raised: int = 0
    times_called: int = 0
    total_aggression: float = 0.0

    def update(self, folded: bool, raised: bool, called: bool, aggression: float) -> None:
        """Update model based on observed action."""
        self.games_played += 1
        if folded:
            self.times_folded += 1
        if raised:
            self.times_raised += 1
        if called:
            self.times_called += 1
        self.total_aggression += aggression

    @property
    def fold_rate(self) -> float:
        """Estimated fold frequency."""
        return self.times_folded / max(1, self.games_played)

    @property
    def aggression_factor(self) -> float:
        """Average aggression (raise frequency relative to call)."""
        if self.times_called == 0:
            return 1.0
        return self.times_raised / max(1, self.times_called)

    @property
    def avg_aggression(self) -> float:
        """Average reported aggression level."""
        return self.total_aggression / max(1, self.games_played)


# =============================================================================
# ComposablePokerStrategy Class
# =============================================================================


@dataclass
class ComposablePokerStrategy:
    """A poker strategy composed of multiple sub-behavior selections plus parameters.

    This replaces monolithic strategies (TAG, LAG, etc.) with a composable structure
    that allows evolution to mix and match sub-behaviors while tuning parameters.

    Attributes:
        hand_selection: How tight/loose to play
        betting_style: How to size bets
        bluffing_approach: When and how to bluff
        position_awareness: How position affects play
        showdown_tendency: How to handle contested pots
        parameters: Continuous parameters that tune sub-behavior execution
        opponent_models: Tracked opponent tendencies (optional)
    """

    strategy_id: str = "composable"
    hand_selection: HandSelection = HandSelection.BALANCED
    betting_style: BettingStyle = BettingStyle.VALUE_HEAVY
    bluffing_approach: BluffingApproach = BluffingApproach.OCCASIONAL
    position_awareness: PositionAwareness = PositionAwareness.SLIGHT_ADJUSTMENT
    showdown_tendency: ShowdownTendency = ShowdownTendency.CALL_STATION
    parameters: Dict[str, float] = field(default_factory=dict)
    opponent_models: Dict[str, SimpleOpponentModel] = field(default_factory=dict, repr=False)

    # CFR Learning State (Lamarckian-inheritable)
    # regret[info_set][action] = cumulative regret for that action
    regret: Dict[str, Dict[str, float]] = field(default_factory=dict, repr=False)
    # strategy_sum[info_set][action] = cumulative strategy for averaging
    strategy_sum: Dict[str, Dict[str, float]] = field(default_factory=dict, repr=False)
    # visit_count[info_set] = how many times we've visited this info set
    visit_count: Dict[str, int] = field(default_factory=dict, repr=False)
    # Learning rate for regret accumulation (can evolve)
    learning_rate: float = 1.0

    def __post_init__(self):
        """Initialize default parameters if not provided."""
        if not self.parameters:
            self.parameters = {
                key: (low + high) / 2 for key, (low, high) in POKER_SUB_BEHAVIOR_PARAMS.items()
            }

    @classmethod
    def create_random(cls, rng: Optional[random.Random] = None) -> "ComposablePokerStrategy":
        """Create a random composable poker strategy."""
        rng = rng or random.Random()
        return cls(
            hand_selection=HandSelection(rng.randint(0, len(HandSelection) - 1)),
            betting_style=BettingStyle(rng.randint(0, len(BettingStyle) - 1)),
            bluffing_approach=BluffingApproach(rng.randint(0, len(BluffingApproach) - 1)),
            position_awareness=PositionAwareness(rng.randint(0, len(PositionAwareness) - 1)),
            showdown_tendency=ShowdownTendency(rng.randint(0, len(ShowdownTendency) - 1)),
            parameters=_random_params(rng),
        )

    # Alias for consistency with other strategy classes
    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None) -> "ComposablePokerStrategy":
        """Create a random instance (alias for create_random)."""
        return cls.create_random(rng)

    # -------------------------------------------------------------------------
    # Main Decision Method
    # -------------------------------------------------------------------------

    def decide_action(
        self,
        hand_strength: float,  # 0.0-1.0 normalized
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
        opponent_id: Optional[str] = None,
        rng: Optional[random.Random] = None,
    ) -> Tuple[BettingAction, float]:
        """Make betting decision based on composed sub-behaviors.

        Args:
            hand_strength: Normalized hand strength (0.0-1.0)
            current_bet: Our current bet this round
            opponent_bet: Opponent's current bet
            pot: Total pot size
            player_energy: Our available energy for betting
            position_on_button: Whether we're in position (on button)
            opponent_id: Optional opponent ID for model lookup
            rng: Optional random number generator for deterministic decisions

        Returns:
            Tuple of (action, amount)
        """
        # Use provided RNG or create a fallback for backward compatibility
        _rng = rng if rng is not None else random.Random()
        call_amount = max(0, opponent_bet - current_bet)

        # Can't call if insufficient energy
        if call_amount > player_energy:
            return (BettingAction.FOLD, 0.0)

        # Premium hands should always raise when facing a bet
        # Check this BEFORE position adjustment to avoid missing premium hands OOP
        premium_threshold = self.parameters.get("premium_threshold", 0.80)
        if hand_strength >= premium_threshold and opponent_bet > current_bet:
            sizing = self._calculate_bet_sizing(hand_strength, pot, player_energy, call_amount)
            return (BettingAction.RAISE, sizing)

        # Get opponent adjustments if available
        opponent_adjustment = self._get_opponent_adjustment(opponent_id)

        # Apply position awareness
        adjusted_strength = self._apply_position_adjustment(hand_strength, position_on_button)

        # Check desperation mode
        energy_ratio = player_energy / max(1.0, player_energy + pot)
        is_desperate = energy_ratio < self.parameters.get("desperation_threshold", 0.2)

        # Step 1: Should we even play this hand?
        if not self._should_play_hand(adjusted_strength, position_on_button, is_desperate):
            return self._fold_or_check(call_amount)

        # Step 2: Should we bet/raise?
        if self._should_bet_or_raise(
            adjusted_strength, pot, player_energy, call_amount, is_desperate, opponent_adjustment, _rng
        ):
            sizing = self._calculate_bet_sizing(adjusted_strength, pot, player_energy, call_amount)
            return (BettingAction.RAISE, sizing)

        # Step 3: Call or fold based on showdown tendency
        return self._call_or_fold(adjusted_strength, call_amount, pot, player_energy, opponent_adjustment, _rng)

    # -------------------------------------------------------------------------
    # Sub-behavior Execution Methods
    # -------------------------------------------------------------------------

    def _should_play_hand(
        self, strength: float, position_on_button: bool, is_desperate: bool
    ) -> bool:
        """Determine if hand is playable based on hand_selection."""
        playable = self.parameters.get("playable_threshold", 0.35)

        # Adjust threshold based on hand selection style
        if self.hand_selection == HandSelection.ULTRA_TIGHT:
            threshold = 0.75  # Only premiums
        elif self.hand_selection == HandSelection.TIGHT:
            threshold = playable + 0.15
        elif self.hand_selection == HandSelection.BALANCED:
            threshold = playable
        else:  # LOOSE
            threshold = playable - 0.15

        # Position bonus
        if position_on_button:
            threshold -= self.parameters.get("position_range_expand", 0.10)

        # Desperation makes us looser
        if is_desperate:
            threshold -= 0.15

        return strength >= max(0.05, threshold)

    def _apply_position_adjustment(self, strength: float, position_on_button: bool) -> float:
        """Apply position-based strength adjustment."""
        if self.position_awareness == PositionAwareness.IGNORE:
            return strength

        if position_on_button:
            boost = self.parameters.get("ip_aggression_boost", 0.10)
            if self.position_awareness == PositionAwareness.HEAVY_EXPLOIT:
                boost *= 1.5
            return min(1.0, strength + boost)
        else:
            tightening = self.parameters.get("oop_tightening", 0.10)
            if self.position_awareness == PositionAwareness.HEAVY_EXPLOIT:
                tightening *= 1.5
            return max(0.0, strength - tightening)

    def _should_bet_or_raise(
        self,
        strength: float,
        pot: float,
        energy: float,
        call_amount: float,
        is_desperate: bool,
        opponent_adj: float,
        rng: random.Random,
    ) -> bool:
        """Decide whether to bet or raise."""
        premium_threshold = self.parameters.get("premium_threshold", 0.80)
        bluff_freq = self.parameters.get("bluff_frequency", 0.15)

        # Always bet premium hands
        if strength >= premium_threshold:
            return True

        # Check bluffing approach (use provided RNG for determinism)
        should_bluff = False
        if self.bluffing_approach == BluffingApproach.NEVER_BLUFF:
            should_bluff = False
        elif self.bluffing_approach == BluffingApproach.OCCASIONAL:
            should_bluff = rng.random() < bluff_freq * 0.5
        elif self.bluffing_approach == BluffingApproach.BALANCED:
            # Bluff more when opponent folds often
            adjusted_freq = bluff_freq + opponent_adj * 0.1
            should_bluff = rng.random() < adjusted_freq
        else:  # AGGRESSIVE
            should_bluff = rng.random() < bluff_freq * 1.5

        # Semi-bluff with draws
        semibluff_threshold = self.parameters.get("semibluff_threshold", 0.25)
        if strength >= semibluff_threshold and should_bluff:
            return True

        # Strong but not premium - sometimes raise for value
        if strength >= 0.55:
            if self.betting_style == BettingStyle.VALUE_HEAVY:
                return rng.random() < 0.7
            elif self.betting_style == BettingStyle.POLARIZED:
                # Polarized: raise strong, check medium
                return strength >= 0.70
            else:
                return rng.random() < 0.4

        return should_bluff

    def _calculate_bet_sizing(
        self, strength: float, pot: float, energy: float, call_amount: float
    ) -> float:
        """Calculate bet size based on betting_style."""
        premium_threshold = self.parameters.get("premium_threshold", 0.80)
        value_sizing = self.parameters.get("value_bet_sizing", 0.70)
        bluff_sizing = self.parameters.get("bluff_sizing", 0.50)
        risk_tolerance = self.parameters.get("risk_tolerance", 0.35)

        is_value_bet = strength >= 0.55
        base_sizing = value_sizing if is_value_bet else bluff_sizing

        if self.betting_style == BettingStyle.SMALL_BALL:
            sizing = pot * base_sizing * 0.5
        elif self.betting_style == BettingStyle.VALUE_HEAVY:
            sizing = pot * base_sizing * (1.2 if is_value_bet else 0.7)
        elif self.betting_style == BettingStyle.POLARIZED:
            # Either big or small, rarely medium
            if strength >= premium_threshold:
                sizing = pot * 1.2  # Big with monsters
            elif is_value_bet:
                sizing = pot * 0.33  # Small probe
            else:
                sizing = pot * 0.75  # Standard bluff
        else:  # POT_GEOMETRIC
            # SPR-aware sizing
            spr = energy / max(0.1, pot)
            if spr > 3:
                sizing = pot * 0.66  # Deep - smaller bets
            else:
                sizing = pot * 1.0  # Short - pot-sized

        # Cap by risk tolerance
        max_bet = energy * risk_tolerance
        sizing = min(sizing, max_bet)

        # Ensure minimum meaningful raise
        min_raise = max(call_amount * 1.5, 10.0)
        sizing = max(sizing, min_raise)

        return sizing

    def _call_or_fold(
        self,
        strength: float,
        call_amount: float,
        pot: float,
        energy: float,
        opponent_adj: float,
        rng: random.Random,
    ) -> Tuple[BettingAction, float]:
        """Decide whether to call or fold based on showdown_tendency."""
        if call_amount <= 0:
            return (BettingAction.CHECK, 0.0)

        # Calculate pot odds
        pot_odds = call_amount / (pot + call_amount) if (pot + call_amount) > 0 else 1.0
        sensitivity = self.parameters.get("pot_odds_sensitivity", 1.1)

        # Required equity to call
        required_equity = pot_odds * sensitivity

        if self.showdown_tendency == ShowdownTendency.FOLD_EASILY:
            # Need extra equity margin to call
            required_equity *= 1.3
            if strength >= required_equity:
                return (BettingAction.CALL, call_amount)
            return (BettingAction.FOLD, 0.0)

        elif self.showdown_tendency == ShowdownTendency.CALL_STATION:
            # Lower threshold, will call light
            required_equity *= 0.7
            if strength >= required_equity:
                return (BettingAction.CALL, call_amount)
            # Even below threshold, sometimes call (use provided RNG)
            if rng.random() < 0.25:
                return (BettingAction.CALL, call_amount)
            return (BettingAction.FOLD, 0.0)

        else:  # AGGRESSIVE_DENY
            # Rarely call - either raise or fold
            # (This branch represents the "raise" case, but we're in call_or_fold)
            # So we fold more often
            if strength >= required_equity * 1.5:
                return (BettingAction.CALL, call_amount)
            return (BettingAction.FOLD, 0.0)

    def _fold_or_check(self, call_amount: float) -> Tuple[BettingAction, float]:
        """Return appropriate non-play action."""
        if call_amount > 0:
            return (BettingAction.FOLD, 0.0)
        return (BettingAction.CHECK, 0.0)

    def _get_opponent_adjustment(self, opponent_id: Optional[str]) -> float:
        """Get adjustment factor based on opponent history."""
        if not opponent_id or opponent_id not in self.opponent_models:
            return 0.0

        model = self.opponent_models[opponent_id]
        weight = self.parameters.get("opponent_model_weight", 0.2)

        # High fold rate -> we can bluff more
        # Low fold rate -> we should value bet more
        adjustment = (model.fold_rate - 0.33) * weight  # 0.33 is baseline fold rate

        return adjustment

    def update_opponent_model(
        self, opponent_id: str, folded: bool, raised: bool, called: bool, aggression: float
    ) -> None:
        """Update opponent model after observing their action."""
        if opponent_id not in self.opponent_models:
            self.opponent_models[opponent_id] = SimpleOpponentModel(opponent_id=opponent_id)
        self.opponent_models[opponent_id].update(folded, raised, called, aggression)

    # -------------------------------------------------------------------------
    # Mutation Methods
    # -------------------------------------------------------------------------

    def mutate_parameters(
        self,
        mutation_rate: float = 0.12,
        mutation_strength: float = 0.15,
    ) -> None:
        """Mutate parameters for evolution (compatibility with existing interface)."""
        self.mutate(mutation_rate, mutation_strength)

    def mutate(
        self,
        mutation_rate: float = 0.12,
        mutation_strength: float = 0.15,
        sub_behavior_switch_rate: float = 0.05,
        rng: Optional[random.Random] = None,
    ) -> None:
        """Mutate the composable poker strategy.

        Args:
            mutation_rate: Probability of each parameter mutating
            mutation_strength: Magnitude of parameter mutations
            sub_behavior_switch_rate: Probability of switching each sub-behavior
            rng: Random number generator
        """
        rng = rng or random.Random()

        # Mutate sub-behavior selections (discrete)
        if rng.random() < sub_behavior_switch_rate:
            self.hand_selection = HandSelection(rng.randint(0, len(HandSelection) - 1))
        if rng.random() < sub_behavior_switch_rate:
            self.betting_style = BettingStyle(rng.randint(0, len(BettingStyle) - 1))
        if rng.random() < sub_behavior_switch_rate:
            self.bluffing_approach = BluffingApproach(rng.randint(0, len(BluffingApproach) - 1))
        if rng.random() < sub_behavior_switch_rate:
            self.position_awareness = PositionAwareness(rng.randint(0, len(PositionAwareness) - 1))
        if rng.random() < sub_behavior_switch_rate:
            self.showdown_tendency = ShowdownTendency(rng.randint(0, len(ShowdownTendency) - 1))

        # Mutate continuous parameters
        for key, value in list(self.parameters.items()):
            if rng.random() < mutation_rate:
                bounds = POKER_SUB_BEHAVIOR_PARAMS.get(key, (0.0, 1.0))
                span = bounds[1] - bounds[0]
                delta = rng.gauss(0, mutation_strength * span)
                new_value = max(bounds[0], min(bounds[1], value + delta))
                self.parameters[key] = new_value

    # -------------------------------------------------------------------------
    # CFR Learning Methods (Lamarckian-inheritable)
    # -------------------------------------------------------------------------

    def get_info_set(
        self,
        hand_strength: float,
        pot_ratio: float,
        position_on_button: bool,
        street: int = 0,
    ) -> str:
        """Discretize game state into info set key.

        Args:
            hand_strength: Normalized hand strength (0.0-1.0)
            pot_ratio: Pot size relative to player's stack
            position_on_button: Whether we have position
            street: Betting street (0=preflop, 1=flop, etc.)

        Returns:
            String key for regret table lookup
        """
        # Hand strength bucket (0-4)
        hs_bucket = min(CFR_HAND_STRENGTH_BUCKETS - 1, int(hand_strength * CFR_HAND_STRENGTH_BUCKETS))
        # Pot ratio bucket (0-4)
        pr_bucket = min(CFR_POT_RATIO_BUCKETS - 1, int(pot_ratio * CFR_POT_RATIO_BUCKETS / 2))
        # Position
        pos = "IP" if position_on_button else "OOP"
        return f"{hs_bucket}:{pr_bucket}:{pos}:{street}"

    def get_regret_strategy(self, info_set: str) -> Optional[Dict[str, float]]:
        """Get action probabilities from regret matching.

        Returns None if no regret data exists, meaning caller should use
        default composable sub-behavior logic.

        Args:
            info_set: Discretized game state key

        Returns:
            Dict mapping action -> probability, or None for default behavior
        """
        if info_set not in self.regret:
            return None

        raw_regret = self.regret[info_set]
        # Only use positive regret
        positive = {a: max(r, 0.0) for a, r in raw_regret.items()}
        total = sum(positive.values())

        if total <= 0:
            return None  # No positive regret - use defaults

        return {a: r / total for a, r in positive.items()}

    def sample_cfr_action(self, info_set: str, rng: Optional[random.Random] = None) -> Optional[str]:
        """Sample an action from the regret-matched strategy.

        Args:
            info_set: Discretized game state key
            rng: Random number generator

        Returns:
            Action string ("fold", "call", "raise_small", "raise_big") or None
        """
        strategy = self.get_regret_strategy(info_set)
        if strategy is None:
            return None

        rng = rng or random.Random()
        roll = rng.random()
        cumulative = 0.0
        for action, prob in strategy.items():
            cumulative += prob
            if roll < cumulative:
                return action
        return CFR_ACTIONS[-1]  # Fallback

    def update_regret(
        self,
        info_set: str,
        action_taken: str,
        action_values: Dict[str, float],
    ) -> None:
        """Update regret after a hand.

        Args:
            info_set: Discretized game state key
            action_taken: The action we actually took
            action_values: Dict mapping each action -> counterfactual value
        """
        if info_set not in self.regret:
            self.regret[info_set] = {a: 0.0 for a in CFR_ACTIONS}
        if info_set not in self.strategy_sum:
            self.strategy_sum[info_set] = {a: 0.0 for a in CFR_ACTIONS}

        # Update visit count
        self.visit_count[info_set] = self.visit_count.get(info_set, 0) + 1

        # Value we got from the action we took
        value_got = action_values.get(action_taken, 0.0)

        # Update regret for each action
        for action in CFR_ACTIONS:
            action_value = action_values.get(action, 0.0)
            regret_delta = (action_value - value_got) * self.learning_rate
            self.regret[info_set][action] += regret_delta

        # Update strategy sum for averaging
        strategy = self.get_regret_strategy(info_set)
        if strategy:
            for action, prob in strategy.items():
                self.strategy_sum[info_set][action] += prob

        # Prune if we've accumulated too many info sets
        if len(self.regret) > CFR_MAX_INFO_SETS:
            self._prune_info_sets()

    def _prune_info_sets(self) -> None:
        """Remove least-visited info sets to cap memory usage."""
        if len(self.regret) <= CFR_MAX_INFO_SETS // 2:
            return

        # Sort by visit count, keep most visited
        sorted_sets = sorted(
            self.regret.keys(),
            key=lambda k: self.visit_count.get(k, 0),
            reverse=True
        )

        # Keep top half
        keeps = set(sorted_sets[: CFR_MAX_INFO_SETS // 2])

        self.regret = {k: v for k, v in self.regret.items() if k in keeps}
        self.strategy_sum = {k: v for k, v in self.strategy_sum.items() if k in keeps}
        self.visit_count = {k: v for k, v in self.visit_count.items() if k in keeps}

    def get_average_strategy(self, info_set: str) -> Optional[Dict[str, float]]:
        """Get the time-averaged strategy for an info set.

        This is more stable than the regret-matched strategy and better
        for exploitation-resistant play.
        """
        if info_set not in self.strategy_sum:
            return None

        sums = self.strategy_sum[info_set]
        total = sum(sums.values())
        if total <= 0:
            return None
        return {a: s / total for a, s in sums.items()}

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get statistics about learned knowledge."""
        return {
            "info_sets_learned": len(self.regret),
            "total_visits": sum(self.visit_count.values()),
            "learning_rate": self.learning_rate,
        }

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for storage/transmission."""
        # Only include well-visited info sets in serialization
        inheritable_regret = {
            k: v for k, v in self.regret.items()
            if self.visit_count.get(k, 0) >= CFR_MIN_VISITS_FOR_INHERITANCE
        }
        inheritable_strategy_sum = {
            k: v for k, v in self.strategy_sum.items()
            if k in inheritable_regret
        }
        inheritable_visit_count = {
            k: v for k, v in self.visit_count.items()
            if k in inheritable_regret
        }
        
        return {
            "type": "ComposablePokerStrategy",
            "strategy_id": self.strategy_id,
            "hand_selection": int(self.hand_selection),
            "betting_style": int(self.betting_style),
            "bluffing_approach": int(self.bluffing_approach),
            "position_awareness": int(self.position_awareness),
            "showdown_tendency": int(self.showdown_tendency),
            "parameters": dict(self.parameters),
            "learning_rate": self.learning_rate,
            # CFR learned state (Lamarckian-inheritable)
            "regret": inheritable_regret,
            "strategy_sum": inheritable_strategy_sum,
            "visit_count": inheritable_visit_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComposablePokerStrategy":
        """Deserialize from dictionary."""
        return cls(
            strategy_id=data.get("strategy_id", "composable"),
            hand_selection=HandSelection(data.get("hand_selection", 2)),
            betting_style=BettingStyle(data.get("betting_style", 1)),
            bluffing_approach=BluffingApproach(data.get("bluffing_approach", 1)),
            position_awareness=PositionAwareness(data.get("position_awareness", 1)),
            showdown_tendency=ShowdownTendency(data.get("showdown_tendency", 1)),
            parameters=data.get("parameters", {}),
            learning_rate=data.get("learning_rate", 1.0),
            regret=data.get("regret", {}),
            strategy_sum=data.get("strategy_sum", {}),
            visit_count=data.get("visit_count", {}),
        )

    # -------------------------------------------------------------------------
    # Inheritance / Crossover
    # -------------------------------------------------------------------------

    @classmethod
    def from_parents(
        cls,
        parent1: "ComposablePokerStrategy",
        parent2: "ComposablePokerStrategy",
        weight1: float = 0.5,
        mutation_rate: float = 0.10,
        mutation_strength: float = 0.12,
        sub_behavior_switch_rate: float = 0.03,
        rng: Optional[random.Random] = None,
    ) -> "ComposablePokerStrategy":
        """Create offspring by crossing over two parent strategies.

        Sub-behaviors are inherited Mendelian-style (pick one parent).
        Parameters are blended with weighting.

        Args:
            parent1: First parent strategy (often the winner in poker)
            parent2: Second parent strategy
            weight1: Weight for parent1 (0.0-1.0), parent2 gets (1-weight1)
            mutation_rate: Probability of each parameter mutating
            mutation_strength: Magnitude of mutations
            sub_behavior_switch_rate: Extra chance of random sub-behavior switch
            rng: Random number generator
        """
        rng = rng or random.Random()

        # Mendelian inheritance for discrete sub-behaviors
        hand_selection = (
            parent1.hand_selection if rng.random() < weight1 else parent2.hand_selection
        )
        betting_style = (
            parent1.betting_style if rng.random() < weight1 else parent2.betting_style
        )
        bluffing_approach = (
            parent1.bluffing_approach if rng.random() < weight1 else parent2.bluffing_approach
        )
        position_awareness = (
            parent1.position_awareness if rng.random() < weight1 else parent2.position_awareness
        )
        showdown_tendency = (
            parent1.showdown_tendency if rng.random() < weight1 else parent2.showdown_tendency
        )

        # Blend parameters
        all_keys = set(parent1.parameters.keys()) | set(parent2.parameters.keys())
        blended_params = {}
        for key in all_keys:
            default = POKER_SUB_BEHAVIOR_PARAMS.get(key, (0.5, 0.5))
            default_val = (default[0] + default[1]) / 2
            val1 = parent1.parameters.get(key, default_val)
            val2 = parent2.parameters.get(key, default_val)
            blended_params[key] = val1 * weight1 + val2 * (1 - weight1)

        # Lamarckian inheritance: blend and decay regret tables
        inherited_regret = _blend_regret_tables(
            parent1.regret, parent2.regret,
            weight1=weight1,
            decay=CFR_INHERITANCE_DECAY,
            min_visits=CFR_MIN_VISITS_FOR_INHERITANCE,
            visit_count1=parent1.visit_count,
            visit_count2=parent2.visit_count,
        )
        inherited_strategy_sum = _blend_regret_tables(
            parent1.strategy_sum, parent2.strategy_sum,
            weight1=weight1,
            decay=CFR_INHERITANCE_DECAY,
            min_visits=CFR_MIN_VISITS_FOR_INHERITANCE,
            visit_count1=parent1.visit_count,
            visit_count2=parent2.visit_count,
        )
        # Blend learning rates
        inherited_learning_rate = (
            parent1.learning_rate * weight1 + parent2.learning_rate * (1 - weight1)
        )

        # Create offspring with inherited regret
        offspring = cls(
            hand_selection=hand_selection,
            betting_style=betting_style,
            bluffing_approach=bluffing_approach,
            position_awareness=position_awareness,
            showdown_tendency=showdown_tendency,
            parameters=blended_params,
            regret=inherited_regret,
            strategy_sum=inherited_strategy_sum,
            learning_rate=inherited_learning_rate,
        )

        # Apply mutations
        offspring.mutate(
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            sub_behavior_switch_rate=sub_behavior_switch_rate,
            rng=rng,
        )

        return offspring

    def clone_with_mutation(
        self,
        mutation_rate: float = 0.10,
        mutation_strength: float = 0.12,
        sub_behavior_switch_rate: float = 0.05,
        rng: Optional[random.Random] = None,
    ) -> "ComposablePokerStrategy":
        """Create a mutated clone (for asexual reproduction)."""
        rng = rng or random.Random()
        clone = ComposablePokerStrategy(
            hand_selection=self.hand_selection,
            betting_style=self.betting_style,
            bluffing_approach=self.bluffing_approach,
            position_awareness=self.position_awareness,
            showdown_tendency=self.showdown_tendency,
            parameters=dict(self.parameters),
        )
        clone.mutate(
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            sub_behavior_switch_rate=sub_behavior_switch_rate,
            rng=rng,
        )
        return clone

    # -------------------------------------------------------------------------
    # Display / Debug
    # -------------------------------------------------------------------------

    def get_style_description(self) -> str:
        """Get human-readable description of this strategy blend."""
        parts = [
            f"{self.hand_selection.name.replace('_', ' ').title()}",
            f"{self.betting_style.name.replace('_', ' ').title()}",
            f"{self.bluffing_approach.name.replace('_', ' ').title()} Bluffer",
        ]
        return " / ".join(parts)

    def __repr__(self) -> str:
        return (
            f"ComposablePokerStrategy("
            f"hand={self.hand_selection.name}, "
            f"bet={self.betting_style.name}, "
            f"bluff={self.bluffing_approach.name}, "
            f"pos={self.position_awareness.name}, "
            f"showdown={self.showdown_tendency.name})"
        )
