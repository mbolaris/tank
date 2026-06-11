"""Unit tests for the spatial partitioning grid (core/spatial/grid.py).

SpatialGrid backs all collision/proximity queries in the simulation, but had
no dedicated tests. These tests pin its public contracts:

- insert / remove / move (update_agent) bookkeeping, including the dedicated
  fish_grid / food_grid fast-path indexes
- cell assignment at boundaries (exact cell edges, negative coords,
  coordinates outside the world get clamped into edge cells)
- radius queries returning exactly the right entities (validated against a
  brute-force O(n^2) reference, both on hand-built scenarios and on seeded
  random scenarios)
- clear() / rebuild(), duplicate insertion, empty-grid queries

Determinism contract: the property-style tests use fixed seeds only.

Known sharp edges documented (not fixed) by tests below:
- Adding the same agent twice creates a duplicate entry; a single
  remove_agent() then leaves a ghost copy behind (see
  TestDuplicateHandling).
- Queries centered more than one cell outside the world bounds return
  nothing, even though out-of-bounds entities are clamped into edge cells
  at insertion time (see TestOutOfBounds).
"""

import random

from core.entities.plant import Plant
from core.entities.resources import Food
from core.math_utils import Vector2
from core.spatial.grid import SpatialGrid

# ---------------------------------------------------------------------------
# Lightweight stand-ins
#
# SpatialGrid only requires `.pos` with `.x`/`.y`; it routes entities to the
# dedicated fast-path indexes by type *name* ("Fish") or by issubclass against
# the real Food base class. So fish/crabs can be plain stubs, while food must
# genuinely subclass core.entities.resources.Food (we bypass its heavy
# World-dependent __init__).
# ---------------------------------------------------------------------------


class Probe:
    """Generic entity with a position (lands on the slow/generic grid path)."""

    def __init__(self, x: float, y: float):
        self.pos = Vector2(x, y)

    def __repr__(self):  # pragma: no cover - debugging aid only
        return f"{type(self).__name__}({self.pos.x}, {self.pos.y})"


class Fish(Probe):
    """Class name must be exactly 'Fish' to exercise the fish_grid fast path."""


class Crab(Probe):
    pass


class GiantCrab(Crab):
    pass


class FakeFood(Food):
    """Real Food subclass so issubclass-based routing applies.

    Skips Food.__init__ (which requires a World and an RNG); the grid only
    touches `.pos`.
    """

    def __init__(self, x: float, y: float):
        self.pos = Vector2(x, y)


class FakeNectar(Food):
    """Second Food subclass, used to pin subclass-routing semantics."""

    def __init__(self, x: float, y: float):
        self.pos = Vector2(x, y)


def make_plant(x: float, y: float) -> Plant:
    """Create an exact-type Plant without constructing a World.

    query_poker_entities looks plants up by the exact `Plant` type key, so a
    test subclass would be invisible to it; we instead allocate a real Plant
    and only set the attribute the grid reads.
    """
    plant = Plant.__new__(Plant)
    plant.pos = Vector2(x, y)
    return plant


# ---------------------------------------------------------------------------
# Brute-force reference
# ---------------------------------------------------------------------------


def brute_radius(agents, agent, radius):
    """O(n^2) reference: all agents within `radius` of `agent`, excluding it.

    Mirrors the grid's contract: inclusive boundary (dist <= radius),
    exclusion by identity (`is`), positions read live from `.pos`.
    """
    rsq = radius * radius
    out = []
    for other in agents:
        if other is agent:
            continue
        dx = other.pos.x - agent.pos.x
        dy = other.pos.y - agent.pos.y
        if dx * dx + dy * dy <= rsq:
            out.append(other)
    return out


def ids(entities):
    """Order-insensitive, duplicate-sensitive fingerprint of a result list."""
    return sorted(id(e) for e in entities)


