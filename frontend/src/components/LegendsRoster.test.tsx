import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { LegendsRoster } from './LegendsRoster';
import { legendMeta, subjectLabel } from '../utils/legendDisplay';
import type { Legend, LegendKind } from '../types/legend';

function text(html: string): string {
    return html.replace(/<!-- -->/g, '');
}

function legend(overrides: Partial<Legend> & { id: number }): Legend {
    return {
        schema_version: 1,
        kind: 'longevity_record' as LegendKind,
        subject_type: 'fish',
        subject_id: '7',
        name: 'Patient Drifter',
        title: 'Oldest fish this tank has known',
        reason: 'Reached 9000 frames of age.',
        evidence: { age_frames: 9000 },
        frame: 3000,
        simulation_time: 100,
        ...overrides,
    };
}

describe('LegendsRoster', () => {
    it('renders nothing when the tank has no legends', () => {
        expect(renderToString(<LegendsRoster legends={[]} />)).toBe('');
    });

    it('names each legend and states why it qualified', () => {
        const html = renderToString(<LegendsRoster legends={[legend({ id: 1 })]} />);
        expect(html).toContain('Patient Drifter');
        expect(html).toContain('Reached 9000 frames of age.');
        // The criterion is named in words, not carried by the icon alone.
        expect(html).toContain('Longevity record');
    });

    it('tells the viewer these are not benchmark champions', () => {
        // U8b's hard line, stated where a viewer can actually see it.
        const html = renderToString(<LegendsRoster legends={[legend({ id: 1 })]} />);
        expect(text(html)).toContain('Not benchmark champions');
    });

    it('addresses a lineage as a lineage, not a fish', () => {
        const html = renderToString(
            <LegendsRoster
                legends={[legend({ id: 1, subject_type: 'lineage', subject_id: '3' })]}
            />,
        );
        expect(text(html)).toContain('Lineage 3');
        expect(text(html)).not.toContain('Fish #3');
    });

    it('offers the inspector only for a fish still in the world', () => {
        const present = renderToString(
            <LegendsRoster
                legends={[legend({ id: 1, subject_id: '7' })]}
                liveEntityIds={new Set([7])}
                onInspectEntity={() => {}}
            />,
        );
        expect(text(present)).toContain('Inspect Fish #7');

        // A legend outlives its subject; most will be long dead.
        const gone = renderToString(
            <LegendsRoster
                legends={[legend({ id: 1, subject_id: '7' })]}
                liveEntityIds={new Set([99])}
                onInspectEntity={() => {}}
            />,
        );
        expect(text(gone)).not.toContain('Inspect');
    });

    it('never offers to inspect a lineage', () => {
        const html = renderToString(
            <LegendsRoster
                legends={[legend({ id: 1, subject_type: 'lineage', subject_id: '3' })]}
                liveEntityIds={new Set([3])}
                onInspectEntity={() => {}}
            />,
        );
        // Lineage id 3 and fish id 3 are different things; the inspector opens
        // entities, so a lineage must not resolve to a same-numbered fish.
        expect(text(html)).not.toContain('Inspect');
    });

    it('pluralizes the count', () => {
        const one = renderToString(<LegendsRoster legends={[legend({ id: 1 })]} />);
        expect(text(one)).toContain('1 legend<');
        const two = renderToString(
            <LegendsRoster legends={[legend({ id: 1 }), legend({ id: 2, subject_id: '8' })]} />,
        );
        expect(text(two)).toContain('2 legends');
    });
});

describe('legendDisplay', () => {
    it('labels every known kind in words', () => {
        for (const kind of ['longevity_record', 'lineage_founder', 'collapse_survivor'] as const) {
            expect(legendMeta(kind).label.length).toBeGreaterThan(3);
        }
    });

    it('falls back for a kind this build does not know', () => {
        expect(legendMeta('most_charming').label).toBe('Legend');
    });

    it('addresses subjects by type', () => {
        expect(subjectLabel(legend({ id: 1, subject_type: 'fish', subject_id: '4' }))).toBe(
            'Fish #4',
        );
        expect(subjectLabel(legend({ id: 1, subject_type: 'lineage', subject_id: '4' }))).toBe(
            'Lineage 4',
        );
    });
});
