"""Generate docs/ALGORITHM_CATALOG.md dynamically from the algorithm registry."""

import inspect
import os
import sys
from pathlib import Path
from typing import Any

# Add repo root to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.algorithms.base import ALGORITHM_PARAMETER_BOUNDS
from core.algorithms.registry import ALL_ALGORITHMS, DEPRECATED_ALGORITHMS
from core.algorithms.composable.definitions import (
    ThreatResponse,
    FoodApproach,
    SocialMode,
    PokerEngagement,
    SUB_BEHAVIOR_PARAMS,
)

# High-quality descriptions for sub-behavior choices
SUB_BEHAVIOR_DESCRIPTIONS = {
    # Threat Response
    "PANIC_FLEE": "Flee at max speed directly away from predator",
    "STEALTH_AVOID": "Move slowly and carefully away from predator",
    "FREEZE": "Stop moving when predator is close to avoid detection",
    "ERRATIC_EVADE": "Unpredictable zigzag escape movement",
    # Food Approach
    "DIRECT_PURSUIT": "Beeline directly to nearest food",
    "PREDICTIVE_INTERCEPT": "Predict where moving food/prey will be and intercept",
    "CIRCLING_STRIKE": "Circle around food before striking",
    "AMBUSH_WAIT": "Wait for food to come close, conserving energy",
    "ZIGZAG_SEARCH": "Explore the tank in a zigzag pattern to scan for food",
    "PATROL_ROUTE": "Follow local patrol pattern, diverting to food only when spotted",
    # Social Mode
    "SOLO": "Ignore other fish, acting completely independently",
    "LOOSE_SCHOOL": "Maintain loose proximity to other fish for safety",
    "TIGHT_SCHOOL": "Stay very close to neighboring fish, tight schooling",
    "FOLLOW_LEADER": "Identify and follow the nearest fish ahead of it",
    # Poker Engagement
    "AVOID": "Actively steer away from other fish to avoid poker games",
    "PASSIVE": "Neither seek nor avoid poker games, neutral posture",
    "OPPORTUNISTIC": "Engage in poker if nearby and energy levels are high",
    "AGGRESSIVE": "Actively seek out neighboring fish to trigger poker games",
}

