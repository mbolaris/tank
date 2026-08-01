import { describe, it, expect } from 'vitest';
import { renderToString } from 'react-dom/server';
import { StandingPopulationPanel } from './StandingPopulationPanel';
import type { StatsData } from '../types/simulation';

describe('StandingPopulationPanel', () => {
    it('renders placeholder when stats is null without hook order error', () => {
        const htmlNull = renderToString(<StandingPopulationPanel stats={null} />);
        expect(htmlNull).toContain('Connecting to telemetry');

        const mockStats = {
            frame: 100,
            population: 10,
            max_generation: 5,
            gene_distributions: {
                physical: [
                    {
                        key: 'adult_size',
                        label: 'Adult Size',
                        category: 'physical',
                        discrete: false,
                        allowed_min: 0.5,
                        allowed_max: 2.0,
                        min: 0.8,
                        max: 1.5,
                        median: 1.1,
                        bins: [2, 5, 3],
                        bin_edges: [0.5, 1.0, 1.5, 2.0],
                    },
                ],
                behavioral: [],
            },
        } as unknown as StatsData;

        const htmlPopulated = renderToString(<StandingPopulationPanel stats={mockStats} />);
        expect(htmlPopulated).toContain('Adult Size');
    });
});