# ---------------------------------------------------------------------------
# Construction and cell assignment
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_dimensions_round_up_to_whole_cells(self):
        grid = SpatialGrid(width=1000, height=700, cell_size=150)
        assert grid.cols == 7  # ceil(1000 / 150)
        assert grid.rows == 5  # ceil(700 / 150)

    def test_exact_multiple_dimensions(self):
        grid = SpatialGrid(width=600, height=400, cell_size=100)
        assert grid.cols == 6
        assert grid.rows == 4


class TestCellAssignment:
    """Cell assignment is observable through agent_cells after add_agent."""

    def setup_method(self):
        self.grid = SpatialGrid(width=600, height=400, cell_size=100)

    def cell_of(self, x, y):
        agent = Probe(x, y)
        self.grid.add_agent(agent)
        return self.grid.agent_cells[agent]

    def test_origin_maps_to_first_cell(self):
        assert self.cell_of(0, 0) == (0, 0)

    def test_interior_position(self):
        assert self.cell_of(250, 150) == (2, 1)

    def test_exactly_on_cell_edge_belongs_to_next_cell(self):
        # x == cell_size is the left edge of column 1, not part of column 0.
        assert self.cell_of(100, 0) == (1, 0)
        assert self.cell_of(0, 100) == (0, 1)

    def test_just_inside_cell_edge(self):
        assert self.cell_of(99.999, 99.999) == (0, 0)

    def test_negative_coordinates_clamp_to_first_cell(self):
        assert self.cell_of(-1, -1) == (0, 0)
        assert self.cell_of(-500, -500) == (0, 0)

    def test_exactly_on_world_edge_clamps_to_last_cell(self):
        # x == width truncates to col 6 which is clamped to cols - 1 == 5.
        assert self.cell_of(600, 400) == (5, 3)

    def test_far_outside_world_clamps_to_last_cell(self):
        assert self.cell_of(10_000, 10_000) == (5, 3)

    def test_entity_without_pos_is_ignored(self):
        class NoPos:
            pass

        agent = NoPos()
        self.grid.add_agent(agent)
        assert agent not in self.grid.agent_cells


# ---------------------------------------------------------------------------
# Add / remove / update lifecycle
# ---------------------------------------------------------------------------


class TestAddRemove:
    def setup_method(self):
        self.grid = SpatialGrid(width=600, height=400, cell_size=100)

    def test_added_agent_is_found_by_query(self):
        fish = Fish(50, 50)
        other = Fish(70, 60)
        self.grid.add_agent(fish)
        self.grid.add_agent(other)
        assert self.grid.query_radius(fish, 50) == [other]

    def test_removed_agent_disappears_from_all_indexes(self):
        observer = Probe(50, 50)
        fish = Fish(60, 60)
        food = FakeFood(40, 40)
        for a in (observer, fish, food):
            self.grid.add_agent(a)

        self.grid.remove_agent(fish)
        self.grid.remove_agent(food)

        assert self.grid.query_radius(observer, 200) == []
        assert self.grid.query_fish(observer, 200) == []
        assert self.grid.query_food(observer, 200) == []
        assert fish not in self.grid.agent_cells
        assert food not in self.grid.agent_cells

    def test_remove_unknown_agent_is_noop(self):
        self.grid.remove_agent(Fish(10, 10))  # never added; must not raise
        assert self.grid.agent_cells == {}

    def test_remove_cleans_up_empty_buckets(self):
        fish = Fish(50, 50)
        self.grid.add_agent(fish)
        cell = self.grid.agent_cells[fish]
        self.grid.remove_agent(fish)

        # Empty per-type lists are deleted so iteration stays fast.
        assert Fish not in self.grid.grid.get(cell, {})
        assert cell not in self.grid.fish_grid


