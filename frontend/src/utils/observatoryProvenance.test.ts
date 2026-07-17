import { describe, expect, it } from 'vitest';
import { describePredictionProvenance } from './observatoryProvenance';

describe('describePredictionProvenance', () => {
    const base = {
        id: 1,
        name: 'Test Fish',
        score: 0.5,
        food_collected: 5,
        food_available: 10,
        legacy_prediction_skill: 0.7,
        species_founder_legacy_prediction_skill: 0.4,
        parent_legacy_prediction_skill: null as number | null,
        pursuit_prediction_strength: null as number | null,
        parent_pursuit_prediction_strength: null as number | null,
        species_median: 0.5,
        module_fingerprint: 'graph_x',
        similar_fraction: 0.5,
        score_uncertainty: 0.01,
        sample_size: 8,
    };

    it('prefers the living parent legacy comparison when available', () => {
        const result = describePredictionProvenance({
            ...base,
            parent_legacy_prediction_skill: 0.4,
            // A pursuit comparison is also available, but must not be used -
            // the two fields measure different parameters and must never be
            // compared as if they were the same value.
            pursuit_prediction_strength: 1.5,
            parent_pursuit_prediction_strength: 0.1,
        });
        expect(result).toBe('Prediction skill increased from its parent (was 0.40)');
    });

    it('falls back to the pursuit-module comparison when there is no living parent', () => {
        const result = describePredictionProvenance({
            ...base,
            parent_legacy_prediction_skill: null,
            pursuit_prediction_strength: 1.2,
            parent_pursuit_prediction_strength: 0.9,
        });
        expect(result).toBe('Pursuit prediction strength increased from its parent (was 0.90)');
    });

    it('falls back to the species founder when neither parent value is available', () => {
        const result = describePredictionProvenance({
            ...base,
            parent_legacy_prediction_skill: null,
            pursuit_prediction_strength: null,
            parent_pursuit_prediction_strength: null,
        });
        expect(result).toBe('Prediction skill differs from the species founder by +0.30');
    });

    it('falls back to the species founder when only one of the two pursuit fields is available', () => {
        const result = describePredictionProvenance({
            ...base,
            parent_legacy_prediction_skill: null,
            pursuit_prediction_strength: 1.2,
            parent_pursuit_prediction_strength: null,
        });
        expect(result).toBe('Prediction skill differs from the species founder by +0.30');
    });

    it('reports decreased and unchanged parent comparisons correctly', () => {
        expect(
            describePredictionProvenance({ ...base, legacy_prediction_skill: 0.3, parent_legacy_prediction_skill: 0.7 })
        ).toBe('Prediction skill decreased from its parent (was 0.70)');
        expect(
            describePredictionProvenance({ ...base, legacy_prediction_skill: 0.7, parent_legacy_prediction_skill: 0.7 })
        ).toBe('Prediction skill is unchanged from its parent (was 0.70)');
    });
});
