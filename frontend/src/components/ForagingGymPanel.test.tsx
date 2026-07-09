import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { ForagingGymResultCard } from './ForagingGymPanel';
import { TankSkillsTab } from './tank_tabs/TankSkillsTab';
import type { ForagingGymResult } from '../types/skill';

const result: ForagingGymResult = {
    benchmark_id: 'tank/foraging_gym',
    seed: 42,
    score: 0.75,
    score_breakdown: {
        composable_energy_ratio: 0.75,
        random_walk_energy_ratio: 0.25,
        oracle_energy_ratio: 1,
    },
    metadata: {
        oracle_energy: 800,
        composable: { energy_collected: 600, food_collected: 8, energy_spent: 20, travel_distance: 2000 },
        random_walk: { energy_collected: 200, food_collected: 3, energy_spent: 30, travel_distance: 3000 },
        oracle: { energy_collected: 800, food_collected: 12, energy_spent: 15, travel_distance: 1800 },
        skill: { domain: 'foraging', benchmark_id: 'tank/foraging_gym', metric_name: 'energy_collected_over_oracle', skill_index: 67, rungs_beaten: 1, total_rungs: 2, rungs: [] },
    },
};

describe('ForagingGymResultCard', () => {
    it('shows the oracle-normalized result and both references', () => {
        const html = renderToString(<ForagingGymResultCard result={result} />);

        expect(html).toContain('75.0%');
        expect(html).toContain('ABOVE RANDOM FLOOR');
        expect(html).toContain('Oracle ceiling');
        expect(html).toContain('600');
        expect(html).toContain('12');
    });

    it('is mounted in the domain-neutral Skills tab', () => {
        const html = renderToString(<TankSkillsTab />);

        expect(html).toContain('Skills &amp; Benchmarks');
        expect(html).toContain('Foraging Gym');
    });
});
