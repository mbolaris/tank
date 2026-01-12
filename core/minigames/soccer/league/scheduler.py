"""Deterministic Round-Robin Scheduler for Soccer League."""

from __future__ import annotations

from core.minigames.soccer.league.types import LeagueMatch, TeamAvailability


class LeagueScheduler:
    """Manages season schedules and match selection."""

    def __init__(self) -> None:
        self._season_schedule: list[LeagueMatch] = []
        self._current_match_index: int = 0
        self._season_counter: int = 0

    def get_schedule(self) -> list[LeagueMatch]:
        return self._season_schedule

    def ensure_schedule(self, team_ids: list[str]) -> None:
        """Generate a new schedule if needed or if teams changed significantly."""
        # For simplicity, if schedule is empty or finished, generate new one.
        # Also, strict round-robin usually creates fixed fixtures at start of season.
        # If new teams appear, we might wait for next season or rebuild.
        # Here we rebuild if empty or finished.

        if not self._season_schedule or self._current_match_index >= len(self._season_schedule):
            self._generate_season(sorted(team_ids))

    def get_next_match(self, availability: dict[str, TeamAvailability]) -> LeagueMatch | None:
        """Find the next playable match, skipping unavailable ones."""

        # Scan forward from current index
        while self._current_match_index < len(self._season_schedule):
            match = self._season_schedule[self._current_match_index]

            # Check availability
            home_ok = availability.get(match.home_team_id, TeamAvailability(False, 0)).is_available
            away_ok = availability.get(match.away_team_id, TeamAvailability(False, 0)).is_available

            if home_ok and away_ok:
                return match

            # If not playable, mark as skipped and continue
            match.skipped = True
            match.skip_reason = (
                f"Home unavailable: {match.home_team_id}"
                if not home_ok
                else f"Away unavailable: {match.away_team_id}" if not away_ok else "Unknown"
            )
            self._current_match_index += 1

        # End of season reached
        return None

    def advance_match(self) -> None:
        """Mark current match as done and move pointer."""
        if self._current_match_index < len(self._season_schedule):
            self._season_schedule[self._current_match_index].played = True
            self._current_match_index += 1

    def _generate_season(self, team_ids: list[str]) -> None:
        """Generate round-robin fixtures using Circle Method."""
        self._season_schedule = []
        self._current_match_index = 0
        self._season_counter += 1

        if len(team_ids) < 2:
            return

        # Circle method
        rotation = list(team_ids)
        if len(rotation) % 2 != 0:
            rotation.append("BYE")

        n = len(rotation)
        num_rounds = n - 1
        half = n // 2

        match_counter = 0

        for round_idx in range(num_rounds):
            left = rotation[:half]
            right = list(reversed(rotation[half:]))

            for i in range(half):
                home = left[i]
                away = right[i]

                if home != "BYE" and away != "BYE":
                    # Swap home/away every other match for balance (optional)
                    if round_idx % 2 == 1:
                        home, away = away, home

                    match = LeagueMatch(
                        match_id=f"S{self._season_counter}_R{round_idx}_{home}_vs_{away}",
                        home_team_id=home,
                        away_team_id=away,
                        round_index=round_idx,
                        match_index=match_counter,
                    )
                    self._season_schedule.append(match)
                    match_counter += 1

            # Rotate: Keep index 0 fixed, rotate others
            rotation = [rotation[0]] + [rotation[-1]] + rotation[1:-1]
