import logging

from core.simulation_engine import HeadlessSimulator


def main():
    # Configure logging so simulation prints stats to console
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    sim = HeadlessSimulator(max_frames=300, stats_interval=100)
    sim.run()

    # Print final summary and plant energies
    stats = sim.get_stats()
    print('\nFinal stats:')
    for k, v in stats.items():
        print(f'  {k}: {v}')

    # List fractal plants and their energies
    plants = [e for e in sim.get_all_entities() if hasattr(e, 'plant_id')]
    print(f'\nFractal plants present: {len(plants)}')
    for p in plants:
        print(f'  Plant #{p.plant_id}: energy={getattr(p, "energy", None):.2f}, max={getattr(p, "max_energy", None):.2f}')


if __name__ == '__main__':
    main()
