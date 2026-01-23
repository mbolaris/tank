"""Guard test to prevent concrete entity imports from creeping back into infrastructure code.

This test ensures that backend and shared world modules remain decoupled from concrete
entity types (Fish, Plant, Food, etc.) by checking for disallowed import patterns.

The goal is to keep infrastructure code generic, using snapshot_type and capability
checks instead of isinstance() with concrete entity classes.
"""

import re
from pathlib import Path

import pytest

# Files that should NOT have runtime imports of concrete entity classes
# TYPE_CHECKING imports are acceptable for type hints
INFRA_FILES = [
    "backend/simulation_runner.py",
    "backend/world_persistence.py",
    "backend/routers/solutions.py",
    "backend/routers/worlds.py",
    "backend/runner/commands/poker.py",
    "backend/runner/commands/soccer.py",
    "backend/runner/commands/benchmark.py",
    "backend/runner/hooks/tank_hooks.py",
    "backend/runner/hooks/poker_mixin.py",
    "backend/snapshots/tank_snapshot_builder.py",
    "core/worlds/shared/tank_like_phase_hooks.py",
    "core/worlds/shared/movement_observations.py",
]

# Disallowed import patterns (runtime imports of concrete entity classes)
# Note: TYPE_CHECKING imports are allowed, so we look for imports outside of that block
DISALLOWED_PATTERNS = [
    # Direct imports of concrete entity classes (not inside TYPE_CHECKING)
    r"^from core\.entities import (?:Fish|Plant)\b",
    r"^from core\.entities\.fish import Fish\b",
    r"^from core\.entities\.plant import (?:Plant|PlantNectar)\b",
    # Note: Food imports are sometimes needed for instantiation (e.g., world_persistence)
    # Ball and GoalZone are allowed if needed for instantiation in soccer setup
]

# These patterns indicate isinstance checks with concrete types that should use snapshot_type
DISCOURAGED_ISINSTANCE_PATTERNS = [
    r"isinstance\([^,]+,\s*Fish\)",
    r"isinstance\([^,]+,\s*Plant\)",
    r"isinstance\([^,]+,\s*PlantNectar\)",
]


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def is_inside_type_checking_block(content: str, match_pos: int) -> bool:
    """Check if the match position is inside a TYPE_CHECKING block.

    This is a heuristic check that looks for 'if TYPE_CHECKING:' before the match
    and checks if the indentation suggests we're inside that block.
    """
    lines_before = content[:match_pos].split('\n')

    # Look backwards for TYPE_CHECKING block
    in_type_checking = False
    for line in reversed(lines_before):
        stripped = line.strip()
        if stripped.startswith('if TYPE_CHECKING:'):
            in_type_checking = True
            break
        # If we hit a non-indented line (class, def, etc.), we're outside any block
        if stripped and not line.startswith(' ') and not line.startswith('\t'):
            if not stripped.startswith('#'):
                break

    return in_type_checking


@pytest.mark.parametrize("file_path", INFRA_FILES)
def test_no_disallowed_imports(file_path: str) -> None:
    """Test that infrastructure files don't have disallowed concrete entity imports."""
    full_path = get_project_root() / file_path

    if not full_path.exists():
        pytest.skip(f"File not found: {file_path}")

    content = full_path.read_text()
    lines = content.split('\n')

    violations = []

    for line_num, line in enumerate(lines, 1):
        # Skip TYPE_CHECKING blocks
        if 'TYPE_CHECKING' in line:
            continue

        for pattern in DISALLOWED_PATTERNS:
            if re.search(pattern, line):
                # Check if this line is inside a TYPE_CHECKING block
                match_pos = content.find(line)
                if not is_inside_type_checking_block(content, match_pos):
                    violations.append(f"  Line {line_num}: {line.strip()}")

    if violations:
        pytest.fail(
            f"Found disallowed concrete entity imports in {file_path}:\n"
            + "\n".join(violations)
            + "\n\nUse snapshot_type checks instead of isinstance() with concrete types."
        )


@pytest.mark.parametrize("file_path", INFRA_FILES)
def test_no_isinstance_with_concrete_types(file_path: str) -> None:
    """Test that infrastructure files don't use isinstance() with concrete entity types."""
    full_path = get_project_root() / file_path

    if not full_path.exists():
        pytest.skip(f"File not found: {file_path}")

    content = full_path.read_text()
    lines = content.split('\n')

    violations = []

    for line_num, line in enumerate(lines, 1):
        for pattern in DISCOURAGED_ISINSTANCE_PATTERNS:
            if re.search(pattern, line):
                violations.append(f"  Line {line_num}: {line.strip()}")

    if violations:
        pytest.fail(
            f"Found isinstance() with concrete entity types in {file_path}:\n"
            + "\n".join(violations)
            + "\n\nUse getattr(entity, 'snapshot_type', None) == 'type_name' instead."
        )


def test_snapshot_type_exists_on_all_entity_classes() -> None:
    """Verify that all major entity classes have snapshot_type property defined."""
    from core.entities import Fish, Food, Plant
    from core.entities.ball import Ball
    from core.entities.base import Castle
    from core.entities.goal_zone import GoalZone
    from core.entities.plant import PlantNectar

    # These are the expected snapshot_type values for each class
    expected_types = {
        Fish: "fish",
        Plant: "plant",
        PlantNectar: "plant_nectar",
        Food: "food",
        Ball: "ball",
        GoalZone: "goal_zone",
        Castle: "castle",
    }

    for entity_class, expected_type in expected_types.items():
        # Check that snapshot_type is a property
        assert hasattr(entity_class, 'snapshot_type'), \
            f"{entity_class.__name__} missing snapshot_type property"

        # For classes with @property, we can't easily check the return value
        # without instantiating. The property descriptor check is sufficient.
        prop = getattr(entity_class, 'snapshot_type', None)
        assert isinstance(prop, property), \
            f"{entity_class.__name__}.snapshot_type should be a @property"
