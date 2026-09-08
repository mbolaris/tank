import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { StoryRecap } from './StoryRecap';
import { buildRecap, headlineEvent, summarizeCounts } from '../utils/storyRecap';
import { readStoredId, storageKey } from '../hooks/useLastSeenStoryEvent';
import type { StoryEvent, StoryEventType } from '../types/story';

/** Strip React's SSR text-boundary markers so assertions read like the UI. */
function text(html: string): string {
    return html.replace(/<!-- -->/g, '');
}

function event(overrides: Partial<StoryEvent> & { id: number }): StoryEvent {
    return {
        schema_version: 1,
        event_type: 'generation_milestone' as StoryEventType,
        frame: overrides.id * 120,
        simulation_time: (overrides.id * 120) / 30,
        severity: 'insight',
        title: `Event ${overrides.id}`,
        entity_ids: [],
        lineage_ids: [],
        metrics_before: {},
        metrics_after: {},
        detector_name: 'generation_milestone',
        detector_threshold: {},
        replay_ref: null,
        ...overrides,
    };
}

// ---------------------------------------------------------------------------
// The five acceptance cases U8a names
// ---------------------------------------------------------------------------

describe('buildRecap acceptance cases', () => {
    const events = [event({ id: 1 }), event({ id: 2 }), event({ id: 3 })];

    it('first visit: no baseline yields no recap', () => {
        // The viewer has not been away from anything, so claiming a recap of
        // the whole run would be false.
        expect(buildRecap(events, null)).toBeNull();
    });

    it('cleared storage behaves exactly like a first visit', () => {
        // readStoredId returns null for a missing key, which is the same input
        // a first visit produces - the two cases are deliberately identical.
        expect(readStoredId('world-with-no-entry')).toBeNull();
        expect(buildRecap(events, readStoredId('world-with-no-entry'))).toBeNull();
    });

    it('no new events: baseline at the newest id yields no recap', () => {
        expect(buildRecap(events, 3)).toBeNull();
    });

    it('expired buffer entries are counted, not silently dropped', () => {
        // The viewer last saw id 2; the buffer now starts at id 40. Ids are
        // dense, so exactly 37 records (3..39) are gone.
        const retained = [event({ id: 40 }), event({ id: 41 })];
        const recap = buildRecap(retained, 2);
        expect(recap).not.toBeNull();
        expect(recap!.missingCount).toBe(37);
        expect(recap!.events.map(e => e.id)).toEqual([41, 40]);
    });

    it('reports a gap even when every retained event predates the baseline', () => {
        // Everything after the baseline scrolled off entirely. Saying "nothing
        // happened" here would be the exact lie the acceptance bar forbids.
        const recap = buildRecap([event({ id: 5 })], 10, 60);
        expect(recap).not.toBeNull();
        expect(recap!.events).toEqual([]);
        expect(recap!.missingCount).toBe(50);
    });

    it('multiple worlds get separate storage keys', () => {
        expect(storageKey('world-a')).not.toBe(storageKey('world-b'));
        expect(storageKey('world-a')).toContain('world-a');
    });
});

describe('buildRecap windowing', () => {
    it('includes only events after the baseline, newest first', () => {
        const recap = buildRecap([event({ id: 1 }), event({ id: 2 }), event({ id: 3 })], 1);
        expect(recap!.events.map(e => e.id)).toEqual([3, 2]);
    });

    it('excludes events that arrived after the viewer showed up', () => {
        // The ceiling freezes at arrival, so a live arrival (id 9) must not be
        // folded into a summary of the time they were away.
        const events = [event({ id: 5 }), event({ id: 6 }), event({ id: 9 })];
        const recap = buildRecap(events, 4, 6);
        expect(recap!.events.map(e => e.id)).toEqual([6, 5]);
        expect(recap!.ceilingId).toBe(6);
    });

    it('counts events by type', () => {
        const recap = buildRecap(
            [
                event({ id: 1, event_type: 'population_danger' }),
                event({ id: 2, event_type: 'population_danger' }),
                event({ id: 3, event_type: 'generation_milestone' }),
            ],
            0,
        );
        expect(recap!.counts).toEqual({ population_danger: 2, generation_milestone: 1 });
    });

    it('reports the span it covers, in frames and in the records own clock', () => {
        const recap = buildRecap(
            [
                event({ id: 1, frame: 300, simulation_time: 10 }),
                event({ id: 2, frame: 900, simulation_time: 30 }),
            ],
            0,
        );
        expect(recap!.fromFrame).toBe(300);
        expect(recap!.toFrame).toBe(900);
        // Taken from the records, never recomputed against a hardcoded FPS.
        expect(recap!.fromTime).toBe(10);
        expect(recap!.toTime).toBe(30);
    });
});

