"""Lamarckian CFR-table inheritance for composable poker strategies.

ComposablePokerStrategy carries learned CFR state (``regret``,
``strategy_sum``, ``visit_count``) that offspring can inherit. This module
owns the rules for how that learned state crosses generations:

- ``CFRInheritanceMode`` names the inheritance modes explicitly (they were
  previously implicit in which constructor arguments callers passed).
- ``CFRInheritance.blend_tables`` implements the blend math (documented in
  its docstring) shared by the regret and strategy-sum tables.
- ``CFRInheritance.filter_inheritable`` selects which info sets are
  trustworthy enough to serialize/inherit at all.

Determinism note: all iteration here is over ``sorted(...)`` keys and no RNG
is consumed, so inheritance is byte-identical for identical parents.
"""

from enum import Enum
from typing import TYPE_CHECKING

from core.poker.strategy.composable.definitions import (
    CFR_INHERITANCE_DECAY,
    CFR_MIN_VISITS_FOR_INHERITANCE,
)

if TYPE_CHECKING:
    from core.poker.strategy.composable.strategy import ComposablePokerStrategy

# regret/strategy_sum tables: info_set key -> action -> cumulative value
RegretTable = dict[str, dict[str, float]]
# visit counts: info_set key -> number of visits
VisitCounts = dict[str, int]

# Matches the ComposablePokerStrategy.learning_rate dataclass default.
_DEFAULT_LEARNING_RATE = 1.0


class CFRInheritanceMode(Enum):
    """How offspring inherit parental CFR learning state.

    BLEND_DECAY: Lamarckian inheritance used by sexual crossover
        (``ComposablePokerStrategy.from_parents``). Parent tables are
        blended with winner-biased weighting and decayed (see
        ``CFRInheritance.blend_tables``); learning rates are blended
        linearly.

    RESET: Offspring starts as a fresh learner with empty tables and the
        default learning rate. Used by asexual cloning
        (``ComposablePokerStrategy.clone_with_mutation``).
    """

    BLEND_DECAY = "blend_decay"
    RESET = "reset"


class CFRInheritance:
    """Blends and filters CFR learning state across generations."""

    @staticmethod
    def blend_tables(
        table1: RegretTable,
        table2: RegretTable,
        weight1: float,
        decay: float,
        min_visits: int,
        visit_count1: VisitCounts,
        visit_count2: VisitCounts,
    ) -> RegretTable:
        """Blend two regret/strategy_sum tables with weighting and decay.

        Blend math:

        1. **Eligibility.** An info set enters the blend if *either* parent
           has visited it at least ``min_visits`` times (each parent's own
           visit counts gate only that parent's keys). Once an info set is
           eligible, *both* parents' values for it participate in the blend,
           even if the other parent's visit count is below the threshold.

        2. **Per-action weighted average with decay.** For every action seen
           by either parent at an eligible info set (missing entries are
           treated as 0.0)::

               blended = (v1 * weight1 + v2 * (1 - weight1)) * decay

           where ``weight1`` is parent1's contribution share (parent1 is the
           winner under winner-biased inheritance, so typically
           ``weight1 >= 0.5``) and ``decay`` (``CFR_INHERITANCE_DECAY``,
           currently 0.80) geometrically shrinks inherited values toward
           zero. After ``n`` generations an unrefreshed value contributes a
           factor of ``decay**n``, so stale knowledge fades and offspring
           can relearn, while regret magnitudes stay bounded across
           generations.

        3. **Visit counts are not blended.** Offspring start with empty
           ``visit_count`` tables: inherited info sets must be re-earned
           (revisited ``min_visits`` times) before they are serialized or
           passed on again, and they are first in line for pruning.

        Info sets and actions are iterated in sorted order so the resulting
        dict ordering is deterministic.
        """
        blended: RegretTable = {}

        # Collect all info sets from both parents that meet minimum visits
        all_info_sets: set[str] = set()
        for k in table1:
            if visit_count1.get(k, 0) >= min_visits:
                all_info_sets.add(k)
        for k in table2:
            if visit_count2.get(k, 0) >= min_visits:
                all_info_sets.add(k)

        for info_set in sorted(all_info_sets):
            actions1 = table1.get(info_set, {})
            actions2 = table2.get(info_set, {})
            all_actions = sorted(set(actions1.keys()) | set(actions2.keys()))

            blended[info_set] = {}
            for action in all_actions:
                val1 = actions1.get(action, 0.0)
                val2 = actions2.get(action, 0.0)
                # Weighted blend with decay
                blended_val = (val1 * weight1 + val2 * (1 - weight1)) * decay
                blended[info_set][action] = blended_val

        return blended

    @staticmethod
    def filter_inheritable(
        regret: RegretTable,
        strategy_sum: RegretTable,
        visit_count: VisitCounts,
        min_visits: int = CFR_MIN_VISITS_FOR_INHERITANCE,
    ) -> tuple[RegretTable, RegretTable, VisitCounts]:
        """Keep only well-visited info sets (used when serializing).

        An info set qualifies if it has been visited at least ``min_visits``
        times; the strategy_sum and visit_count tables are filtered to the
        same key set as the qualifying regret entries.
        """
        inheritable_regret = {
            k: v for k, v in regret.items() if visit_count.get(k, 0) >= min_visits
        }
        inheritable_strategy_sum = {
            k: v for k, v in strategy_sum.items() if k in inheritable_regret
        }
        inheritable_visit_count = {k: v for k, v in visit_count.items() if k in inheritable_regret}
        return inheritable_regret, inheritable_strategy_sum, inheritable_visit_count

    @classmethod
    def inherit(
        cls,
        parent1: "ComposablePokerStrategy",
        parent2: "ComposablePokerStrategy",
        weight1: float = 0.5,
        mode: CFRInheritanceMode = CFRInheritanceMode.BLEND_DECAY,
    ) -> tuple[RegretTable, RegretTable, float]:
        """Compute offspring CFR state from two parents.

        Returns ``(regret, strategy_sum, learning_rate)`` for the offspring.
        See ``CFRInheritanceMode`` for the semantics of each mode and
        ``blend_tables`` for the BLEND_DECAY math.
        """
        if mode is CFRInheritanceMode.RESET:
            return {}, {}, _DEFAULT_LEARNING_RATE

        inherited_regret = cls.blend_tables(
            parent1.regret,
            parent2.regret,
            weight1=weight1,
            decay=CFR_INHERITANCE_DECAY,
            min_visits=CFR_MIN_VISITS_FOR_INHERITANCE,
            visit_count1=parent1.visit_count,
            visit_count2=parent2.visit_count,
        )
        inherited_strategy_sum = cls.blend_tables(
            parent1.strategy_sum,
            parent2.strategy_sum,
            weight1=weight1,
            decay=CFR_INHERITANCE_DECAY,
            min_visits=CFR_MIN_VISITS_FOR_INHERITANCE,
            visit_count1=parent1.visit_count,
            visit_count2=parent2.visit_count,
        )
        # Blend learning rates
        inherited_learning_rate = parent1.learning_rate * weight1 + parent2.learning_rate * (
            1 - weight1
        )
        return inherited_regret, inherited_strategy_sum, inherited_learning_rate
