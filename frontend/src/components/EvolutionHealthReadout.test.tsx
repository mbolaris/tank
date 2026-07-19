/**
 * Render tests for the Evolution Health readout (renderToString — no DOM in
 * the test env). The panel mounts collapsed by default; regressions here
 * would mean the metrics grid (and its extra width) leaks into that state.
 */

import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { MetricsHistory, MetricsSample } from '../types/simulation';
import { EvolutionHealthReadout } from './EvolutionHealthReadout';

function sample(overrides: Partial<MetricsSample> & Pick<MetricsSample, 'frame'>): MetricsSample {
    return {
        max_generation: 1,
        population: 25,
        births_total: 0,
        deaths_total: 0,
        fish_energy: 100,
        poker: { auto_eval_elo: 1000, total_games: 0, showdown_win_rate: 0, net_energy_total: 0 },
        soccer: {
            goals_total: 0,
            goals_per_1k_frames: 0,
            matches_completed: 0,
            matches_skipped: 0,
            baseline_match_score_diff: null,
        },
        diversity_score: 0.2,
        ...overrides,
    };
}

const history: MetricsHistory = {
    schema_version: 2,
    world_id: 'world-1',
    sample_interval_frames: 500,
    max_samples: 50,
    samples: [
        sample({ frame: 0, max_generation: 1, population: 22, traits: { pursuit_aggression: 0.5 } }),
        sample({ frame: 10000, max_generation: 6, population: 28, traits: { pursuit_aggression: 0.6 } }),
    ],
};

const noop = () => undefined;

describe('EvolutionHealthReadout', () => {
    it('mounts collapsed by default, showing only the summary row', () => {
        const html = renderToString(<EvolutionHealthReadout history={history} onOpenTrends={noop} />);

        expect(html).toContain('Evolution');
        // Metrics grid, "Since frame" window text, and the Trends button are
        // only rendered once the panel is expanded.
        expect(html).not.toContain('Turnover');
        expect(html).not.toContain('Population');
        expect(html).not.toContain('Since frame');
        expect(html).not.toContain('Open Trends');
    });

    it('prefers the live population over the last sample when provided', () => {
        const html = renderToString(
            <EvolutionHealthReadout history={history} onOpenTrends={noop} compact livePopulation={31} />
        );
        expect(html).toContain('<strong>31</strong>');
        expect(html).not.toContain('28');
    });

    it('shows a collecting-history placeholder before two samples exist', () => {
        const thin: MetricsHistory = { ...history, samples: [sample({ frame: 0 })] };
        const html = renderToString(<EvolutionHealthReadout history={thin} onOpenTrends={noop} />);

        expect(html).toContain('Collecting enough history to assess selection.');
        expect(html).toContain('Open Trends');
    });

    it('renders a compact floating badge instead of the side panel in Watch Mode', () => {
        const html = renderToString(<EvolutionHealthReadout history={history} onOpenTrends={noop} compact />);

        expect(html).toContain('gen/10k');
        expect(html).not.toContain('aria-label="Evolution health"');
    });
});
