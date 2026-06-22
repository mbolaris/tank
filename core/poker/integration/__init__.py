"""Tank-integration layer for the poker engine.

These modules wire the pure poker engine (``core.poker.core`` /
``core.poker.simulation`` / ``core.poker.strategy``) into the live tank
simulation: pairing eligible fish, running games as part of the interaction
phase, and planning multi-seat tables.

Import the concrete submodule directly (e.g.
``from core.poker.integration.poker_system import PokerSystem``). This package
intentionally does not re-export, to keep it out of the ``core.poker`` facade
load chain (see ADR-008).
"""
