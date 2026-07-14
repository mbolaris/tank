import { renderToString } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import type { ForagingGymSummary } from '../types/skill';

let useCustomHooks = false;
let useStateCallCount = 0;
// eslint-disable-next-line @typescript-eslint/no-unused-vars, @typescript-eslint/no-explicit-any
let mockSummarySetter = (_val: any) => {};
// eslint-disable-next-line @typescript-eslint/no-unused-vars, @typescript-eslint/no-explicit-any
let mockObservatorySetter = (_val: any) => {};
// eslint-disable-next-line @typescript-eslint/no-unused-vars, @typescript-eslint/no-explicit-any
let mockLoadingSetter = (_val: any) => {};
// eslint-disable-next-line @typescript-eslint/no-unused-vars, @typescript-eslint/no-explicit-any
let mockErrorSetter = (_val: any) => {};
let capturedEffect: (() => void) | undefined = undefined;

vi.mock('react', async (importOriginal) => {
    const actual = await importOriginal<typeof import('react')>();
    return {
        ...actual,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        useState: (init: any) => {
            if (useCustomHooks) {
                const index = useStateCallCount;
                useStateCallCount++;
                if (index === 0) {
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    return [null, (v: any) => mockSummarySetter(v)];
                } else if (index === 1) {
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    return [null, (v: any) => mockObservatorySetter(v)];
                } else if (index === 2) {
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    return [true, (v: any) => mockLoadingSetter(v)];
                } else {
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    return [null, (v: any) => mockErrorSetter(v)];
                }
            }
            return actual.useState(init);
        },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        useEffect: (cb: any, deps: any) => {
            if (useCustomHooks) {
                capturedEffect = cb;
                return;
            }
            return actual.useEffect(cb, deps);
        }
    };
});

import { ForagingGymPanel, ForagingGymSummaryDisplay, ForagingGymObservatoryDisplay } from './ForagingGymPanel';
import { TankSkillsTab } from './tank_tabs/TankSkillsTab';
import type { ObservatoryData } from '../types/skill';

const mockSummary: ForagingGymSummary = {
    subject: 'engine_baseline',
    benchmark_id: 'tank/foraging_gym',
    config_hash: 'c8f3b2a1a09d8e7f',
    mean: 0.69,
    wandering_mean: 0.49,
    perfect_mean: 1.0,
    confidence_interval: [0.65, 0.73],
    range: [0.63, 0.77],
    average_food: 7.4,
    average_food_available: 12,
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
        expect(html).toContain('Engine baseline');
        expect(html).toContain('Perfect route');
        expect(html).toContain('49');
        expect(html).toContain('100');

        // Aggregate info
        expect(html).toContain('Average across');
        expect(html).toContain('standardized trials');
        expect(html).toContain('7.4');
        expect(html).toContain('of');
        expect(html).toContain('12');
        expect(html).toContain('food collected');
        expect(html).toContain('Trial range');
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

const mockObservatory: ObservatoryData = {
    status: 'success',
    tank_average: 0.64,
    best_species: {
        name: 'Azure Predictive Bigeye',
        score: 0.78,
    },
    best_individual: {
        id: 481,
        name: 'Azure Predictive Bigeye #481',
        score: 0.83,
        food_collected: 10,
        food_available: 12,
        legacy_prediction_skill: 0.71,
        species_founder_legacy_prediction_skill: 0.48,
        parent_legacy_prediction_skill: 0.65,
        pursuit_prediction_strength: null,
        parent_pursuit_prediction_strength: null,
        species_median: 0.60,
        module_fingerprint: 'graph_a1b2c3d4',
        similar_fraction: 0.23,
        score_uncertainty: 0.045,
        sample_size: 8,
    },
    engine_baseline: 0.70,
    wandering_mean: 0.19,
    perfect_mean: 1.0,
};

describe('TankSkillsTab Integration', () => {
    it('does not repeat the "Skills & Benchmarks" title inside the tab content', () => {
        const html = renderToString(<TankSkillsTab />);

        // Should NOT have the title element
        expect(html).not.toContain('Skills &amp; Benchmarks');
        // But should have the descriptive introductory text and panels
        expect(html).toContain('See how Tank World’s behaviors perform in standardized challenges.');
        expect(html).toContain('FORAGING SKILL');
    });
});

describe('ForagingGymObservatoryDisplay', () => {
    it('renders the observatory dashboard details correctly', () => {
        const html = renderToString(<ForagingGymObservatoryDisplay observatory={mockObservatory} />);
        
        expect(html).toContain("YOUR TANK&#x27;S FORAGING");
        expect(html).toContain('Best species (');
        expect(html).toContain('Azure Predictive Bigeye');
        expect(html).toContain('Tank average');
        expect(html).toContain('Default controller');
        expect(html).toContain('Wandering');
        expect(html).toContain('Perfect route');
        
        // Individual details
        expect(html).toContain('BEST FORAGER:');
        expect(html).toContain('Azure Predictive Bigeye #481');
        expect(html).toContain('Captured');
        expect(html).toContain('10.0');
        expect(html).toContain('12');
        expect(html).toContain('Prediction skill increased from its parent (was 0.65)');
        expect(html).toContain('Species median prediction skill:');
        expect(html).toContain('0.60');
        expect(html).toContain('This module variant (fingerprint:');
        expect(html).toContain('graph_a1b2c3d4');
        expect(html).toContain(') is present in');
        expect(html).toContain('23');
        expect(html).toContain('uncertainty: ±');
        expect(html).toContain('0.045');
        expect(html).toContain('n=');
        expect(html).toContain('8');
    });
});

describe('ForagingGymPanel hook flow', () => {
    it('mocks fetch and verifies transition from loading to loaded state', async () => {
        const fetchMock = vi.fn().mockImplementation((url) => {
            if (url === '/api/skill/foraging-gym/summary') {
                return Promise.resolve({
                    ok: true,
                    json: async () => mockSummary,
                });
            } else if (url === '/api/skill/foraging-gym/observatory') {
                return Promise.resolve({
                    ok: true,
                    json: async () => mockObservatory,
                });
            }
            return Promise.reject(new Error(`Unknown URL: ${url}`));
        });
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (globalThis as any).fetch = fetchMock;

        // Reset tracking vars
        useStateCallCount = 0;
        capturedEffect = undefined;
        const mockSetSummary = vi.fn();
        const mockSetObservatory = vi.fn();
        const mockSetLoading = vi.fn();
        const mockSetError = vi.fn();

        mockSummarySetter = mockSetSummary;
        mockObservatorySetter = mockSetObservatory;
        mockLoadingSetter = mockSetLoading;
        mockErrorSetter = mockSetError;

        useCustomHooks = true;

        try {
            // Trigger render
            ForagingGymPanel({});

            // Verify hooks setup (summary, observatory, loading, error)
            expect(useStateCallCount).toBe(4);
            expect(capturedEffect).toBeDefined();

            // Run the effect
            capturedEffect!();

            // Verify fetch calls
            expect(fetchMock).toHaveBeenCalledWith('/api/skill/foraging-gym/summary');
            expect(fetchMock).toHaveBeenCalledWith('/api/skill/foraging-gym/observatory');

            // Wait for async state updates to be triggered
            await vi.waitFor(() => {
                expect(mockSetSummary).toHaveBeenCalledWith(mockSummary);
                expect(mockSetObservatory).toHaveBeenCalledWith(mockObservatory);
                expect(mockSetLoading).toHaveBeenCalledWith(false);
            });
        } finally {
            useCustomHooks = false;
        }
    });
});

