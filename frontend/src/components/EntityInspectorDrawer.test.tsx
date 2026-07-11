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

import type { EntityData } from '../types/simulation';
import { EntityInspectorDrawer } from './EntityInspectorDrawer';
import { energyBarColor, entityTypeLabel, formatTraitName } from './entityInspectorFormat';

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
    });

    it('offers transfer as an explicit secondary action for fish', () => {
        const html = renderDrawer();
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
});
