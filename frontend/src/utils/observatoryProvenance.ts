import type { ObservatoryData } from '../types/skill';

function describeChange(current: number, previous: number, label: string): string {
    if (current > previous) {
        return `${label} increased from its parent (was ${previous.toFixed(2)})`;
    } else if (current < previous) {
        return `${label} decreased from its parent (was ${previous.toFixed(2)})`;
    }
    return `${label} is unchanged from its parent (was ${previous.toFixed(2)})`;
}

/**
 * The legacy composable-behavior trait and the newer pursuit-module
 * parameter measure genuinely different things, so a living parent's legacy
 * value and its birth-time pursuit-module snapshot must never be compared
 * as if they were the same value - prefer whichever is actually available,
 * falling back to the species founder only when neither parent value is.
 */
export function describePredictionProvenance(bestIndividual: NonNullable<ObservatoryData['best_individual']>): string {
    const {
        legacy_prediction_skill,
        species_founder_legacy_prediction_skill,
        parent_legacy_prediction_skill,
        pursuit_prediction_strength,
        parent_pursuit_prediction_strength,
    } = bestIndividual;

    if (parent_legacy_prediction_skill !== null && parent_legacy_prediction_skill !== undefined) {
        return describeChange(legacy_prediction_skill, parent_legacy_prediction_skill, 'Prediction skill');
    }
    if (
        pursuit_prediction_strength !== null && pursuit_prediction_strength !== undefined &&
        parent_pursuit_prediction_strength !== null && parent_pursuit_prediction_strength !== undefined
    ) {
        return describeChange(pursuit_prediction_strength, parent_pursuit_prediction_strength, 'Pursuit prediction strength');
    }
    const diff = legacy_prediction_skill - species_founder_legacy_prediction_skill;
    const diffStr = diff >= 0 ? `+${diff.toFixed(2)}` : diff.toFixed(2);
    return `Prediction skill differs from the species founder by ${diffStr}`;
}
