"""Architecture guard ensuring energy mutations use modify_energy."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_DIR = ROOT / "core"

ALLOWLIST_PATHS = {
    Path("core/entities/fish.py"),
    Path("core/entities/plant.py"),
    Path("core/entities/generic_agent.py"),
    Path("core/entities/predators.py"),
    Path("core/energy/energy_component.py"),
    Path("core/plant/energy_component.py"),
    Path("core/minigames/soccer/league_runtime.py"),
    Path("core/transfer/entity_transfer.py"),
    # energy_utils.py is the centralized energy mutation utility. Its direct
    # assignment fallback (allow_direct_assignment=True) is intentional for
    # entities that don't implement modify_energy() (e.g. Food, poker PlayerState).
    # All other code should use apply_energy_delta() rather than direct assignment.
    Path("core/energy/energy_utils.py"),
}


class _EnergyAssignmentVisitor(ast.NodeVisitor):
    def __init__(self, source_lines: list[str]) -> None:
        self.source_lines = source_lines
        self.matches: list[tuple[int, str]] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._maybe_record(target, node.lineno)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._maybe_record(node.target, node.lineno)
        self.generic_visit(node)

    def _maybe_record(self, target: ast.expr, lineno: int) -> None:
        if isinstance(target, ast.Attribute) and target.attr == "energy":
            line = (
                self.source_lines[lineno - 1].strip()
                if 0 <= lineno - 1 < len(self.source_lines)
                else ""
            )
            self.matches.append((lineno, line))


def test_energy_changes_use_modify_energy() -> None:
    """Direct energy writes outside approved files should not exist."""
    violations: list[tuple[Path, int, str]] = []

    for path in CORE_DIR.rglob("*.py"):
        rel_path = path.relative_to(ROOT)
        if rel_path in ALLOWLIST_PATHS:
            continue

        source = path.read_text(encoding="utf-8")
        visitor = _EnergyAssignmentVisitor(source.splitlines())
        visitor.visit(ast.parse(source, filename=str(rel_path)))

        for lineno, line in visitor.matches:
            violations.append((rel_path, lineno, line))

    assert not violations, (
        "Energy mutations must go through modify_energy (or apply_energy_delta)."
        " Found direct assignments:\n"
        + "\n".join(f"- {path}:{lineno}: {line}" for path, lineno, line in violations)
    )
