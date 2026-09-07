import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { StoryTimeline } from './StoryTimeline';
import { clusterEvents, mergeFeedRows, MIN_SEPARATION_PCT } from '../utils/storyFeed';
import { StoryEventCard } from './StoryEventCard';
import { merge } from '../hooks/useStoryEvents';
import {
    describeChange,
    describeThreshold,
    formatSimulationTime,
    storyEventMeta,
} from '../utils/storyEventDisplay';
import type { CommentaryItem } from '../types/simulation';
import type { StoryEvent, StoryEventType } from '../types/story';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

/**
 * Strip React's SSR text-boundary markers so assertions can be written against
 * the text a viewer actually sees, not `Inspect fish #<!-- -->7`.
 */
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

function comment(overrides: Partial<CommentaryItem> & { id: number }): CommentaryItem {
    return {
        created_at: 1_700_000_000,
        frame: 500,
        author: 'claude',
        text: 'An observation',
        tags: [],
        severity: 'info',
        topic: 'ecosystem',
        reactions: {},
        ...overrides,
    };
}

// ---------------------------------------------------------------------------
// Hook merge: ordering and dedup must survive reconnects
// ---------------------------------------------------------------------------

describe('useStoryEvents merge', () => {
    it('orders newest first by id', () => {
        const merged = merge([], [event({ id: 1 }), event({ id: 3 }), event({ id: 2 })]);
        expect(merged.map(e => e.id)).toEqual([3, 2, 1]);
    });

    it('deduplicates an event already held', () => {
        const prev = merge([], [event({ id: 1 }), event({ id: 2 })]);
        const after = merge(prev, [event({ id: 2 }), event({ id: 3 })], 2);
        expect(after.map(e => e.id)).toEqual([3, 2, 1]);
    });

    it('prefers the server copy on a collision', () => {
        const prev = merge([], [event({ id: 1, title: 'stale' })]);
        const after = merge(prev, [event({ id: 1, title: 'fresh' })], 0);
        expect(after[0].title).toBe('fresh');
    });

    it('keeps prior events when an incremental page adds newer ones', () => {
        // The reconnect case: we hold a backfill page, then poll with since_id
        // and receive only the delta. The old events must not vanish.
        const prev = merge([], [event({ id: 1 }), event({ id: 2 })]);
        const after = merge(prev, [event({ id: 3 })], 2);
        expect(after.map(e => e.id)).toEqual([3, 2, 1]);
    });

    it('replaces the list when the id space restarts', () => {
        // A world switch or server restart renumbers from 1. Merging would
        // interleave two unrelated numbering schemes into nonsense.
        const prev = merge([], [event({ id: 40 }), event({ id: 41 })]);
        const after = merge(prev, [event({ id: 1 }), event({ id: 2 })], 41);
        expect(after.map(e => e.id)).toEqual([2, 1]);
    });

    it('is a no-op for an empty page', () => {
        const prev = merge([], [event({ id: 1 })]);
        expect(merge(prev, [], 1)).toBe(prev);
    });

    it('caps retention so a long session cannot grow without bound', () => {
        const many = Array.from({ length: 400 }, (_, i) => event({ id: i + 1 }));
        const merged = merge([], many);
        expect(merged.length).toBe(300);
        expect(merged[0].id).toBe(400);
    });
});

// ---------------------------------------------------------------------------
// Clustering: markers must aggregate at high density
// ---------------------------------------------------------------------------

describe('clusterEvents', () => {
    it('returns nothing for no events', () => {
        expect(clusterEvents([], 1000)).toEqual([]);
    });

    it('keeps well-separated events as individual markers', () => {
        const events = [
            event({ id: 1, frame: 0 }),
            event({ id: 2, frame: 5000 }),
            event({ id: 3, frame: 10000 }),
        ];
        expect(clusterEvents(events, 10000)).toHaveLength(3);
    });

    it('aggregates events closer than the separation threshold', () => {
        // Ten events inside 1% of a 10k-frame run: one marker, count 10.
        const events = Array.from({ length: 10 }, (_, i) =>
            event({ id: i + 1, frame: 5000 + i * 10 }),
        );
        const clusters = clusterEvents(events, 10000);
        expect(clusters).toHaveLength(1);
        expect(clusters[0].events).toHaveLength(10);
    });

    it('splits a cluster once the gap exceeds the threshold', () => {
        const span = 10000;
        const gap = Math.ceil((MIN_SEPARATION_PCT / 100) * span) + 10;
        const clusters = clusterEvents(
            [event({ id: 1, frame: 1000 }), event({ id: 2, frame: 1000 + gap })],
            span,
        );
        expect(clusters).toHaveLength(2);
    });

    it('orders clusters left-to-right but events newest-first inside one', () => {
        const events = [
            event({ id: 1, frame: 100 }),
            event({ id: 2, frame: 110 }),
            event({ id: 3, frame: 9000 }),
        ];
        const clusters = clusterEvents(events, 10000);
        expect(clusters[0].pct).toBeLessThan(clusters[1].pct);
        expect(clusters[0].events.map(e => e.id)).toEqual([2, 1]);
    });

    it('clamps positions into the track even if a frame overruns the span', () => {
        const clusters = clusterEvents([event({ id: 1, frame: 99999 })], 1000);
        expect(clusters[0].pct).toBeLessThanOrEqual(100);
        expect(clusters[0].pct).toBeGreaterThanOrEqual(0);
    });
});