// ---------------------------------------------------------------------------
// Never claim causality
// ---------------------------------------------------------------------------

describe('recap wording', () => {
    it('summarizes as bare counts with no connective words', () => {
        const recap = buildRecap(
            [
                event({ id: 1, event_type: 'population_danger' }),
                event({ id: 2, event_type: 'lineage_dominant' }),
            ],
            0,
        )!;
        const summary = summarizeCounts(recap);
        expect(summary).toBe('1 lineage dominant, 1 population danger');
        // The acceptance bar: the recap must not assert causality the records
        // do not establish.
        for (const word of [' because ', ' caused ', ' led to ', ' so ', ' therefore ', ' after ']) {
            expect(summary).not.toContain(word);
        }
    });

    it('pluralizes counts', () => {
        const recap = buildRecap(
            [event({ id: 1 }), event({ id: 2 })].map(e => ({ ...e, event_type: 'population_danger' as StoryEventType })),
            0,
        )!;
        expect(summarizeCounts(recap)).toBe('2 population dangers');
    });

    it('orders the summary by type name so the same recap always reads the same', () => {
        const a = buildRecap(
            [event({ id: 1, event_type: 'population_danger' }), event({ id: 2, event_type: 'generation_milestone' })],
            0,
        )!;
        const b = buildRecap(
            [event({ id: 2, event_type: 'generation_milestone' }), event({ id: 1, event_type: 'population_danger' })],
            0,
        )!;
        expect(summarizeCounts(a)).toBe(summarizeCounts(b));
    });
});

describe('headlineEvent', () => {
    it('picks the highest severity', () => {
        const recap = buildRecap(
            [
                event({ id: 1, severity: 'info' }),
                event({ id: 2, severity: 'concern' }),
                event({ id: 3, severity: 'insight' }),
            ],
            0,
        )!;
        expect(headlineEvent(recap)!.id).toBe(2);
    });

    it('breaks ties toward the most recent', () => {
        const recap = buildRecap(
            [event({ id: 1, severity: 'insight' }), event({ id: 2, severity: 'insight' })],
            0,
        )!;
        expect(headlineEvent(recap)!.id).toBe(2);
    });

    it('returns null when only dropped events remain', () => {
        const recap = buildRecap([event({ id: 5 })], 10, 60)!;
        expect(headlineEvent(recap)).toBeNull();
    });
});

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

describe('StoryRecap', () => {
    const events = [
        event({ id: 1, event_type: 'population_danger', severity: 'concern' }),
        event({ id: 2 }),
        event({ id: 3 }),
    ];

    it('renders nothing on a first visit', () => {
        const html = renderToString(
            <StoryRecap events={events} baselineId={null} ceilingId={3} onDismiss={() => {}} />,
        );
        expect(html).toBe('');
    });

    it('renders nothing when no events are new', () => {
        const html = renderToString(
            <StoryRecap events={events} baselineId={3} ceilingId={3} onDismiss={() => {}} />,
        );
        expect(html).toBe('');
    });

    it('leads with the highest-severity event and counts the rest', () => {
        const html = renderToString(
            <StoryRecap events={events} baselineId={0} ceilingId={3} onDismiss={() => {}} />,
        );
        expect(html).toContain('Since your last visit');
        expect(text(html)).toContain('2 generation milestones, 1 population danger');
        // The headline card is the concern, not merely the newest event.
        expect(html).toContain('data-event-type="population_danger"');
        expect(text(html)).toContain('Show 2 more events');
    });

    it('states a retention gap instead of hiding it', () => {
        const html = renderToString(
            <StoryRecap
                events={[event({ id: 40 })]}
                baselineId={2}
                ceilingId={40}
                onDismiss={() => {}}
            />,
        );
        expect(text(html)).toContain('37 earlier events from this period are no longer retained');
    });

    it('renders a single event as one moment, not a zero-width range', () => {
        const html = renderToString(
            <StoryRecap events={events} baselineId={2} ceilingId={3} onDismiss={() => {}} />,
        );
        expect(text(html)).not.toContain(' – ');
    });

    it('renders a real span as a range', () => {
        const html = renderToString(
            <StoryRecap events={events} baselineId={0} ceilingId={3} onDismiss={() => {}} />,
        );
        expect(text(html)).toContain(' – ');
    });

    it('offers a way to mark the recap as seen', () => {
        const html = renderToString(
            <StoryRecap events={events} baselineId={0} ceilingId={3} onDismiss={() => {}} />,
        );
        expect(html).toContain('Mark as seen');
    });

    it('does not offer to expand a single-event recap', () => {
        const html = renderToString(
            <StoryRecap events={events} baselineId={2} ceilingId={3} onDismiss={() => {}} />,
        );
        expect(text(html)).not.toContain('Show ');
    });
});
