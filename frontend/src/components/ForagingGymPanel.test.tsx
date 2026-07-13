import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { ForagingGymPanel, ForagingGymSummaryDisplay } from './ForagingGymPanel';
import { TankSkillsTab } from './tank_tabs/TankSkillsTab';
import type { ForagingGymSummary } from '../types/skill';

const mockSummary: ForagingGymSummary = {
    subject: 'engine_baseline',
    config_hash: 'c8f3b2a1a09d8e7f',
    mean: 0.69,
    wandering_mean: 0.49,
    perfect_mean: 1.0,
    confidence_interval: [0.65, 0.73],
    range: [0.63, 0.77],
    average_food: 7.4,
    average_energy: 580.5,
    metadata: {
        seeds: [42, 7, 31, 38, 1, 5, 0, 41],
        per_seed: {
            '42': {
                benchmark_id: 'tank/foraging_gym',
                seed: 42,
                score: 0.77,
                score_breakdown: {
                    composable_energy_ratio: 0.77,
                    random_walk_energy_ratio: 0.49,
                    oracle_energy_ratio: 1.0,
                },
                metadata: {
                    oracle_energy: 800,
                    composable: { energy_collected: 616, food_collected: 8, energy_spent: 20, travel_distance: 2000 },
                    random_walk: { energy_collected: 392, food_collected: 5, energy_spent: 30, travel_distance: 3000 },
                    oracle: { energy_collected: 800, food_collected: 12, energy_spent: 15, travel_distance: 1800 },
                    skill: { domain: 'foraging', benchmark_id: 'tank/foraging_gym', metric_name: 'energy_collected_over_oracle', skill_index: 69, rungs_beaten: 1, total_rungs: 2, rungs: [] }
                }
            }
        }
    }
};

describe('ForagingGymPanel', () => {
    it('renders the loading skeleton initially and has no manual seed controls', () => {
        const html = renderToString(<ForagingGymPanel />);

        // Should render header/skeleton
        expect(html).toContain('FORAGING SKILL');
        expect(html).toContain('data-testid="skeleton"');

        // Should NOT have manual seed controls or Run Gym button
        expect(html).not.toContain('seed');
        expect(html).not.toContain('select');
        expect(html).not.toContain('Run gym');
    });
});

describe('ForagingGymSummaryDisplay', () => {
    it('renders the aggregate summary correctly', () => {
        const html = renderToString(<ForagingGymSummaryDisplay summary={mockSummary} />);

        // Basic fields and title
        expect(html).toContain('FORAGING SKILL');
        expect(html).toContain('69');
        expect(html).toContain('SKILLED');
        expect(html).toContain('Efficiently finds most available food');

        // Comparison scale markers
        expect(html).toContain('Wandering');
        expect(html).toContain('Current behavior');
        expect(html).toContain('Perfect route');
        expect(html).toContain('49');
        expect(html).toContain('100');

        // Aggregate info
        expect(html).toContain('Average across');
        expect(html).toContain('standardized trials');
        expect(html).toContain('7.4');
        expect(html).toContain('of 12 food collected');
        expect(html).toContain('Typical range');
        expect(html).toContain('63');
        expect(html).toContain('77');

        // Technical/Test details
        expect(html).toContain('How this is measured');
        expect(html).toContain('Test details');
        expect(html).toContain('engine_baseline');
        expect(html).toContain('c8f3b2a1a09d8e7f');
        expect(html).toContain('Confidence Interval (95%)');
        expect(html).toContain('65.0%');
        expect(html).toContain('73.0%');
    });
});

describe('TankSkillsTab Integration', () => {
    it('does not repeat the "Skills & Benchmarks" title inside the tab content', () => {
        const html = renderToString(<TankSkillsTab />);

        // Should NOT have the title element
        expect(html).not.toContain('Skills &amp; Benchmarks');
        // But should have the descriptive introductory text and panels
        expect(html).toContain('Measure what agents can do outside the ecosystem composite.');
        expect(html).toContain('FORAGING SKILL');
    });
});
