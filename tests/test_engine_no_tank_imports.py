"""Test that SimulationEngine's delta tracking is mode-agnostic.

This test verifies that _apply_entity_mutations doesn't directly import
Fish, Plant, or other Tank-specific entities for identity resolution.
The phase implementations may still contain mode-specific logic.
"""

import ast
from pathlib import Path


def test_apply_entity_mutations_does_not_import_tank_types():
    """Verify _apply_entity_mutations doesn't import Tank entity types for identity."""
    engine_path = Path(__file__).parent.parent / "core" / "simulation" / "engine.py"
    assert engine_path.exists(), f"engine.py not found at {engine_path}"

    source = engine_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(engine_path))

    # Find the _apply_entity_mutations function
    apply_mutations_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_apply_entity_mutations":
            apply_mutations_func = node
            break

    assert apply_mutations_func is not None, "_apply_entity_mutations not found"

    # Tank-specific entity types that should NOT be imported in _apply_entity_mutations
    forbidden_names = {"Fish", "Plant", "PlantNectar", "Food"}

    violations = []

    for node in ast.walk(apply_mutations_func):
        # Check 'from X import Y' statements within the function
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in forbidden_names:
                    violations.append(
                        f"Forbidden import in _apply_entity_mutations: '{alias.name}' "
                        f"at line {node.lineno}"
                    )
        # Check isinstance calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "isinstance":
                if len(node.args) >= 2:
                    type_arg = node.args[1]
                    if isinstance(type_arg, ast.Name) and type_arg.id in forbidden_names:
                        violations.append(
                            f"isinstance check for '{type_arg.id}' in _apply_entity_mutations "
                            f"at line {node.lineno}"
                        )

    assert not violations, (
        "_apply_entity_mutations contains Tank-specific imports/isinstance checks. "
        "Use identity provider instead.\n\nViolations:\n" + "\n".join(violations)
    )


def test_delta_tracking_uses_identity_provider():
    """Verify _apply_entity_mutations uses identity_provider for entity identity."""
    engine_path = Path(__file__).parent.parent / "core" / "simulation" / "engine.py"
    source = engine_path.read_text(encoding="utf-8")
    lines = source.split("\n")
    tree = ast.parse(source, filename=str(engine_path))

    # Find SimulationEngine class first, then the method within it
    simulation_engine_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "SimulationEngine":
            simulation_engine_class = node
            break

    assert simulation_engine_class is not None, "SimulationEngine class not found"

    # Find _apply_entity_mutations within SimulationEngine
    apply_mutations_func = None
    for node in ast.walk(simulation_engine_class):
        if isinstance(node, ast.FunctionDef) and node.name == "_apply_entity_mutations":
            apply_mutations_func = node
            break

    assert apply_mutations_func is not None, "_apply_entity_mutations not found in SimulationEngine"

    # Get function body using AST line range
    start_line = apply_mutations_func.lineno - 1  # 0-indexed
    end_line = apply_mutations_func.end_lineno  # 1-indexed, exclusive
    function_body = "\n".join(lines[start_line:end_line])

    # Check that the identity helper is used
    assert (
        "_get_entity_identity" in function_body
    ), "_apply_entity_mutations should use _get_entity_identity() for stable identity"


def test_energy_recorder_does_not_use_fish_only_patterns():
    """Verify _create_energy_recorder doesn't use fish-only identity patterns."""
    engine_path = Path(__file__).parent.parent / "core" / "simulation" / "engine.py"
    source = engine_path.read_text(encoding="utf-8")
    lines = source.split("\n")
    tree = ast.parse(source, filename=str(engine_path))

    # Find SimulationEngine class
    simulation_engine_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "SimulationEngine":
            simulation_engine_class = node
            break

    assert simulation_engine_class is not None, "SimulationEngine class not found"

    # Find _create_energy_recorder
    recorder_func = None
    for node in ast.walk(simulation_engine_class):
        if isinstance(node, ast.FunctionDef) and node.name == "_create_energy_recorder":
            recorder_func = node
            break

    assert recorder_func is not None, "_create_energy_recorder not found"

    start_line = recorder_func.lineno - 1
    end_line = recorder_func.end_lineno
    func_body = "\n".join(lines[start_line:end_line])

    # Should NOT contain fish-only identity patterns
    forbidden_patterns = ["fish_id", "plant_id", "get_fish_list"]
    violations = []
    for pattern in forbidden_patterns:
        if pattern in func_body:
            violations.append(f"Found '{pattern}' in _create_energy_recorder")

    assert not violations, (
        "_create_energy_recorder should use identity provider, not fish-only patterns:\n"
        + "\n".join(violations)
    )

    # Should use identity provider
    assert (
        "_get_entity_identity" in func_body
    ), "_create_energy_recorder should use _get_entity_identity for stable IDs"
