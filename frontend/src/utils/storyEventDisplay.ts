import type { StoryEvent, StoryEventType } from '../types/story';

/**
 * Presentation metadata for the E3 detector outputs.
 *
 * `label` carries the meaning in **text**, not only in the icon or the severity
 * colour - U7 requires severity to be legible without relying on colour, and an
 * emoji alone is not a label for a screen reader or a monochrome display.
 */
export const STORY_EVENT_META: Record<StoryEventType, { icon: string; label: string }> = {
    population_danger: { icon: '📉', label: 'Population danger' },
    population_recovered: { icon: '📈', label: 'Population recovered' },
    generation_milestone: { icon: '🧬', label: 'Generation milestone' },
    lineage_dominant: { icon: '👑', label: 'Lineage dominant' },
};

const FALLBACK = { icon: '🌍', label: 'World event' };

/** Metadata for an event type, tolerating a type this build does not know. */
export function storyEventMeta(eventType: string) {
    return STORY_EVENT_META[eventType as StoryEventType] ?? FALLBACK;
}

/**
 * Format simulated seconds as `m:ss`, or `h:mm:ss` past an hour.
 *
 * Story events are placed in time by simulation clock, never wall clock - two
 * runs of the same seed produce the same timestamps here.
 */
export function formatSimulationTime(seconds: number): string {
    const total = Math.max(0, Math.floor(seconds));
    const secs = total % 60;
    const mins = Math.floor(total / 60) % 60;
    const hours = Math.floor(total / 3600);
    const mm = String(mins).padStart(2, '0');
    const ss = String(secs).padStart(2, '0');
    return hours > 0 ? `${hours}:${mm}:${ss}` : `${mins}:${ss}`;
}

/**
 * A one-line summary of what actually changed, built from the record's own
 * before/after metrics so the feed never invents meaning the detector did not
 * measure. Returns null when there is nothing honest to say.
 */
export function describeChange(event: StoryEvent): string | null {
    const before = event.metrics_before ?? {};
    const after = event.metrics_after ?? {};

    switch (event.event_type) {
        case 'population_danger':
        case 'population_recovered': {
            const to = after.population;
            if (typeof to !== 'number') return null;
            const from = before.population;
            return typeof from === 'number'
                ? `Population ${from} → ${to}`
                : `Population ${to}`;
        }
        case 'generation_milestone': {
            const milestone = after.milestone;
            const max = after.max_generation;
            if (typeof milestone !== 'number') return null;
            // The card's title already reads "Generation N reached". Only add a
            // line when the population actually ran past the milestone, which
            // is information the title does not carry.
            return typeof max === 'number' && max !== milestone
                ? `Top generation is now ${max}`
                : null;
        }
        case 'lineage_dominant': {
            const share = after.share;
            if (typeof share !== 'number') return null;
            const pct = `${Math.round(share * 100)}%`;
            const members = after.members;
            const population = after.population;
            return typeof members === 'number' && typeof population === 'number'
                ? `${members} of ${population} fish (${pct})`
                : `${pct} of the population`;
        }
        default:
            return null;
    }
}

/** The explicit threshold that fired, rendered as `key value` pairs. */
export function describeThreshold(event: StoryEvent): string | null {
    const entries = Object.entries(event.detector_threshold ?? {});
    if (entries.length === 0) return null;
    return entries
        .map(([key, value]) => `${key.replace(/_/g, ' ')} ${value}`)
        .join(', ');
}
