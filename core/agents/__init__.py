"""Agent components package.

Contains shared agent implementations and the components they compose.
"""

from core.agents.components import (FeedingComponent, LifecycleComponent,
                                    LocomotionComponent, PerceptionComponent,
                                    ReproductionComponent)

__all__ = [
    "FeedingComponent",
    "LifecycleComponent",
    "LocomotionComponent",
    "PerceptionComponent",
    "ReproductionComponent",
]
