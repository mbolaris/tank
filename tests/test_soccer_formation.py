import math


def _expected_spawn_specs(team_size: int, *, field_length: float):
    from core.minigames.soccer.formation import SpawnSpec

    half_length = field_length / 2

    specs = []
    for i in range(team_size):
        y = (i // 4 - team_size // 8) * 12

        left_id = f"left_{i + 1}"
        left_x = -half_length / 2 + (i % 4) * 8 - 10
        specs.append(SpawnSpec(player_id=left_id, team="left", x=left_x, y=y, body_angle=0.0))

        right_id = f"right_{i + 1}"
        right_x = half_length / 2 - (i % 4) * 8 + 10
        specs.append(
            SpawnSpec(player_id=right_id, team="right", x=right_x, y=y, body_angle=math.pi)
        )

    return specs


def test_build_default_formation_team_size_3_matches_previous_formula():
    from core.minigames.soccer.formation import build_default_formation
    from core.minigames.soccer.params import SOCCER_CANONICAL_PARAMS

    spawns = build_default_formation(team_size=3, params=SOCCER_CANONICAL_PARAMS)
    expected = _expected_spawn_specs(team_size=3, field_length=SOCCER_CANONICAL_PARAMS.field_length)

    assert spawns == expected
    assert {s.player_id for s in spawns} == {
        "left_1",
        "left_2",
        "left_3",
        "right_1",
        "right_2",
        "right_3",
    }
    assert {s.body_angle for s in spawns if s.team == "left"} == {0.0}
    assert {s.body_angle for s in spawns if s.team == "right"} == {math.pi}


def test_build_default_formation_team_size_8_matches_previous_formula():
    from core.minigames.soccer.formation import build_default_formation
    from core.minigames.soccer.params import SOCCER_CANONICAL_PARAMS

    spawns = build_default_formation(team_size=8, params=SOCCER_CANONICAL_PARAMS)
    expected = _expected_spawn_specs(team_size=8, field_length=SOCCER_CANONICAL_PARAMS.field_length)

    assert spawns == expected
    assert {s.player_id for s in spawns} == {
        "left_1",
        "left_2",
        "left_3",
        "left_4",
        "left_5",
        "left_6",
        "left_7",
        "left_8",
        "right_1",
        "right_2",
        "right_3",
        "right_4",
        "right_5",
        "right_6",
        "right_7",
        "right_8",
    }
    assert {s.body_angle for s in spawns if s.team == "left"} == {0.0}
    assert {s.body_angle for s in spawns if s.team == "right"} == {math.pi}


def test_build_default_formation_is_deterministic():
    from core.minigames.soccer.formation import build_default_formation
    from core.minigames.soccer.params import SOCCER_CANONICAL_PARAMS

    assert build_default_formation(
        team_size=8, params=SOCCER_CANONICAL_PARAMS
    ) == build_default_formation(team_size=8, params=SOCCER_CANONICAL_PARAMS)
