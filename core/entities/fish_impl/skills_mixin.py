"""SkillfulAgent Protocol implementation mixin for Fish."""

from typing import TYPE_CHECKING, Optional

from core.entities.base import LifeStage
from core.skills.base import SkillGameType, SkillStrategy, SkillGameResult

if TYPE_CHECKING:
    from core.fish.skill_game_component import SkillGameComponent
    from core.fish.lifecycle_component import LifecycleComponent


class FishSkillsMixin:
    """Implement the SkillfulAgent protocol for Fish.
    
    Expected attributes on host:
        _skill_game_component: SkillGameComponent
        _lifecycle_component: LifecycleComponent
        energy: float
        poker_cooldown: int
        is_dead: Callable[[], bool]
    """
    
    # Type definition for mixin expectations
    if TYPE_CHECKING:
        _skill_game_component: "SkillGameComponent"
        _lifecycle_component: "LifecycleComponent"
        energy: float
        poker_cooldown: int
        def is_dead(self) -> bool: ...

    def get_strategy(self, game_type: SkillGameType) -> Optional[SkillStrategy]:
        """Get the fish's strategy for a specific skill game (implements SkillfulAgent Protocol).
        
        Args:
            game_type: The type of skill game
            
        Returns:
            The fish's strategy for that game, or None if not initialized
        """
        return self._skill_game_component.get_strategy(game_type)
    
    def set_strategy(self, game_type: SkillGameType, strategy: SkillStrategy) -> None:
        """Set the fish's strategy for a specific skill game (implements SkillfulAgent Protocol).
        
        Args:
            game_type: The type of skill game
            strategy: The strategy to use for that game
        """
        self._skill_game_component.set_strategy(game_type, strategy)
    
    def learn_from_game(self, game_type: SkillGameType, result: SkillGameResult) -> None:
        """Update strategy based on game outcome (implements SkillfulAgent Protocol).
        
        This is how fish learn within their lifetime. The strategy is updated
        based on the result (win/loss/tie) and optimality of play.
        
        Args:
            game_type: The type of skill game that was played
            result: The outcome of the game
        """
        self._skill_game_component.record_game_result(game_type, result)
    
    @property
    def can_play_skill_games(self) -> bool:
        """Whether this fish is currently able to play skill games (implements SkillfulAgent Protocol).
        
        Returns:
            True if fish is adult, has sufficient energy, and isn't on cooldown
        """
        if self._lifecycle_component.life_stage not in (LifeStage.ADULT, LifeStage.ELDER):
            return False
            
        # We perform local import to avoid circular dependencies if they exist,
        # mirroring the original implementation's safety.
        from core.poker_interaction import MIN_ENERGY_TO_PLAY
        
        return (
            self.energy >= MIN_ENERGY_TO_PLAY
            and self.poker_cooldown <= 0
            and not self.is_dead()
        )
