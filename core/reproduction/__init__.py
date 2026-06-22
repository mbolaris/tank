"""Reproduction subsystem.

Groups the reproduction service (offspring creation, energy transfer,
emergency spawns), the per-frame reproduction system, and reproduction
statistics. Import the concrete submodule directly (e.g.
``from core.reproduction.reproduction_service import ReproductionService``);
this package does not re-export, keeping the module-load graph acyclic
(see ADR-008).
"""