# High-quality hand-crafted metadata for each algorithm's niche and weakness
ALGO_METADATA = {
    # Food seeking
    "greedy_food_seeker": {
        "niche": "High food density environments where immediate exploitation of close resources is optimal.",
        "weakness": "In sparse environments, gets stuck walking in straight lines or gets outcompeted by wider search patterns.",
    },
    "energy_aware_food_seeker": {
        "niche": "Medium-to-sparse food environments where conserving energy when full and rushing for food when hungry is necessary.",
        "weakness": "Suboptimal speed transition thresholds can result in starvation if it waits too long to start moving quickly.",
    },
    "opportunistic_feeder": {
        "niche": "Environments with varying food density, allowing the fish to balance resting/patrolling with sudden, short-range food pursuit.",
        "weakness": "Relies on food coming relatively close; fails to adapt if food is very far.",
    },
    "food_quality_optimizer": {
        "niche": "High quality/density clusters of food where selecting the best nutrition per unit distance traveled dominates.",
        "weakness": "High movement/evaluation overhead when checking distant food options.",
    },
    "ambush_feeder": {
        "niche": "High food spawn rates where sitting still and letting food drift close conserves maximum energy.",
        "weakness": "Extremely vulnerable to starvation if food spawn rate is low or if food is stationary.",
    },
    "patrol_feeder": {
        "niche": "Predictable food spawning grounds, moving in a local area to capture food as soon as it appears.",
        "weakness": "Misses food that spawns outside its patrol radius.",
    },
    "surface_skimmer": {
        "niche": "Shallow/surface food environments where food floats at the top.",
        "weakness": "Completely ignores food in the bottom half of the tank.",
    },
    "bottom_feeder": {
        "niche": "Deep/sinking food environments where food drops to the bottom.",
        "weakness": "High starvation when food stays near the surface, plus low exploration range.",
    },
    "zigzag_forager": {
        "niche": "Wide exploration in empty tanks to search for sparse, randomly distributed food.",
        "weakness": "Inefficient travel path (longer distance) when pursuing a specific, visible food item.",
    },
    "circular_hunter": {
        "niche": "Circling moving food/prey before striking to optimize intercept angle.",
        "weakness": "Unnecessary rotation costs when food is static, delaying feeding.",
    },
    "food_memory_seeker": {
        "niche": "Stationary or clustering food spawns where remembering previous food locations pays off.",
        "weakness": "Memory can become stale in dynamically shifting environments, leading to empty searches.",
    },
    "cooperative_forager": {
        "niche": "Schooling/group-foraging environments where following successful foragers increases search efficiency.",
        "weakness": "High congestion and competition at food sites; susceptible to herd errors if leaders go the wrong way.",
    },
    "aggressive_hunter": {
        "niche": "Highly competitive settings with fast moving prey or high fish counts, where getting to the food first at all costs is required.",
        "weakness": "Extreme energy drain due to constant high-speed sprints; dies of starvation quickly if food is missed.",
    },
    "spiral_forager": {
        "niche": "Systematic search in uniform environments where food is sparse and evenly distributed.",
        "weakness": "Fixed geometric pattern makes it highly predictable and unable to dynamically pivot to nearby threats/opportunities.",
    },
    # Predator avoidance
    "panic_flee": {
        "niche": "High predator density where immediate high-speed flight away from danger is the only option.",
        "weakness": "Extremely high energy cost; can run into other predators or walls if not steering carefully.",
    },
    "stealthy_avoider": {
        "niche": "Low speed, stealthy movement to avoid triggering predator aggression/awareness.",
        "weakness": "Slow speed may fail to escape if the predator has already initiated a pursuit.",
    },
    "freeze_response": {
        "niche": "Camouflage/stillness where moving would trigger predator visual detection.",
        "weakness": "Becomes a sitting duck if the predator approaches directly regardless of movement.",
    },
    "erratic_evader": {
        "niche": "Evading active predator chases by making unpredictable, sharp turns.",
        "weakness": "Hard to navigate toward safety or food while moving erratically; high turning energy cost.",
    },
    "vertical_escaper": {
        "niche": "Predators that operate primarily on a horizontal plane or have poor vertical movement.",
        "weakness": "Ineffective if predators can move vertically just as fast, or if the tank depth is shallow.",
    },
    "group_defender": {
        "niche": "Schooling groups where safety in numbers reduces individual predation risk.",
        "weakness": "If the group is targeted or panics, individual choices are restricted; can lead to group traps.",
    },
    "spiral_escape": {
        "niche": "Escaping line-of-sight predator attacks by looping around the attacker.",
        "weakness": "Complex path length takes longer to reach absolute safety compared to a straight line flee.",
    },
    "border_hugger": {
        "niche": "Staying near walls where predators rarely patrol or where navigation is restricted.",
        "weakness": "Can get cornered easily with no escape routes if a predator approaches along the wall.",
    },
    "perpendicular_escape": {
        "niche": "Breaking the predator's direct line-of-sight/pursuit angle by fleeing at 90 degrees.",
        "weakness": "Does not maximize absolute distance from the predator as quickly as direct fleeing.",
    },
    "distance_keeper": {
        "niche": "Maintaining a strict safety buffer zone, keeping predators at a distance before they start chasing.",
        "weakness": "Can spend too much time adjusting distance, leaving less time for foraging.",
    },
    # Schooling/social
    "tight_schooler": {
        "niche": "Highly coordinated group schooling to minimize predation and maximize collective sensing.",
        "weakness": "Extremely high local competition for food; susceptible to collective traps.",
    },
    "loose_schooler": {
        "niche": "Balancing the safety/social benefits of schooling with individual space to forage.",
        "weakness": "Weak cohesion makes the group vulnerable to split attacks by multiple predators.",
    },
    "leader_follower": {
        "niche": "Hierarchical group movement where a few dominant individuals navigate.",
        "weakness": "Entire school fails if the leader is eaten, makes a bad decision, or gets stuck.",
    },
    "alignment_matcher": {
        "niche": "Creating synchronized school movement velocities (swarming/flocking).",
        "weakness": "Lacks positional cohesion; fish can drift apart if speed matches but positions do not.",
    },
    "separation_seeker": {
        "niche": "Avoiding crowding and collisions within a school, reducing transmission of negative behaviors or group starvation.",
        "weakness": "Can disintegrate the school entirely if separation force is too high.",
    },
    "front_runner": {
        "niche": "Leading the group to navigate toward new resources or away from threats.",
        "weakness": "High exposure to frontal predators/hazards.",
    },
    "perimeter_guard": {
        "niche": "Circling the boundary of a school to watch for and deter predators.",
        "weakness": "High energy cost of constant circling; less opportunity to feed.",
    },
    "mirror_mover": {
        "niche": "Mimicking adjacent fish movements to maintain precise local schooling structures.",
        "weakness": "Delays response to environmental cues by waiting for neighbors to move first.",
    },
    "boids_behavior": {
        "niche": "Classic flocking (combining cohesion, separation, and alignment) for realistic group simulation.",
        "weakness": "Parameter tuning is delicate; poor values lead to either chaotic scattering or rigid stagnation.",
    },
    "dynamic_schooler": {
        "niche": "Schooling that dynamically contracts (gets tighter) when danger is detected and expands for foraging when safe.",
        "weakness": "Transition lag between tight and loose states can leave fish vulnerable or hungry.",
    },
    # Energy management
    "energy_conserver": {
        "niche": "Extreme food scarcity, minimizing unnecessary movement to survive long periods without food.",
        "weakness": "Easily outcompeted for food when it does spawn due to passive speed.",
    },
    "burst_swimmer": {
        "niche": "Alternating rapid exploration with stationary rest periods to optimize metabolic rates.",
        "weakness": "Stationary resting periods make the fish highly vulnerable to passing predators.",
    },
    "opportunistic_rester": {
        "niche": "Resting only when safe and food is absent, maximizing activity when opportunities exist.",
        "weakness": "Can get stuck resting if threat and food detection zones are configured too small.",
    },
    "energy_balancer": {
        "niche": "Balancing current speed/activity directly with remaining internal energy reserves.",
        "weakness": "May run too slowly to escape threats when energy is low.",
    },
    "sustainable_cruiser": {
        "niche": "Constant, steady cruising speed that avoids the high metabolic cost of acceleration and sprinting.",
        "weakness": "Lack of burst speed makes it vulnerable to predators and fast competitors.",
    },
    "starvation_preventer": {
        "niche": "Rapidly switching to hyper-aggressive food seeking when energy drops below critical thresholds.",
        "weakness": "Extreme energy burn in the panic phase can accelerate death if food is not found immediately.",
    },
    "metabolic_optimizer": {
        "niche": "Dynamically tuning speed to maximize distance traveled per unit of energy consumed.",
        "weakness": "Highly dependent on accurate environmental feedback; fails if configuration is noisy.",
    },
    "adaptive_pacer": {
        "niche": "Adapting speed dynamically to both internal energy reserves and local predator/food density.",
        "weakness": "High decision complexity can lead to sub-optimal behavior blending under rapid state changes.",
    },
    # Territory/exploration
    "territorial_defender": {
        "niche": "Patrolling and defending a local area containing reliable food resources.",
        "weakness": "Vulnerable if the local resource dries up; wastes energy chasing intruders.",
    },
    "random_explorer": {
        "niche": "Searching highly unpredictable environments with no structured food patterns.",
        "weakness": "Inefficient pathing, frequently re-visiting recently explored areas.",
    },
    "wall_follower": {
        "niche": "Exploring boundaries or navigating large rectangular layouts.",
        "weakness": "Ignores the entire center of the environment where food or social groups might gather.",
    },
    "corner_seeker": {
        "niche": "Finding shelter or hiding spots in corners where predator approach angles are halved.",
        "weakness": "Can get easily trapped; highly restricted food access.",
    },
    "center_hugger": {
        "niche": "Staying in the center of the environment where food spawns are often dense.",
        "weakness": "High vulnerability to predators that cross the center, and high competition.",
    },
    "route_patroller": {
        "niche": "Patrolling a predefined loop or waypoint sequence to monitor a large territory.",
        "weakness": "Inflexible path; can be easily predicted by predators or miss off-path food.",
    },
    "boundary_explorer": {
        "niche": "Searching along boundary edges for spawned food or escape paths.",
        "weakness": "High travel distance with low food exposure if food spawns centrally.",
    },
    "nomadic_wanderer": {
        "niche": "Long-distance migration to cover maximum ground over time.",
        "weakness": "High energy cost; prone to moving into high-danger areas.",
    },
    # Poker interactions
    "poker_challenger": {
        "niche": "High-energy fish seeking to challenge neighbors to poker games to exploit their energy.",
        "weakness": "Suffers energy loss if opponent plays better or has a better cards hand.",
    },
    "poker_dodger": {
        "niche": "Avoiding poker invitations to preserve energy for foraging.",
        "weakness": "Misses out on profitable poker games when holding strong hands or energy advantage.",
    },
    "poker_gambler": {
        "niche": "High risk tolerance, joining games frequently to quickly accumulate large energy surpluses.",
        "weakness": "High variance; prone to sudden bankruptcy/starvation from consecutive losses.",
    },
    "selective_poker": {
        "niche": "Playing poker only when possessing a distinct energy advantage or within optimal energy bounds.",
        "weakness": "Misses passive energy accumulation when playing too conservatively.",
    },
    "poker_opportunist": {
        "niche": "Balancing poker challenges with food seeking based on direct proximity.",
        "weakness": "Can get distracted by nearby games when in critical need of food.",
    },
    "poker_strategist": {
        "niche": "Incorporating opponent tracking and position awareness to optimize game selection.",
        "weakness": "Overhead in parameters makes it complex to tune and adapt.",
    },
    "poker_bluffer": {
        "niche": "Bluffing to win pots from more conservative players.",
        "weakness": "High-risk strategies can be called and heavily punished by aggressive or high-energy opponents.",
    },
    "poker_conservative": {
        "niche": "High energy threshold requirements, entering poker only when risk is minimal.",
        "weakness": "Extremely low game participation rate.",
    },
}


