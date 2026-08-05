"""RCSS monitor adapter: sign, angle and identity contracts (ADR-017, §10.5).

Sign and axis errors are invisible in a screenshot and obvious only in motion,
so they are pinned here rather than left to the eye.
"""

from __future__ import annotations

import math

import pytest

from core.minigames.soccer.adapters import (
    RcssMonitorAdapter,
    RcssMonitorParseError,
    parse_show_frame,
    rcss_participants,
    rcss_show_to_canonical,
)
from core.minigames.soccer.coords import (
    CanonicalPoint,
    canonical_to_legacy,
    legacy_to_canonical,
)
from core.minigames.soccer.fake_server import FakeRCSSServer

# A hand-checked monitor frame. The left forward stands 20 m up the pitch and
# 10 m *south* of centre in RCSS terms, moving north-east, facing 45 degrees
# clockwise of +x.
SHOW_FRAME = (
    "(show 12 (pm 0) (tm HomeSide AwaySide 2 1) "
    "((b) 5.0000 -3.0000 1.5000 0.5000) "
    "((l 1) 0 0x1 -20.0000 10.0000 1.0000 -2.0000 45.0000 0 "
    "(v h 90) (s 4000.0 1 1 130600) (c 0 0 0 0 0 0 0 0 0 0 0)) "
    "((r 1) 0 0x1 20.0000 -10.0000 -1.0000 2.0000 180.0000 0 "
    "(v h 90) (s 8000.0 1 1 130600) (c 0 0 0 0 0 0 0 0 0 0 0)))"
)


class TestShowFrameParsing:
    def test_reads_cycle_teams_and_score(self) -> None:
        frame = parse_show_frame(SHOW_FRAME)
        assert frame.cycle == 12
        assert frame.left_name == "HomeSide"
        assert frame.right_name == "AwaySide"
        assert (frame.left_score, frame.right_score) == (2, 1)

    def test_reads_both_sides_and_their_uniform_numbers(self) -> None:
        frame = parse_show_frame(SHOW_FRAME)
        assert [(p.side, p.uniform_number) for p in frame.players] == [("left", 1), ("right", 1)]

    def test_uniform_number_alone_is_not_an_identity(self) -> None:
        # Both sides number from 1, so the composite is what disambiguates (§10.2).
        frame = parse_show_frame(SHOW_FRAME)
        assert len({p.uniform_number for p in frame.players}) == 1
        assert len({p.participant_id for p in frame.players}) == 2

    def test_optional_pointto_fields_do_not_shift_the_position(self) -> None:
        # The monitor appends `pointto` before the tagged sub-lists, so the
        # numeric run gets longer without any index moving.
        with_pointto = (
            "(show 1 ((b) 0 0 0 0) "
            "((l 3) 0 0x1 -11.0000 4.0000 0 0 0 0 12.0000 13.0000 "
            "(v h 90) (s 8000 1 1 130600)))"
        )
        state = rcss_show_to_canonical(with_pointto)
        assert state["players"][0]["position"] == pytest.approx({"x": -11.0, "y": -4.0})

    def test_a_non_show_message_is_rejected_rather_than_half_read(self) -> None:
        with pytest.raises(RcssMonitorParseError):
            parse_show_frame("(sense_body 3 (view_mode high normal))")

    def test_unbalanced_parentheses_are_rejected(self) -> None:
        with pytest.raises(RcssMonitorParseError):
            parse_show_frame("(show 1 ((b) 0 0 0 0)")


class TestCanonicalConversion:
    def test_y_is_flipped_and_x_is_not(self) -> None:
        state = rcss_show_to_canonical(SHOW_FRAME)
        left, right = state["players"]
        assert left["position"] == pytest.approx({"x": -20.0, "y": -10.0})
        assert right["position"] == pytest.approx({"x": 20.0, "y": 10.0})
        assert state["ball"]["position"] == pytest.approx({"x": 5.0, "y": 3.0})

    def test_velocity_takes_the_same_flip_as_position(self) -> None:
        # A velocity that kept RCSS handedness would send players drifting the
        # wrong way between monitor frames while their positions looked right.
        state = rcss_show_to_canonical(SHOW_FRAME)
        assert state["players"][0]["velocity"] == pytest.approx({"x": 1.0, "y": 2.0})
        assert state["ball"]["velocity"] == pytest.approx({"x": 1.5, "y": -0.5})

    def test_body_angle_becomes_radians_counter_clockwise(self) -> None:
        state = rcss_show_to_canonical(SHOW_FRAME)
        # 45 degrees clockwise in RCSS is -pi/4 counter-clockwise in canonical.
        assert state["players"][0]["facing_angle"] == pytest.approx(-math.pi / 4)
        assert abs(state["players"][1]["facing_angle"]) == pytest.approx(math.pi)

    def test_stamina_is_normalised_to_the_wire_range(self) -> None:
        state = rcss_show_to_canonical(SHOW_FRAME)
        assert state["players"][0]["stamina"] == pytest.approx(0.5)
        assert state["players"][1]["stamina"] == pytest.approx(1.0)

    def test_the_state_declares_the_space_it_is_in(self) -> None:
        assert rcss_show_to_canonical(SHOW_FRAME)["coord_space"] == "canonical"

    def test_a_numeric_play_mode_is_carried_as_an_honest_unknown(self) -> None:
        # Naming it would need the rcssserver PlayMode enum ordering, which
        # nothing here can verify. §10.4 rule 5 prefers a visible unknown to a
        # confidently wrong label, and never a fallback to play_on.
        state = rcss_show_to_canonical(SHOW_FRAME)
        assert state["play_mode"] == "pm:0"
        assert state["play_mode"] != "play_on"

    def test_a_string_play_mode_is_passed_through_verbatim(self) -> None:
        frame = "(show 1 (playmode 1 free_kick_l) ((b) 0 0 0 0))"
        assert rcss_show_to_canonical(frame)["play_mode"] == "free_kick_l"


