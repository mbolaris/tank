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
        "Use identity provider instead.\n\nViolations:\n"
        + "\n".join(violations)
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
    assert "_get_entity_identity" in function_body, (
        "_apply_entity_mutations should use _get_entity_identity() for stable identity"
    )


def _check_function_for_fish_only_patterns(func_node, source_lines, func_name):
    """Helper to verify a function doesn't use fish-only patterns."""
    forbidden_patterns = ["fish_id", "get_fish_list", "Fish"]
    allowed_patterns = ["FISH_ID_OFFSET"]  # Offset constants are OK for ID translation
    
    start_line = func_node.lineno - 1
    end_line = func_node.end_lineno
    func_body = "\n".join(source_lines[start_line:end_line])
    
    violations = []
    for pattern in forbidden_patterns:
        if pattern in func_body:
            # Check if it's in an allowed context
            skip = False
            for allowed in allowed_patterns:
                if allowed in func_body and pattern in allowed:
                    skip = True
                    break
            if not skip:
                violations.append(f"Found '{pattern}' in {func_name}")
    
    return violations


def test_resolve_energy_does_not_use_fish_only_patterns():
    """Verify _resolve_energy doesn't build fish-only entity maps."""
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

    # Find _resolve_energy
    resolve_energy_func = None
    for node in ast.walk(simulation_engine_class):
        if isinstance(node, ast.FunctionDef) and node.name == "_resolve_energy":
            resolve_energy_func = node
            break

    assert resolve_energy_func is not None, "_resolve_energy not found"

    start_line = resolve_energy_func.lineno - 1
    end_line = resolve_energy_func.end_lineno
    func_body = "\n".join(lines[start_line:end_line])

    # Should NOT contain fish-only mapping pattern
    assert "e.fish_id: e for e in self.get_fish_list()" not in func_body, (
        "_resolve_energy should not build fish-only entity map. "
        "Use identity provider for mode-agnostic lookup."
    )

    # Should use identity provider
    assert "_identity_provider" in func_body, (
        "_resolve_energy should use identity provider for entity lookup"
    )


def test_apply_energy_deltas_does_not_use_fish_only_patterns():
    """Verify _apply_energy_deltas doesn't build fish-only entity maps."""
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

    # Find _apply_energy_deltas
    apply_deltas_func = None
    for node in ast.walk(simulation_engine_class):
        if isinstance(node, ast.FunctionDef) and node.name == "_apply_energy_deltas":
            apply_deltas_func = node
            break

    assert apply_deltas_func is not None, "_apply_energy_deltas not found"

    start_line = apply_deltas_func.lineno - 1
    end_line = apply_deltas_func.end_lineno
    func_body = "\n".join(lines[start_line:end_line])

    # Should NOT contain fish-only mapping pattern
    assert "e.fish_id: e for e in self.get_fish_list()" not in func_body, (
        "_apply_energy_deltas should not build fish-only entity map. "
        "Use identity provider for mode-agnostic lookup."
    )

    # Should use identity provider
    assert "_identity_provider" in func_body, (
        "_apply_energy_deltas should use identity provider for entity lookup"
    )
    
    # Should use get_entity_by_id
    assert "get_entity_by_id" in func_body, (
        "_apply_energy_deltas should use get_entity_by_id for reverse lookup"
    )


def test_energy_delta_functions_avoid_fish_only_identity():
    """Verify energy delta functions avoid fish-only identity assumptions."""
    engine_path = Path(__file__).parent.parent / "core" / "simulation" / "engine.py"
    source = engine_path.read_text(encoding="utf-8")
    lines = source.split("\n")
    tree = ast.parse(source, filename=str(engine_path))

    simulation_engine_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "SimulationEngine":
            simulation_engine_class = node
            break

    assert simulation_engine_class is not None, "SimulationEngine class not found"

    target_funcs = {}
    for node in ast.walk(simulation_engine_class):
        if isinstance(node, ast.FunctionDef) and node.name in {"_resolve_energy", "_apply_energy_deltas"}:
            target_funcs[node.name] = node

    assert "_resolve_energy" in target_funcs, "_resolve_energy not found"
    assert "_apply_energy_deltas" in target_funcs, "_apply_energy_deltas not found"

    violations = []
    for name, func_node in target_funcs.items():
        violations.extend(_check_function_for_fish_only_patterns(func_node, lines, name))

    assert not violations, (
        "Energy delta functions should avoid fish-only identity patterns:\n"
        + "\n".join(violations)
    )
