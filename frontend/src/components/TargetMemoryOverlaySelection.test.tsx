/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, expect, it, vi } from 'vitest';

const capturedEffects: Array<any> = [];

vi.mock('react', async (importOriginal) => {
    const actual = await importOriginal<typeof import('react')>();
    return {
        ...actual,
        useCallback: (fn: any) => {
            return fn;
        },
        useRef: (init: any) => {
            return { current: init };
        },
        useState: (init: any) => {
            return [init, vi.fn()];
        },
        useEffect: (effect: any) => {
            capturedEffects.push(effect);
        },
    };
});

import { EntityInspectorDrawer } from './EntityInspectorDrawer';
import type { EntityDetails } from '../types/entityDetails';
import type { EntityData } from '../types/simulation';

const mockFishEntity: EntityData = {
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

const mockDetails: EntityDetails = {
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
                effective_switch_threshold: 1.4,
                remembered_effective_value: 50.0,
                candidate_value: 45.0,
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
        recent_event: {
            domain: 'food',
            action: 'continue',
            from_target: 218,
            to_target: 218,
            age_frames: 2,
        },
        recent_events: {
            food: {
                domain: 'food',
                action: 'continue',
                from_target: 218,
                to_target: 218,
                age_frames: 2,
            }
        }
    }
} as unknown as EntityDetails;

describe('EntityInspectorDrawer overlay callbacks and cleanup', () => {
    it('correctly passes active domain overlay details to onTargetMemoryOverlayChange', async () => {
        // Stub global window, document and HTMLElement
        const mockWindow = {
            setInterval: vi.fn(() => 123),
            clearInterval: vi.fn(),
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
        };
        vi.stubGlobal('window', mockWindow);

        class DummyHTMLElement {
            focus = vi.fn();
        }
        vi.stubGlobal('HTMLElement', DummyHTMLElement);

        const mockDocument = {
            activeElement: new DummyHTMLElement(),
        };
        vi.stubGlobal('document', mockDocument);

        const onTargetMemoryOverlayChange = vi.fn();
        const onPursuitOverlayChange = vi.fn();

        const sendCommandWithResponse = vi.fn().mockResolvedValue({
            success: true,
            details: mockDetails,
        });

        EntityInspectorDrawer({
            entityId: 42,
            entityType: "fish",
            entity: mockFishEntity,
            isConnected: true,
            sendCommandWithResponse: sendCommandWithResponse,
            onClose: () => {},
            onRequestTransfer: () => {},
            followEnabled: false,
            onToggleFollow: () => {},
            onTargetMemoryOverlayChange: onTargetMemoryOverlayChange,
            onPursuitOverlayChange: onPursuitOverlayChange,
        });

        // Trigger the effect that fetches the details
        for (const effect of capturedEffects) {
            effect();
        }

        expect(sendCommandWithResponse).toHaveBeenCalledWith({
            command: 'get_entity_details',
            data: { entity_id: 42 },
        });

        await vi.waitFor(() => {
            expect(onTargetMemoryOverlayChange).toHaveBeenCalled();
        });

        const lastCall = onTargetMemoryOverlayChange.mock.calls[onTargetMemoryOverlayChange.mock.calls.length - 1][0];
        expect(lastCall.domain).toBe('Food');
        expect(lastCall.action).toBe('Continue');
        expect(lastCall.lastSeenPosition).toEqual([100, 100]);
        expect(lastCall.predictedPosition).toEqual([100, 100]);
        expect(lastCall.searchVector).toEqual([0, 0]);
        expect(lastCall.confidence).toBe(1.0);
        expect(lastCall.recentEvent).toEqual({
            domain: 'food',
            action: 'continue',
            ageFrames: 2,
        });

        // Run the cleanup functions of the effects
        for (const effect of capturedEffects) {
            const cleanup = effect();
            if (typeof cleanup === 'function') {
                cleanup();
            }
        }

        expect(onTargetMemoryOverlayChange).toHaveBeenCalledWith(null);
        expect(onPursuitOverlayChange).toHaveBeenCalledWith(null);
        
        vi.unstubAllGlobals();
    });
});
