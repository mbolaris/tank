"""Alias for Tank identity provider.

The canonical implementation now lives in core.worlds.shared.identity.
This module re-exports for existing code.
"""

from core.worlds.shared.identity import TankEntityIdentityProvider, TankLikeEntityIdentityProvider

__all__ = ["TankEntityIdentityProvider", "TankLikeEntityIdentityProvider"]