class TestAttackDirection:
    """Which way each side attacks, in canonical space."""

    def test_left_attacks_positive_x_and_right_attacks_negative_x(self) -> None:
        # RCSS puts the left team's own goal at -x. Advancing means +x for
        # left and -x for right, and the adapter must not disturb that.
        frame = (
            "(show 1 ((b) 0 0 0 0) "
            "((l 1) 0 0x1 -30.0000 0 2.0000 0 0 0 (s 8000 1 1 130600)) "
            "((r 1) 0 0x1 30.0000 0 -2.0000 0 180.0000 0 (s 8000 1 1 130600)))"
        )
        left, right = rcss_show_to_canonical(frame)["players"]
        assert left["position"]["x"] < 0 < left["velocity"]["x"]
        assert right["velocity"]["x"] < 0 < right["position"]["x"]


class TestHandedness:
    """A positive turn is counter-clockwise in canonical space.

    Named so a future reader cannot mistake which side of the render boundary
    this is about: the *screen* is the clockwise one, and that flip lives in
    `renderFromCanonical`, not here.
    """

    def test_positive_canonical_angle_turns_counter_clockwise(self) -> None:
        # +90 degrees canonical points at +y, which is north.
        north = CanonicalPoint(math.cos(math.pi / 2), math.sin(math.pi / 2))
        assert north.y == pytest.approx(1.0)

    def test_the_render_boundary_is_the_clockwise_one(self) -> None:
        assert canonical_to_legacy(CanonicalPoint(0.0, 1.0)).y == pytest.approx(-1.0)

    def test_round_trip_on_the_pure_utilities(self) -> None:
        for point in (
            CanonicalPoint(0.0, 0.0),
            CanonicalPoint(12.5, -7.25),
            CanonicalPoint(-52.5, 34.0),
        ):
            restored = legacy_to_canonical(canonical_to_legacy(point))
            assert (restored.x, restored.y) == pytest.approx((point.x, point.y))


class TestParticipants:
    def test_rcss_players_are_external_not_fish(self) -> None:
        # They have no genome, so the renderer must take its neutral branch
        # rather than inventing an avatar.
        participants = rcss_participants(rcss_show_to_canonical(SHOW_FRAME))
        assert {p["avatar_kind"] for p in participants} == {"external"}

    def test_participant_ids_are_unique_across_sides(self) -> None:
        participants = rcss_participants(rcss_show_to_canonical(SHOW_FRAME))
        assert [p["participant_id"] for p in participants] == ["left_1", "right_1"]


class TestFakeServerMonitorFrames:
    """The project's own server is the fixture source (§10.5)."""

    def _server(self, team_size: int) -> FakeRCSSServer:
        server = FakeRCSSServer(seed=42, team_size=team_size)
        server.setup_teams()
        return server

    @pytest.mark.parametrize("team_size", [3, 6, 11])
    def test_a_frame_round_trips_at_every_supported_team_size(self, team_size: int) -> None:
        server = self._server(team_size)
        state = rcss_show_to_canonical(server.get_monitor_message())
        assert len(state["players"]) == team_size * 2
        assert sum(1 for p in state["players"] if p["side"] == "left") == team_size

    def test_positions_survive_the_server_to_canonical_trip(self) -> None:
        server = FakeRCSSServer(seed=42, team_size=1)
        server.add_player("left_1", "left", (-14.5, 6.25), body_angle=math.pi / 3)
        state = rcss_show_to_canonical(server.get_monitor_message())
        player = state["players"][0]
        # The engine is already canonical-handed, so a correct emit-then-parse
        # pair is the identity - two sign flips that cancel. A single missing
        # flip on either side shows up here as a mirrored player.
        assert player["position"] == pytest.approx({"x": -14.5, "y": 6.25})
        assert player["facing_angle"] == pytest.approx(math.pi / 3)

    def test_frames_are_byte_identical_for_identical_state(self) -> None:
        assert self._server(3).get_monitor_message() == self._server(3).get_monitor_message()

    def test_an_11v11_frame_carries_22_distinct_participants(self) -> None:
        server = self._server(11)
        participants = RcssMonitorAdapter().adapt_participants(server.get_monitor_message())
        assert len({p["participant_id"] for p in participants}) == 22
        # Uniform numbers repeat across sides; only the composite is unique.
        assert len({p["uniform_number"] for p in participants}) == 11
