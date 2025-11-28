
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.simulation_engine import HeadlessSimulator
from core.constants import FRACTAL_PLANTS_ENABLED

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_plant_survival():
    logger.info("Starting plant survival verification (User Config)...")
    
    # Run for 3000 frames
    sim = HeadlessSimulator(max_frames=3000, stats_interval=500)
    
    # Run simulation
    sim.run()
    
    # Check results
    final_stats = sim.get_stats()
    plant_count = final_stats.get("plant_count", 0)
    
    logger.info(f"Final plant count: {plant_count}")
    
    if plant_count > 0:
        logger.info("SUCCESS: Plants survived!")
    else:
        logger.error("FAILURE: All plants went extinct.")

if __name__ == "__main__":
    verify_plant_survival()
