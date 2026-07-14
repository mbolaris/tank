/**
 * Render and accessibility-contract tests for the fish inspector (U4/E1).
 *
 * The suite uses renderToString (repo convention — no DOM in the test env):
 * effects do not run, so the on-demand fetch stays in its loading state and
 * the tests exercise the static render of live-broadcast data plus the
 * missing-entity and non-transferable states.
 */

import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { EntityDetails } from '../types/entityDetails';
import type { EntityData } from '../types/simulation';
import { EntityInspectorDrawer } from './EntityInspectorDrawer';
import {
    energyBarColor,
    entityTypeLabel,
    formatOrigin,
    formatSpecies,
    formatTraitName,
} from './entityInspectorFormat';

const fishEntity: EntityData = {
    id: 42,
    type: 'fish',
    x: 100,
    y: 100,
    width: 20,
    height: 12,
    energy: 55,
    max_energy: 100,
    age: 1234,
    generation: 7,
    taxon_id: 'prov_42',
    common_name: 'Azure Schooling Sailfin',
    scientific_name: 'Synpinna gregaria',
    species_confidence: 'provisional',
};

const noop = () => undefined;
const neverResolves = () => new Promise<never>(() => undefined);

function renderDrawer(overrides: Partial<Parameters<typeof EntityInspectorDrawer>[0]> = {}) {
    return renderToString(
        <EntityInspectorDrawer
            entityId={42}
            entityType="fish"
            entity={fishEntity}
            isConnected={true}
            sendCommandWithResponse={neverResolves}
            onClose={noop}
            onRequestTransfer={noop}
            followEnabled={false}
            onToggleFollow={noop}
            {...overrides}
        />
    );
}

describe('EntityInspectorDrawer', () => {
    it('renders an accessible dialog with live fish vitals', () => {
        const html = renderDrawer();
        expect(html).toContain('role="dialog"');
        expect(html).toContain('aria-label="Fish inspector"');
        expect(html).toContain('#42');
        expect(html).toContain('Gen 7');
        expect(html).toContain('55 / 100');
        expect(html).toContain('role="meter"');
        expect(html).toContain('aria-label="Close inspector"');
        expect(html).toContain('Azure Schooling Sailfin');
        expect(html).toContain('Synpinna gregaria');
        expect(html).toContain('Taxonomy');
    });

    it('offers transfer as an explicit secondary action for fish', () => {
        const html = renderDrawer();
        expect(html).toContain('Follow');
        expect(html).toContain('Transfer to another world');
    });

    it('shows a clear state instead of stale data when the entity is gone', () => {
        const html = renderDrawer({ entity: null });
        expect(html).toContain('No longer in the world');
        // The transfer action must be disabled for a missing entity.
        expect(html).toMatch(/<button[^>]*disabled[^>]*>[^<]*Transfer/);
    });

    it('disables transfer while disconnected', () => {
        const html = renderDrawer({ isConnected: false });
        expect(html).toMatch(/<button[^>]*disabled[^>]*>[^<]*Transfer/);
    });

    it('offers no transfer action for non-transferable entity types', () => {
        const crab: EntityData = { ...fishEntity, id: 9, type: 'crab' };
        const html = renderDrawer({ entityId: 9, entityType: 'crab', entity: crab });
        expect(html).toContain('aria-label="Crab inspector"');
        expect(html).not.toContain('Transfer to another world');
    });

    it('shows the loading state until details arrive', () => {
        const html = renderDrawer();
        expect(html).toContain('Loading details…');
    });

    it('renders the target memory section when details are loaded', () => {
        const mockDetails = {
            id: 42,
            target_memory: {
                domains: {
                    food: {
                        domain: 'Food',
                        action: 'Continue',
                        action_raw: 'continue',
                        remembering: 'Food #218',
                        last_seen: 'visible',
                        last_seen_frames: 0,
                        confidence: '100%',
                        confidence_raw: 1.0,
                        predicted_location: '0 px ahead',
                        predicted_offset: 0,
                        switch_threshold: '1.4x',
                        memory_duration: 90,
                        last_seen_position: [100, 100],
                        predicted_position: [100, 100],
                        search_vector: [0, 0],
                        influencing_movement: true,
                    },
                    ball: {
                        domain: 'Ball',
                        action: 'Idle',
                        action_raw: 'idle',
                        remembering: 'None',
                        last_seen: '10 frames ago',
                        last_seen_frames: 10,
                        confidence: '50%',
                        confidence_raw: 0.5,
                        predicted_location: '20 px ahead',
                        predicted_offset: 20,
                        switch_threshold: '1.4x',
                        memory_duration: 90,
                        last_seen_position: [120, 120],
                        predicted_position: [140, 140],
                        search_vector: [20, 20],
                        influencing_movement: false,
                    }
                },
                recent_event: null,
            }
        };

        const html = renderDrawer({ initialFetchState: { phase: 'loaded', details: mockDetails as unknown as EntityDetails } });
        expect(html).toContain('Target Memory');
        expect(html).toContain('Food');
        expect(html).toContain('Memory');
        expect(html).toContain('Influencing Movement');
        expect(html).toContain('Food #218');
        expect(html).toContain('Ball');
        expect(html).toContain('Inactive');
    });

    it('does not render Target Memory section when target_memory is null', () => {
        const mockDetails = {
            id: 42,
            target_memory: null
        };

        const html = renderDrawer({ initialFetchState: { phase: 'loaded', details: mockDetails as unknown as EntityDetails } });
        expect(html).not.toContain('Target Memory');
    });
});

describe('inspector display helpers', () => {
    it('maps entity types to friendly labels', () => {
        expect(entityTypeLabel('fish')).toBe('Fish');
        expect(entityTypeLabel('plant_nectar')).toBe('Nectar');
        expect(entityTypeLabel('goal_zone')).toBe('goal_zone'); // unknown passes through
    });

    it('humanizes trait names', () => {
        expect(formatTraitName('pursuit_aggression')).toBe('pursuit aggression');
    });

    it('uses the spec 3-tier energy colors', () => {
        expect(energyBarColor(0.1)).toBe('var(--color-danger)');
        expect(energyBarColor(0.45)).toBe('var(--color-warning)');
        expect(energyBarColor(0.9)).toBe('var(--color-success)');
    });

    it('strips sprite filenames from species values', () => {
        expect(formatSpecies('school.png')).toBe('school');
        expect(formatSpecies('schooling')).toBe('schooling');
    });

    it('only claims primordial origin for generation 0', () => {
        expect(formatOrigin(12, 5)).toBe('Offspring of fish #12');
        expect(formatOrigin(null, 0)).toBe('Primordial spawn');
        // Restored worlds do not persist parent ids: an old generation with no
        // parent must not be presented as a primordial spawn.
        expect(formatOrigin(null, 2100)).toBe('Unknown (lineage not recorded)');
    });
});