// ---------------------------------------------------------------------------
// Timeline markup
// ---------------------------------------------------------------------------

describe('StoryTimeline', () => {
    it('explains itself before any event exists', () => {
        const html = renderToString(<StoryTimeline events={[]} currentFrame={0} />);
        expect(html).toContain('Living history');
        expect(html).toContain('no events yet');
    });

    it('exposes markers as listbox options with descriptive names', () => {
        const html = renderToString(
            <StoryTimeline
                events={[event({ id: 1, frame: 600, event_type: 'population_danger', severity: 'concern' })]}
                currentFrame={1200}
            />,
        );
        expect(html).toContain('role="listbox"');
        expect(html).toContain('role="option"');
        // Severity and kind live in the accessible name, not only in colour.
        expect(html).toContain('Population danger');
        expect(text(html)).toContain('severity concern');
    });

    it('labels an aggregated marker with its event count', () => {
        const events = Array.from({ length: 4 }, (_, i) => event({ id: i + 1, frame: 500 + i * 5 }));
        const html = renderToString(<StoryTimeline events={events} currentFrame={10000} />);
        expect(text(html)).toContain('4 events around');
        expect(html).toContain('data-count="4"');
    });

    it('keeps exactly one marker in the tab order (roving tabindex)', () => {
        // Tabbing through every dot would be technically navigable and awful.
        const events = [
            event({ id: 1, frame: 100 }),
            event({ id: 2, frame: 5000 }),
            event({ id: 3, frame: 9000 }),
        ];
        const html = renderToString(<StoryTimeline events={events} currentFrame={10000} />);
        expect((html.match(/tabindex="0"/g) ?? []).length).toBe(1);
        expect((html.match(/tabindex="-1"/g) ?? []).length).toBe(2);
    });

    it('pluralizes the event count', () => {
        const one = renderToString(<StoryTimeline events={[event({ id: 1 })]} currentFrame={500} />);
        expect(text(one)).toContain('1 event<');
        const two = renderToString(
            <StoryTimeline events={[event({ id: 1 }), event({ id: 2 })]} currentFrame={500} />,
        );
        expect(text(two)).toContain('2 events');
    });
});

// ---------------------------------------------------------------------------
// Event card: the honesty rules
// ---------------------------------------------------------------------------

describe('StoryEventCard', () => {
    it('marks the row as a world event, not commentary', () => {
        const html = renderToString(<StoryEventCard event={event({ id: 1 })} />);
        expect(html).toContain('World event');
    });

    it('states severity in words as well as colour', () => {
        const html = renderToString(
            <StoryEventCard event={event({ id: 1, severity: 'concern' })} />,
        );
        expect(html).toContain('concern');
    });

    it('never offers a watch affordance while replay_ref is null', () => {
        const html = renderToString(<StoryEventCard event={event({ id: 1, replay_ref: null })} />);
        expect(html.toLowerCase()).not.toContain('watch');
        // It shows the frame instead of pretending replay exists.
        expect(text(html)).toContain('frame ');
    });

    it('offers an inspector link for an entity that still exists', () => {
        const html = renderToString(
            <StoryEventCard
                event={event({ id: 1, entity_ids: [7] })}
                liveEntityIds={new Set([7])}
                onInspectEntity={() => {}}
            />,
        );
        expect(text(html)).toContain('Inspect fish #7');
    });

    it('explains why it cannot open an entity that is gone', () => {
        const html = renderToString(
            <StoryEventCard
                event={event({ id: 1, entity_ids: [7] })}
                liveEntityIds={new Set([99])}
                onInspectEntity={() => {}}
            />,
        );
        expect(text(html)).not.toContain('Inspect fish');
        expect(text(html)).toContain('has left the tank');
    });

    it('claims nothing about entities before the live set is known', () => {
        const html = renderToString(<StoryEventCard event={event({ id: 1, entity_ids: [7] })} />);
        expect(html).not.toContain('left the tank');
    });

    it('renders the detector name and its explicit threshold', () => {
        const html = renderToString(
            <StoryEventCard
                event={event({
                    id: 1,
                    detector_name: 'population_danger',
                    detector_threshold: { population_danger_at_or_below: 9 },
                })}
            />,
        );
        expect(html).toContain('population_danger');
        expect(text(html)).toContain('population danger at or below 9');
    });
});

