import cProfile
import pstats

from core.worlds import WorldRegistry

FRAMES = 1000


def run_profile(seed: int = 42):
    print(f"Running profile for {FRAMES} frames...")
    config = {
        "headless": True,
        "screen_width": 2000,
        "screen_height": 2000,
        "max_population": 60,
        "critical_population_threshold": 5,
        "emergency_spawn_cooldown": 90,
        "poker_activity_enabled": False,
        "plants_enabled": False,
        "auto_food_spawn_rate": 9,
    }

    world = WorldRegistry.create_world("tank", seed=seed, config=config)
    world.reset(seed=seed, config=config)

    for i in range(FRAMES):
        world.step()
        if (i + 1) % 100 == 0:
            print(f"Frame {i+1}/{FRAMES}")


if __name__ == "__main__":
    cProfile.run("run_profile()", "profile_stats.prof")

    p = pstats.Stats("profile_stats.prof")
    p.strip_dirs().sort_stats("cumulative").print_stats(30)
    p.sort_stats("time").print_stats(30)
