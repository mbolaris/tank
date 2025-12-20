
import os

files = [
    "core/mixed_poker.py",
    "core/plant_poker.py",
    "core/plant_poker_strategy.py",
    "core/root_spots.py",
    "core/simulation_engine.py",
    "core/systems/entity_lifecycle.py",
    "core/simulators/base_simulator.py",
    "core/services/stats_calculator.py",
    "core/serializers.py",
    "core/environment.py",
    "core/entities/fish.py",
    "core/collision_system.py",
    "backend/tank_persistence.py",
    "backend/simulation_runner.py",
    "backend/services/auto_eval_service.py",
    "backend/migration_scheduler.py",
    "backend/migration_handler.py",
    "backend/entity_transfer.py",
    "backend/entity_snapshot_builder.py",
    "backend/models.py",
    "backend/transfer_history.py",
    "scripts/test_plant_density.py",
    "scripts/verify_plants_no_metabolic_cost.py",
    "tests/test_energy_accounting.py",
    "tests/test_entity_snapshot_builder.py",
    "tests/test_entity_transfer_codecs.py",
    "tests/test_mixed_poker_with_plants.py",
    "tests/test_serializers.py",
    "tests/test_tank_persistence_restore_infers_type.py",
    "core/entities/plant.py",
]

base_dir = r"c:\shared\bolaris\tank"

for rel_path in files:
    path = os.path.join(base_dir, rel_path)
    if not os.path.exists(path):
        print(f"Skipping {path} (not found)")
        continue

    print(f"Processing {path}...")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    
    # 1. Imports
    content = content.replace("from core.entities.fractal_plant import FractalPlant", "from core.entities.plant import Plant")
    content = content.replace("from core.entities.fractal_plant import PlantNectar", "from core.entities.plant import PlantNectar")
    content = content.replace("from core.entities.fractal_plant import", "from core.entities.plant import")
    content = content.replace("import core.entities.fractal_plant", "import core.entities.plant")
    
    # 2. Class usage
    content = content.replace("FractalPlant", "Plant")
    
    # 3. Module usage (if any)
    content = content.replace("core.entities.fractal_plant", "core.entities.plant")
    
    # 4. String literals for entity type
    content = content.replace('"fractal_plant"', '"plant"')
    content = content.replace("'fractal_plant'", "'plant'")
    
    # 5. Variable names (safe ones)
    content = content.replace("fractal_plants", "plants")
    content = content.replace("fractal_plant_count", "plant_count")
    
    if content != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {rel_path}")
    else:
        print(f"No changes in {rel_path}")

