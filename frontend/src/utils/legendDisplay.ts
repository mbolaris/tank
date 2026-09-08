import type { Legend, LegendKind } from '../types/legend';

/**
 * Presentation metadata for the promotion criteria.
 *
 * `label` carries the meaning in text, not only in the icon: a legend's reason
 * for existing has to survive a screen reader and a monochrome display.
 */
export const LEGEND_META: Record<LegendKind, { icon: string; label: string }> = {
    longevity_record: { icon: '⏳', label: 'Longevity record' },
    lineage_founder: { icon: '🌳', label: 'Lineage founder' },
    collapse_survivor: { icon: '🛟', label: 'Collapse survivor' },
};

const FALLBACK = { icon: '⭐', label: 'Legend' };

/** Metadata for a kind, tolerating one this build does not know. */
export function legendMeta(kind: string) {
    return LEGEND_META[kind as LegendKind] ?? FALLBACK;
}

/** How the subject is addressed: a fish has a number, a lineage is a line. */
export function subjectLabel(legend: Legend): string {
    return legend.subject_type === 'fish'
        ? `Fish #${legend.subject_id}`
        : `Lineage ${legend.subject_id}`;
}
