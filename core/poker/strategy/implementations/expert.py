"""Expert-level poker strategies."""

import random
from dataclasses import dataclass
from typing import Optional, Tuple

from core.poker.betting.actions import BettingAction
from core.poker.strategy.implementations.base import PokerStrategyAlgorithm


@dataclass
class GTOExpertStrategy(PokerStrategyAlgorithm):
    """GTO-inspired expert strategy using optimal frequencies and ranges."""

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "__init__")
        super().__init__(
            strategy_id="gto_expert",
            parameters={
                "bluff_efficiency": _rng.uniform(0.9, 1.1),  # How close to optimal bluff freq
                "value_sizing_efficiency": _rng.uniform(0.95, 1.05),
                "defensive_bandwidth": _rng.uniform(0.8, 1.0),  # Minimum defense frequency adherence
                "polarization_factor": _rng.uniform(0.8, 1.2),  # Tendency to polarize ranges
            },
            _rng=_rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
        rng: Optional[random.Random] = None,
    ) -> Tuple[BettingAction, float]:

        call_amount = opponent_bet - current_bet
        if call_amount > player_energy:
            return (BettingAction.FOLD, 0.0)

        # Position adjustment: play tighter out of position, looser in position
        # Being on button gives us informational advantage
        position_bonus = 0.05 if position_on_button else -0.03
        adjusted_strength = min(1.0, max(0.0, hand_strength + position_bonus))

        # 1. Calculate Pot Odds and Minimum Defense Frequency (MDF)
        future_pot = pot + call_amount
        pot_odds = call_amount / future_pot if future_pot > 0 else 0.0

        # If facing a bet, calculate MDF-based defense
        if call_amount > 0:
            # MDF: We must defend enough to prevent opponent auto-profit
            # Required equity is approximately pot odds
            required_equity = pot_odds
            
            # Apply defensive bandwidth (expert may over/under defend slightly)
            defense_threshold = required_equity * self.parameters["defensive_bandwidth"]

            if adjusted_strength >= defense_threshold:
                # Profitable call or raise
                
                # Strong hands: value raise or trap
                if adjusted_strength > 0.85:
                    # More aggressive raising in position
                    raise_freq = 0.75 if position_on_button else 0.6
                    if self._rng.random() < raise_freq:
                        return self._get_value_raise(pot, player_energy, call_amount, adjusted_strength)
                    return (BettingAction.CALL, call_amount)
                
                # Good hands: sometimes raise for value/protection
                if adjusted_strength > 0.7:
                    if self._rng.random() < 0.3:
                        return self._get_value_raise(pot, player_energy, call_amount, adjusted_strength)
                    return (BettingAction.CALL, call_amount)
                
                # Medium strength bluff-catchers: pure call
                return (BettingAction.CALL, call_amount)

            else:
                # Below defense threshold - mostly fold
                # But sometimes bluff-raise with very weak hands (polarized)
                if adjusted_strength < 0.15 and position_on_button:
                    if self._rng.random() < 0.15 * self.parameters["bluff_efficiency"]:
                        # Bluff raise representing strength
                        raise_amt = pot * 2.5
                        raise_amt = min(raise_amt, player_energy * 0.6)
                        return (BettingAction.RAISE, max(raise_amt, call_amount * 3.0))
                return (BettingAction.FOLD, 0.0)

        else:
            # We are the aggressor (or first to act)
            
            # Position affects aggression frequency
            value_threshold = 0.65 if position_on_button else 0.72
            bluff_threshold = 0.25 if position_on_button else 0.20
            
            # Value betting with strong hands
            if adjusted_strength > value_threshold:
                return self._get_value_raise(pot, player_energy, 0, adjusted_strength)
            
            # Bluffing with weak hands (polarized range)
            if adjusted_strength < bluff_threshold:
                # Optimal bluff frequency based on bet sizing
                bluff_freq = 0.45 if position_on_button else 0.35
                bluff_freq *= self.parameters["bluff_efficiency"]
                
                if self._rng.random() < bluff_freq:
                    bet_amt = pot * 0.75
                    bet_amt = min(bet_amt, player_energy * 0.4)
                    return (BettingAction.RAISE, max(bet_amt, 10.0))
            
            # Check middle range
            return (BettingAction.CHECK, 0.0)

    def _get_value_raise(
        self, pot: float, player_energy: float, call_amount: float, hand_strength: float
    ) -> Tuple[BettingAction, float]:
        # Geometric growth of pot?
        # For now, standard sizing
        
        # Bets 75% pot usually, overbets (125%) with nuts
        sizing = 0.75
        if hand_strength > 0.95:
            sizing = 1.25 # Polarized overbet
            
        sizing *= self.parameters["value_sizing_efficiency"]
            
        raise_amt = pot * sizing
        raise_amt = min(raise_amt, player_energy * 0.5) # Don't commit > 50% stack in one go unless all-in
        
        return (BettingAction.RAISE, max(raise_amt, call_amount * 2.0))