def get_relative_file_path(cls: Any) -> str:
    """Get the file path of a class relative to the repository root."""
    try:
        abs_path = Path(inspect.getfile(cls)).resolve()
        return abs_path.relative_to(ROOT).as_posix()
    except Exception:
        return "Unknown"


def generate_catalog() -> str:
    """Generate the catalog content as a markdown string."""
    md = []
    md.append("# Tank World Algorithm Catalog")
    md.append("")
    md.append(
        "> This catalog is dynamically generated from the codebase registry. It documents all available fish behavior algorithms, their configuration bounds, and evolutionary characteristics."
    )
    md.append("")
    md.append("---")
    md.append("")
    md.append("## Table of Contents")
    md.append("1. [The Composable Behavior Framework](#the-composable-behavior-framework)")
    md.append(
        "2. [Specialized/Monolithic Behavior Algorithms](#specializedmonolithic-behavior-algorithms)"
    )

    # Categorize algorithms based on module name
    categories: dict[str, list[Any]] = {}
    for algo_cls in ALL_ALGORITHMS:
        mod_parts = algo_cls.__module__.split(".")
        category_name = mod_parts[-1] if len(mod_parts) > 1 else "other"

        # Format category name nicely
        category_title = category_name.replace("_", " ").title()
        if category_title not in categories:
            categories[category_title] = []
        categories[category_title].append(algo_cls)

    for cat_title in sorted(categories.keys()):
        anchor = cat_title.lower().replace(" ", "-")
        md.append(f"   - [{cat_title}](#{anchor})")

    md.append("")
    md.append("---")
    md.append("")

    # Section 1: Composable Behavior Framework
    md.append("## The Composable Behavior Framework")
    md.append("")
    md.append(
        "The Composable Behavior Framework is the primary mechanism for fish behavior evolution. Rather than using fixed algorithms, the genome configures combinations of sub-behaviors along four orthogonal axes."
    )
    md.append("")

    # Threat Response
    md.append("### Threat Response")
    md.append("Determines how fish react when predators are nearby.")
    md.append("| Enum Option | Value | Description |")
    md.append("|---|---|---|")
    for tr in ThreatResponse:
        desc = SUB_BEHAVIOR_DESCRIPTIONS.get(tr.name, tr.__doc__ or "")
        md.append(f"| `{tr.name}` | `{tr.value}` | {desc} |")
    md.append("")

    # Food Approach
    md.append("### Food Approach")
    md.append("Determines how fish approach and capture food.")
    md.append("| Enum Option | Value | Description |")
    md.append("|---|---|---|")
    for fa in FoodApproach:
        desc = SUB_BEHAVIOR_DESCRIPTIONS.get(fa.name, fa.__doc__ or "")
        md.append(f"| `{fa.name}` | `{fa.value}` | {desc} |")
    md.append("")

    # Social Mode
    md.append("### Social Mode")
    md.append("Determines how fish interact and school with other fish.")
    md.append("| Enum Option | Value | Description |")
    md.append("|---|---|---|")
    for sm in SocialMode:
        desc = SUB_BEHAVIOR_DESCRIPTIONS.get(sm.name, sm.__doc__ or "")
        md.append(f"| `{sm.name}` | `{sm.value}` | {desc} |")
    md.append("")

    # Poker Engagement
    md.append("### Poker Engagement")
    md.append("Determines how fish engage with poker minigames.")
    md.append("| Enum Option | Value | Description |")
    md.append("|---|---|---|")
    for pe in PokerEngagement:
        desc = SUB_BEHAVIOR_DESCRIPTIONS.get(pe.name, pe.__doc__ or "")
        md.append(f"| `{pe.name}` | `{pe.value}` | {desc} |")
    md.append("")

    # Composable Parameters
    md.append("### Composable Tuning Parameters")
    md.append("These continuous parameters tune the execution of the selected sub-behaviors.")
    md.append("| Parameter Name | Bounds |")
    md.append("|---|---|")
    for name, param_bounds in sorted(SUB_BEHAVIOR_PARAMS.items()):
        md.append(f"| `{name}` | `[{param_bounds[0]:g}, {param_bounds[1]:g}]` |")
    md.append("")

    md.append("---")
    md.append("")

    # Section 2: Specialized Algorithms
    md.append("## Specialized/Monolithic Behavior Algorithms")
    md.append("")
    md.append(
        "Specialized behavior algorithms are dedicated, self-contained implementations. While Composable Behavior is usually the active choice, these algorithms provide baseline performance references and specialized test configurations."
    )
    md.append("")

    for cat_title in sorted(categories.keys()):
        md.append(f"### {cat_title}")
        md.append("")

        for algo in categories[cat_title]:
            # Instantiate to read metadata
            # Legacies may not accept rng or need it
            import random

            try:
                inst = algo.random_instance(rng=random.Random(0))
            except TypeError:
                inst = algo.random_instance()

            algo_id = inst.algorithm_id
            class_name = algo.__name__
            doc = (algo.__doc__ or "No description available.").strip().split("\n")[0]
            file_path = get_relative_file_path(algo)

            is_deprecated = algo_id in DEPRECATED_ALGORITHMS
            status_badge = " ⚠️ **[DEPRECATED]**" if is_deprecated else ""

            md.append(f"#### {class_name}{status_badge}")
            md.append(f"- **ID**: `{algo_id}`")
            md.append(f"- **Source File**: [{file_path}](../{file_path})")
            md.append(f"- **Description**: {doc}")

            # Fetch custom niche/weakness
            meta = ALGO_METADATA.get(
                algo_id, {"niche": "Not documented yet.", "weakness": "Not documented yet."}
            )
            md.append(f"- **Evolutionary Niche**: {meta['niche']}")
            md.append(f"- **Known Weakness**: {meta['weakness']}")

            # Fetch parameter bounds
            bounds = ALGORITHM_PARAMETER_BOUNDS.get(algo_id, {})
            if bounds:
                md.append("- **Parameters**:")
                for p_name, p_bounds in sorted(bounds.items()):
                    md.append(f"  - `{p_name}`: range `[{p_bounds[0]:g}, {p_bounds[1]:g}]`")
            else:
                md.append("- **Parameters**: None")
            md.append("")

        md.append("")

    return "\n".join(md) + "\n"


def main() -> None:
    output_path = ROOT / "docs" / "ALGORITHM_CATALOG.md"
    content = generate_catalog()

    os.makedirs(output_path.parent, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Catalog successfully generated at: {output_path}")


if __name__ == "__main__":
    main()
