"""Lint-level guard: left/right is the render path, home/away is a label.

SOCCER_ARENA_DESIGN.md §10.4 rule 2 commits to this so RCSS integration stays a
data-source swap. The failure it prevents is specific: once a drawing layer
knows which team is "home", a half swap stops being a label change and becomes
a rendering change, and every layer that guessed has to be found by hand.

These are text checks on purpose. The property is about *which module may know
what*, which no runtime assertion can observe.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RENDER_PATH = ROOT / "frontend" / "src" / "renderers" / "soccer"

# The one designated resolver: it exists to turn a side into a team label, and
# is the only place in the render path allowed to know both vocabularies.
SIDE_RESOLVER = "sideAssignment.ts"

HOME_AWAY = re.compile(r"\b(home_name|away_name|home_id|away_id)\b")
RAW_SWAP_READ = re.compile(r"\.sides_swapped\b|\bsides_swapped\s*[?:]")


def _source_files(directory: Path) -> list[Path]:
    return sorted(path for path in directory.rglob("*.ts") if not path.name.endswith(".test.ts"))


def test_drawing_layers_do_not_know_home_from_away() -> None:
    """Only the resolver may name teams; everything drawn is left/right."""
    violations = []
    for path in _source_files(RENDER_PATH):
        if path.name == SIDE_RESOLVER:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if HOME_AWAY.search(line):
                violations.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")

    assert not violations, (
        "Home/away reached the soccer render path. Sides are left/right there; "
        "resolve the team label through resolveSideAssignment instead:\n  "
        + "\n  ".join(violations)
    )


def test_the_half_swap_has_exactly_one_definition() -> None:
    """`sides_swapped` is read in one place; everyone else calls `sidesAreSwapped`.

    Two readers is one too many: they drift, and then the lineup names one team
    while the pitch draws the other. This is not hypothetical - the tactical
    role derivation and the lineup heading each grew their own copy before this
    guard existed.
    """
    frontend = ROOT / "frontend" / "src"
    allowed = {
        # The declaration itself.
        Path("frontend/src/types/simulation.ts"),
        # The single reader.
        Path("frontend/src/renderers/soccer") / SIDE_RESOLVER,
    }

    violations = []
    for path in sorted(frontend.rglob("*.ts")) + sorted(frontend.rglob("*.tsx")):
        if path.name.endswith((".test.ts", ".test.tsx")):
            continue
        relative = path.relative_to(ROOT)
        if relative in allowed:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith(("*", "//", "/*")):
                continue
            if RAW_SWAP_READ.search(line):
                violations.append(f"{relative}:{number}: {stripped}")

    assert not violations, (
        "`sides_swapped` is read outside the side resolver. Call "
        "`sidesAreSwapped(state)` so the swap has one definition:\n  " + "\n  ".join(violations)
    )


def test_the_guard_would_catch_a_real_violation() -> None:
    """The patterns match what they claim to - an always-passing guard is worse
    than none."""
    assert HOME_AWAY.search("const label = match.home_name ?? 'Home';")
    assert RAW_SWAP_READ.search("if (match.sides_swapped) flip();")
    assert not HOME_AWAY.search("const { leftLabel } = resolveSideAssignment(state);")
    assert not RAW_SWAP_READ.search("const swapped = sidesAreSwapped(match);")