class TestUpdateAgent:
    def setup_method(self):
        self.grid = SpatialGrid(width=600, height=400, cell_size=100)

    def test_move_across_cells_relocates_agent(self):
        fish = Fish(50, 50)
        observer_old = Probe(50, 50)
        observer_new = Probe(550, 350)
        self.grid.add_agent(fish)

        fish.pos = Vector2(550, 350)
        self.grid.update_agent(fish)

        assert self.grid.agent_cells[fish] == (5, 3)
        assert self.grid.query_radius(observer_new, 30) == [fish]
        assert self.grid.query_radius(observer_old, 30) == []
        # Dedicated fish index must move in lockstep.
        assert self.grid.query_fish(observer_new, 30) == [fish]
        assert self.grid.query_fish(observer_old, 30) == []

    def test_move_within_same_cell_keeps_single_entry(self):
        fish = Fish(10, 10)
        self.grid.add_agent(fish)
        fish.pos = Vector2(90, 90)  # still cell (0, 0)
        self.grid.update_agent(fish)

        assert self.grid.agent_cells[fish] == (0, 0)
        assert self.grid.fish_grid[(0, 0)].count(fish) == 1
        # Queries see the live position, not the position at insert time.
        assert self.grid.query_radius(Probe(95, 95), 10) == [fish]
        assert self.grid.query_radius(Probe(10, 10), 10) == []

    def test_food_index_follows_cross_cell_move(self):
        food = FakeFood(50, 50)
        self.grid.add_agent(food)
        food.pos = Vector2(350, 250)
        self.grid.update_agent(food)

        assert self.grid.query_food(Probe(350, 250), 10) == [food]
        assert self.grid.query_food(Probe(50, 50), 10) == []
        assert (0, 0) not in self.grid.food_grid

    def test_update_inserts_agent_that_was_never_added(self):
        # Current behavior: update_agent on an untracked agent registers it.
        fish = Fish(50, 50)
        self.grid.update_agent(fish)
        assert self.grid.agent_cells[fish] == (0, 0)
        assert self.grid.query_fish(Probe(60, 60), 50) == [fish]


class TestDuplicateHandling:
    def test_double_add_creates_duplicate_then_ghost_after_remove(self):
        # Documents current behavior (not an endorsement): add_agent does not
        # deduplicate, so adding twice yields duplicate query results, and a
        # single remove_agent only strips one copy while deleting the
        # agent_cells entry -- leaving an untracked ghost that a second
        # remove_agent cannot reach.
        grid = SpatialGrid(width=600, height=400, cell_size=100)
        observer = Probe(50, 50)
        fish = Fish(60, 60)
        grid.add_agent(observer)
        grid.add_agent(fish)
        grid.add_agent(fish)

        assert grid.query_radius(observer, 50) == [fish, fish]

        grid.remove_agent(fish)
        assert grid.query_radius(observer, 50) == [fish]  # ghost copy
        assert fish not in grid.agent_cells
        grid.remove_agent(fish)  # no-op: tracking entry already gone
        assert grid.query_radius(observer, 50) == [fish]

        # rebuild()/clear() is the documented way to recover from this state.
        grid.rebuild([observer, fish])
        assert grid.query_radius(observer, 50) == [fish]


# ---------------------------------------------------------------------------
# Radius queries: hand-built ground truth
# ---------------------------------------------------------------------------


