import os

files = [
    "core/collision_system.py",
    "core/entities/plant.py",
    "core/simulation_engine.py",
    "core/plant_poker.py",
    "core/root_spots.py",
    "core/simulators/base_simulator.py",
    "backend/entity_transfer.py",
    "backend/entity_snapshot_builder.py",
    "backend/tank_persistence.py",
    "scripts/test_plant_density.py",
    "tests/test_mixed_poker_with_plants.py",
]

base_dir = r"c:\shared\bolaris\tank"

replacements = [
    ("FRACTAL_PLANT_ROOT_SPOT_COUNT", "PLANT_ROOT_SPOT_COUNT"),
    ("FRACTAL_PLANT_ROOT_Y_BASE", "PLANT_ROOT_Y_BASE"),
    ("FRACTAL_PLANT_ROOT_Y_VARIANCE", "PLANT_ROOT_Y_VARIANCE"),
    ("FRACTAL_PLANT_CULL_INTERVAL", "PLANT_CULL_INTERVAL"),
    ("FRACTAL_PLANT_INITIAL_ENERGY", "PLANT_INITIAL_ENERGY"),
    ("FRACTAL_PLANT_MATURE_ENERGY", "PLANT_MATURE_ENERGY"),
    ("FRACTAL_PLANT_MAX_ENERGY", "PLANT_MAX_ENERGY"),
    ("FRACTAL_PLANT_MIN_SIZE", "PLANT_MIN_SIZE"),
    ("FRACTAL_PLANT_MAX_SIZE", "PLANT_MAX_SIZE"),
    ("FRACTAL_PLANT_DEATH_ENERGY", "PLANT_DEATH_ENERGY"),
    ("FRACTAL_PLANT_BASE_WIDTH", "PLANT_BASE_WIDTH"),
    ("FRACTAL_PLANT_BASE_HEIGHT", "PLANT_BASE_HEIGHT"),
    ("FRACTAL_PLANT_POKER_COOLDOWN", "PLANT_POKER_COOLDOWN"),
    ("FRACTAL_PLANT_MIN_POKER_ENERGY", "PLANT_MIN_POKER_ENERGY"),
    ("FRACTAL_PLANT_POKER_BET_RATIO", "PLANT_POKER_BET_RATIO"),
    ("FRACTAL_PLANT_NECTAR_COOLDOWN", "PLANT_NECTAR_COOLDOWN"),
    ("FRACTAL_PLANT_NECTAR_ENERGY", "PLANT_NECTAR_ENERGY"),
    ("FRACTAL_PLANT_SPROUTING_CHANCE", "PLANT_SPROUTING_CHANCE"),
    ("FRACTAL_PLANT_INITIAL_COUNT", "PLANT_INITIAL_COUNT"),
    ("FRACTAL_PLANT_BASE_ENERGY_RATE", "PLANT_BASE_ENERGY_RATE"),
    ("FRACTAL_PLANT_GROWTH_FACTOR", "PLANT_GROWTH_FACTOR"),
    ("FRACTAL_PLANT_DAY_MODIFIER", "PLANT_DAY_MODIFIER"),
    ("FRACTAL_PLANT_DAWN_DUSK_MODIFIER", "PLANT_DAWN_DUSK_MODIFIER"),
    ("FRACTAL_PLANT_NIGHT_MODIFIER", "PLANT_NIGHT_MODIFIER"),
    ("FRACTAL_PLANT_MIN_ITERATIONS", "PLANT_MIN_ITERATIONS"),
    ("FRACTAL_PLANT_MAX_ITERATIONS", "PLANT_MAX_ITERATIONS"),
    ("FRACTAL_PLANT_DEFAULT_ANGLE", "PLANT_DEFAULT_ANGLE"),
    ("FRACTAL_PLANT_DEFAULT_LENGTH_RATIO", "PLANT_DEFAULT_LENGTH_RATIO"),
    ("FRACTAL_PLANT_POKER_MIN_DISTANCE", "PLANT_POKER_MIN_DISTANCE"),
    ("FRACTAL_PLANT_POKER_MAX_DISTANCE", "PLANT_POKER_MAX_DISTANCE"),
    ("FRACTAL_PLANTS_ENABLED", "PLANTS_ENABLED"),
]

for rel_path in files:
    path = os.path.join(base_dir, rel_path)
    if not os.path.exists(path):
        continue

    with open(path, encoding="utf-8") as f:
        content = f.read()

    original = content
    for old, new in replacements:
        content = content.replace(old, new)

    if content != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {rel_path}")
