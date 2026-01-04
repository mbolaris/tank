"""Architecture boundary tests for world mode packs.

These tests enforce that mode packs maintain clean separation without
coupling through inheritance. This enables new modes like Soccer to be
added without tangled import chains.
"""


def test_petri_pack_is_not_a_tankpack_subclass():
    """PetriPack must not inherit TankPack.

    This test enforces the architecture boundary that allows Petri to
    diverge independently from Tank. Both modes should inherit from a
    neutral shared base (TankLikePackBase) rather than Petri inheriting
    from Tank directly.

    If this test fails, it means someone has reintroduced the inheritance
    coupling that we specifically removed to enable clean mode boundaries.
    """
    from core.worlds.petri.pack import PetriPack
    from core.worlds.tank.pack import TankPack

    assert not issubclass(PetriPack, TankPack), (
        "PetriPack must not inherit TankPack. "
        "Use a neutral shared base (TankLikePackBase) so Petri can diverge cleanly."
    )


def test_tankpack_inherits_from_tank_like_pack_base():
    """TankPack should inherit from the neutral shared base."""
    from core.worlds.shared.tank_like_pack_base import TankLikePackBase
    from core.worlds.tank.pack import TankPack

    assert issubclass(TankPack, TankLikePackBase), "TankPack should inherit from TankLikePackBase"


def test_petripack_inherits_from_tank_like_pack_base():
    """PetriPack should inherit from the neutral shared base."""
    from core.worlds.petri.pack import PetriPack
    from core.worlds.shared.tank_like_pack_base import TankLikePackBase

    assert issubclass(PetriPack, TankLikePackBase), "PetriPack should inherit from TankLikePackBase"


def test_petripack_does_not_import_tankpack_module():
    """Verify PetriPack module has no Tank pack imports.

    This is a stricter check than just subclass - we want no import
    chains at all from Petri pack to Tank pack.
    """
    import ast
    import inspect

    from core.worlds.petri import pack as petri_pack_module

    source = inspect.getsource(petri_pack_module)
    tree = ast.parse(source)

    tank_imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "tank.pack" in alias.name or "tank" in alias.name.split(".")[-1]:
                    # Allow tank.identity import (shared identity provider for now)
                    if "identity" not in alias.name:
                        tank_imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            # Check for imports from tank.pack
            if "worlds.tank.pack" in module:
                tank_imports.append(f"from {module}")

    assert (
        not tank_imports
    ), f"PetriPack module should not import TankPack module. Found: {tank_imports}"