class TestQueryRadius:
    def setup_method(self):
        self.grid = SpatialGrid(width=600, height=400, cell_size=100)

    def test_empty_grid_returns_empty(self):
        probe = Probe(300, 200)
        assert self.grid.query_radius(probe, 1000) == []
        assert self.grid.query_fish(probe, 1000) == []
        assert self.grid.query_food(probe, 1000) == []
        assert self.grid.closest_fish(probe, 1000) is None
        assert self.grid.closest_food(probe, 1000) is None

    def test_query_excludes_self_but_includes_cohabitants(self):
        a = Fish(300, 200)
        b = Fish(300, 200)  # same position
        self.grid.add_agent(a)
        self.grid.add_agent(b)
        assert self.grid.query_radius(a, 10) == [b]
        assert self.grid.query_radius(b, 10) == [a]

    def test_radius_boundary_is_inclusive(self):
        center = Probe(300, 200)
        on_edge = Probe(330, 240)  # 3-4-5 triangle: distance exactly 50
        just_outside = Probe(330.001, 240)
        for a in (center, on_edge, just_outside):
            self.grid.add_agent(a)
        assert self.grid.query_radius(center, 50) == [on_edge]

    def test_query_spans_cell_boundaries(self):
        # Center sits on a 4-cell corner; neighbors live in 4 distinct cells.
        center = Probe(200, 200)
        neighbors = [Probe(190, 190), Probe(210, 190), Probe(190, 210), Probe(210, 210)]
        far = Probe(500, 200)
        self.grid.add_agent(center)
        for n in neighbors:
            self.grid.add_agent(n)
        self.grid.add_agent(far)

        result = self.grid.query_radius(center, 30)
        assert ids(result) == ids(neighbors)

    def test_query_radius_returns_all_entity_types(self):
        center = Probe(300, 200)
        members = [Fish(310, 200), FakeFood(290, 200), Crab(300, 210), make_plant(300, 190)]
        self.grid.add_agent(center)
        for m in members:
            self.grid.add_agent(m)
        assert ids(self.grid.query_radius(center, 50)) == ids(members)


class TestTypedQueries:
    def setup_method(self):
        self.grid = SpatialGrid(width=600, height=400, cell_size=100)
        self.observer = Probe(300, 200)
        self.fish_near = Fish(310, 200)
        self.fish_far = Fish(440, 200)
        self.food_near = FakeFood(300, 215)
        self.nectar = FakeNectar(300, 230)
        self.crab = Crab(290, 200)
        self.giant_crab = GiantCrab(300, 185)
        self.plant = make_plant(320, 220)
        self.everything = [
            self.observer,
            self.fish_near,
            self.fish_far,
            self.food_near,
            self.nectar,
            self.crab,
            self.giant_crab,
            self.plant,
        ]
        for a in self.everything:
            self.grid.add_agent(a)

    def test_query_fish_returns_only_fish_in_range(self):
        assert ids(self.grid.query_fish(self.observer, 50)) == ids([self.fish_near])
        assert ids(self.grid.query_fish(self.observer, 200)) == ids([self.fish_near, self.fish_far])

    def test_query_food_covers_all_food_subclasses(self):
        assert ids(self.grid.query_food(self.observer, 50)) == ids([self.food_near, self.nectar])

    def test_query_type_generic_path_respects_subclasses(self):
        # Querying the base Crab type must include GiantCrab (issubclass),
        # while querying the subclass must exclude the plain Crab.
        assert ids(self.grid.query_type(self.observer, 50, Crab)) == ids(
            [self.crab, self.giant_crab]
        )
        assert ids(self.grid.query_type(self.observer, 50, GiantCrab)) == ids([self.giant_crab])

    def test_query_type_fast_paths_match_dedicated_queries(self):
        assert ids(self.grid.query_type(self.observer, 200, Fish)) == ids(
            self.grid.query_fish(self.observer, 200)
        )
        assert ids(self.grid.query_type(self.observer, 200, Food)) == ids(
            self.grid.query_food(self.observer, 200)
        )

    def test_query_type_food_subclass_returns_all_food(self):
        # Documents current behavior: any Food subclass takes the food_grid
        # fast path, so query_type(FakeNectar) also returns FakeFood entities
        # rather than filtering to the requested subclass.
        assert ids(self.grid.query_type(self.observer, 50, FakeNectar)) == ids(
            [self.food_near, self.nectar]
        )

    def test_closest_fish_and_food(self):
        assert self.grid.closest_fish(self.observer, 500) is self.fish_near
        assert self.grid.closest_food(self.observer, 500) is self.food_near
        # Radius is a hard cutoff even when candidates exist further out.
        assert self.grid.closest_fish(self.observer, 5) is None

    def test_closest_excludes_self(self):
        assert self.grid.closest_fish(self.fish_near, 500) is self.fish_far

    def test_query_interaction_candidates(self):
        # Fish + all food + the exact crab type passed in; plants and other
        # generic entities are excluded.
        result = self.grid.query_interaction_candidates(self.observer, 50, Crab)
        assert ids(result) == ids([self.fish_near, self.food_near, self.nectar, self.crab])

    def test_query_poker_entities_returns_fish_and_exact_type_plants(self):
        result = self.grid.query_poker_entities(self.observer, 50)
        assert ids(result) == ids([self.fish_near, self.plant])