// ---------------------------------------------------------------------------
// Display helpers
// ---------------------------------------------------------------------------

describe('storyEventDisplay', () => {
    it('formats simulation time as m:ss and h:mm:ss', () => {
        expect(formatSimulationTime(0)).toBe('0:00');
        expect(formatSimulationTime(92)).toBe('1:32');
        expect(formatSimulationTime(3671)).toBe('1:01:11');
    });

    it('falls back for an event type this build does not know', () => {
        expect(storyEventMeta('something_new').label).toBe('World event');
    });

    it('describes a population change from the record itself', () => {
        expect(
            describeChange(
                event({
                    id: 1,
                    event_type: 'population_danger',
                    metrics_before: { population: 22 },
                    metrics_after: { population: 4 },
                }),
            ),
        ).toBe('Population 22 → 4');
    });

    it('omits the prior value when the record has none', () => {
        expect(
            describeChange(
                event({ id: 1, event_type: 'population_danger', metrics_after: { population: 4 } }),
            ),
        ).toBe('Population 4');
    });

    it('does not restate the title as a change line', () => {
        // The card title already says "Generation 5 reached"; repeating it below
        // is noise, so the change line is omitted unless it adds something.
        expect(
            describeChange(
                event({
                    id: 1,
                    event_type: 'generation_milestone',
                    metrics_after: { milestone: 5, max_generation: 5 },
                }),
            ),
        ).toBeNull();
    });

    it('reports the top generation when it ran past the milestone', () => {
        expect(
            describeChange(
                event({
                    id: 1,
                    event_type: 'generation_milestone',
                    metrics_after: { milestone: 5, max_generation: 7 },
                }),
            ),
        ).toBe('Top generation is now 7');
    });

    it('describes a lineage share with its real member counts', () => {
        expect(
            describeChange(
                event({
                    id: 1,
                    event_type: 'lineage_dominant',
                    metrics_after: { share: 0.51, members: 26, population: 51 },
                }),
            ),
        ).toBe('26 of 51 fish (51%)');
    });

    it('invents nothing when the record carries no usable metrics', () => {
        expect(describeChange(event({ id: 1, metrics_after: {} }))).toBeNull();
        expect(describeThreshold(event({ id: 1, detector_threshold: {} }))).toBeNull();
    });
});

// ---------------------------------------------------------------------------
// Merged Board stream
// ---------------------------------------------------------------------------

describe('mergeFeedRows', () => {
    it('interleaves both kinds newest-first by simulation frame', () => {
        const rows = mergeFeedRows(
            [event({ id: 1, frame: 500 }), event({ id: 2, frame: 1500 })],
            [comment({ id: 1, frame: 1000 })],
        );
        expect(rows.map(r => `${r.kind}:${r.frame}`)).toEqual([
            'event:1500',
            'comment:1000',
            'event:500',
        ]);
    });

    it('puts the fact before the commentary about it on a tie', () => {
        const rows = mergeFeedRows([event({ id: 1, frame: 900 })], [comment({ id: 1, frame: 900 })]);
        expect(rows[0].kind).toBe('event');
    });

    it('handles either side being empty', () => {
        expect(mergeFeedRows([], [comment({ id: 1 })])).toHaveLength(1);
        expect(mergeFeedRows([event({ id: 1 })], [])).toHaveLength(1);
        expect(mergeFeedRows([], [])).toEqual([]);
    });

    it('gives the two id spaces non-colliding keys', () => {
        const rows = mergeFeedRows([event({ id: 1, frame: 10 })], [comment({ id: 1, frame: 10 })]);
        expect(new Set(rows.map(r => r.key)).size).toBe(2);
    });
});