# ---------------------------------------------------------------------------
# get_cells_in_radius, clear, rebuild
# ---------------------------------------------------------------------------


class TestGetCellsInRadius:
    def test_covers_cells_touched_by_radius(self):
        grid = SpatialGrid(width=300, height=300, cell_size=100)
        cells = grid.get_cells_in_radius(150, 150, 50)
        # x range [100, 200] touches cols 1-2 (200 is col 2's left edge).
        assert sorted(cells) == [(1, 1), (1, 2), (2, 1), (2, 2)]

    def test_clamps_to_world_bounds(self):
        grid = SpatialGrid(width=300, height=300, cell_size=100)
        cells = grid.get_cells_in_radius(0, 0, 5000)
        assert sorted(cells) == [(c, r) for c in range(3) for r in range(3)]

    def test_small_radius_single_cell(self):
        grid = SpatialGrid(width=300, height=300, cell_size=100)
        assert grid.get_cells_in_radius(50, 50, 10) == [(0, 0)]


class TestClearAndRebuild:
    def test_clear_empties_all_indexes(self):
        grid = SpatialGrid(width=600, height=400, cell_size=100)
        agents = [Fish(50, 50), FakeFood(60, 60), Crab(70, 70)]
        for a in agents:
            grid.add_agent(a)
        grid.clear()

        probe = Probe(60, 60)
        assert grid.query_radius(probe, 1000) == []
        assert grid.query_fish(probe, 1000) == []
        assert grid.query_food(probe, 1000) == []
        assert grid.agent_cells == {}

    def test_rebuild_replaces_previous_contents(self):
        grid = SpatialGrid(width=600, height=400, cell_size=100)
        old = Fish(50, 50)
        new = Fish(300, 200)
        grid.add_agent(old)

        grid.rebuild([new])

        assert old not in grid.agent_cells
        assert grid.query_fish(Probe(300, 200), 10) == [new]
        assert grid.query_fish(Probe(50, 50), 10) == []


# ---------------------------------------------------------------------------
# Out-of-bounds behavior
# ---------------------------------------------------------------------------


class TestOutOfBounds:
    def setup_method(self):
        self.grid = SpatialGrid(width=600, height=400, cell_size=100)

    def test_slightly_out_of_bounds_entity_is_reachable_from_inside(self):
        # Entities are clamped into edge cells at insert time, and the
        # distance check uses true positions, so an entity just past the edge
        # is still found by an in-bounds query whose cell range reaches col 0.
        outside = Probe(-50, 200)
        observer = Probe(10, 200)
        self.grid.add_agent(outside)
        assert self.grid.query_radius(observer, 100) == [outside]

    def test_query_centered_far_outside_bounds_finds_nothing(self):
        # ODDITY (documented, not fixed): _get_cell clamps insert positions
        # into the grid, but the query range computation only clamps min_col
        # upward and max_col downward. For a query center more than one cell
        # outside the world, max_col stays negative (or min_col exceeds
        # cols-1), the cell range is empty, and the query returns nothing --
        # even for an entity at the exact same position, which insertion
        # clamped into an edge cell.
        outside = Probe(-250, 200)
        self.grid.add_agent(outside)
        assert self.grid.agent_cells[outside] == (0, 2)  # clamped at insert

        observer = Probe(-250, 200)
        assert self.grid.query_radius(observer, 10) == []  # empty cell range

        # A sufficiently large radius from inside the world still reaches it.
        inside = Probe(5, 200)
        assert self.grid.query_radius(inside, 300) == [outside]


# ---------------------------------------------------------------------------
# Property-style: grid vs brute force on seeded random scenarios
# ---------------------------------------------------------------------------


class TestGridMatchesBruteForce:
    """Compare every query family against the O(n^2) reference.

    Random but fully deterministic (fixed seeds). Positions stay strictly
    in-bounds because out-of-bounds query semantics intentionally diverge
    (see TestOutOfBounds).
    """

    WIDTH, HEIGHT = 600, 400
    SEEDS = (1, 7, 42)
    N_ENTITIES = 120
    N_QUERIES = 15

    def build_scenario(self, rng):
        grid = SpatialGrid(self.WIDTH, self.HEIGHT, cell_size=rng.choice([64, 100, 150]))
        makers = [Fish, FakeFood, FakeNectar, Crab, GiantCrab, Probe]
        agents = [
            rng.choice(makers)(rng.uniform(0, self.WIDTH - 1), rng.uniform(0, self.HEIGHT - 1))
            for _ in range(self.N_ENTITIES)
        ]
        for a in agents:
            grid.add_agent(a)
        return grid, agents

    def assert_queries_match(self, grid, agents, rng):
        for _ in range(self.N_QUERIES):
            origin = rng.choice(agents)
            radius = rng.uniform(0, 250)

            expected = brute_radius(agents, origin, radius)
            assert ids(grid.query_radius(origin, radius)) == ids(expected)

            expected_fish = [e for e in expected if type(e).__name__ == "Fish"]
            assert ids(grid.query_fish(origin, radius)) == ids(expected_fish)

            expected_food = [e for e in expected if isinstance(e, Food)]
            assert ids(grid.query_food(origin, radius)) == ids(expected_food)

            expected_crabs = [e for e in expected if isinstance(e, Crab)]
            assert ids(grid.query_type(origin, radius, Crab)) == ids(expected_crabs)

            closest = grid.closest_fish(origin, radius)
            if expected_fish:
                best = min(
                    expected_fish,
                    key=lambda e: (e.pos.x - origin.pos.x) ** 2 + (e.pos.y - origin.pos.y) ** 2,
                )
                # Compare by distance, not identity, to stay robust to ties.
                assert closest is not None
                best_d = (best.pos.x - origin.pos.x) ** 2 + (best.pos.y - origin.pos.y) ** 2
                got_d = (closest.pos.x - origin.pos.x) ** 2 + (closest.pos.y - origin.pos.y) ** 2
                assert got_d == best_d
            else:
                assert closest is None

    def test_static_scenarios_match_brute_force(self):
        for seed in self.SEEDS:
            rng = random.Random(seed)
            grid, agents = self.build_scenario(rng)
            self.assert_queries_match(grid, agents, rng)

    def test_incremental_updates_match_brute_force(self):
        # Move a random subset (including same-cell micro-moves and long
        # jumps), call update_agent, and re-verify: the incremental index
        # maintenance must agree with ground truth computed from live
        # positions.
        for seed in self.SEEDS:
            rng = random.Random(seed)
            grid, agents = self.build_scenario(rng)

            for agent in rng.sample(agents, k=len(agents) // 2):
                if rng.random() < 0.5:
                    agent.pos = Vector2(
                        rng.uniform(0, self.WIDTH - 1), rng.uniform(0, self.HEIGHT - 1)
                    )
                else:  # small jiggle, often within the same cell
                    agent.pos = Vector2(
                        min(max(agent.pos.x + rng.uniform(-20, 20), 0), self.WIDTH - 1),
                        min(max(agent.pos.y + rng.uniform(-20, 20), 0), self.HEIGHT - 1),
                    )
                grid.update_agent(agent)

            # Also remove a few entities entirely.
            removed = rng.sample(agents, k=10)
            for agent in removed:
                grid.remove_agent(agent)
            remaining = [a for a in agents if a not in removed]

            self.assert_queries_match(grid, remaining, rng)
