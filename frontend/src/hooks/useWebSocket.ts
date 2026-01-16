/**
 * WebSocket hook for real-time simulation updates
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import type { SimulationUpdate, Command, CommandResponse, DeltaUpdate } from '../types/simulation';
import { config } from '../config';

// Reuse a single TextDecoder to avoid GC pressure from allocating one per frame.
// At 30fps over long sessions, this prevents 100k+ short-lived allocations per hour.
const sharedTextDecoder = new TextDecoder();

export function useWebSocket(worldId?: string) {
    const [state, setState] = useState<SimulationUpdate | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [connectedWorldId, setConnectedWorldId] = useState<string | null>(worldId ?? null);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<number | null>(null);
    const connectRef = useRef<(() => void) | null>(null);
    const responseCallbacksRef = useRef<Map<string, (data: CommandResponse) => void>>(new Map());
    const unmountedRef = useRef(false);  // Track if component is unmounted

    const connect = useCallback(async () => {
        // Don't connect if component is unmounted
        if (unmountedRef.current) return;

        // Close any existing connection before creating a new one
        if (wsRef.current) {
            wsRef.current.onclose = null;
            wsRef.current.onerror = null;
            wsRef.current.onmessage = null;
            wsRef.current.close();
            wsRef.current = null;
        }

        try {
            // Use worldId if provided, otherwise fetch default world ID
            let wsUrl = worldId ? config.getWsUrlForWorld(worldId) : config.wsUrl;
            let resolvedWorldId = worldId ?? null;

            if (!wsUrl) {
                // No world ID in URL/config - fetch the default world ID from API
                try {
                    const response = await fetch(config.defaultWorldIdUrl);
                    if (response.ok) {
                        const data = await response.json();
                        const defaultWorldId = data.world_id;
                        if (defaultWorldId) {
                            wsUrl = config.getWsUrlForWorld(defaultWorldId);
                            resolvedWorldId = defaultWorldId;
                        }
                    }
                } catch (e) {
                    console.error('Failed to fetch default world ID:', e);
                }
            }

            // Store the resolved world ID so components can use it immediately
            if (resolvedWorldId) {
                setConnectedWorldId(resolvedWorldId);
            }

            if (!wsUrl) {
                // Still no valid URL, cannot connect.
                return;
            }

            const ws = new WebSocket(wsUrl);
            ws.binaryType = 'arraybuffer';

            ws.onopen = () => {
                setIsConnected(true);
            };

            ws.onmessage = (event) => {
                try {
                    // Handle binary data (ArrayBuffer) from orjson
                    let jsonString: string;
                    if (event.data instanceof ArrayBuffer) {
                        jsonString = sharedTextDecoder.decode(event.data);
                    } else {
                        jsonString = event.data;
                    }
                    const data = JSON.parse(jsonString);

                    if (data.type === 'update') {
                        console.log('FULL UPDATE RECEIVED!');  // DEBUG
                        const update = data as SimulationUpdate;
                        // DEBUG: Check if any entities have soccer_effect_state
                        const fishWithSoccer = update.snapshot?.entities?.filter((e: any) => e.soccer_effect_state);
                        if (fishWithSoccer && fishWithSoccer.length > 0) {
                            console.log('FULL UPDATE - Fish with soccer_effect_state:', fishWithSoccer.map((e: any) => ({ id: e.id, state: e.soccer_effect_state })));
                        }
                        // V1 schema: Populate convenience fields from snapshot for component access
                        update.frame = update.snapshot.frame;
                        update.elapsed_time = update.snapshot.elapsed_time;
                        update.entities = update.snapshot.entities;
                        update.stats = update.snapshot.stats;
                        update.poker_events = update.snapshot.poker_events;
                        update.soccer_events = update.snapshot.soccer_events;
                        update.soccer_league_live = update.snapshot.soccer_league_live;
                        update.poker_leaderboard = update.snapshot.poker_leaderboard;
                        update.auto_evaluation = update.snapshot.auto_evaluation;
                        // Preserve mode fields from server
                        update.view_mode = update.view_mode ?? 'side';
                        update.mode_id = update.mode_id ?? 'tank';
                        setState(update);
                    } else if (data.type === 'delta') {
                        setState((current) => (current ? applyDelta(current, data as DeltaUpdate) : current));
                    } else if (data.success !== undefined || data.state !== undefined || data.error !== undefined) {
                        // This is a command response (e.g., poker game state)
                        // Call any pending callbacks
                        responseCallbacksRef.current.forEach((callback) => callback(data));
                        responseCallbacksRef.current.clear();
                    }
                } catch (error) {
                    console.error('WebSocket message parse error:', error, 'Data:', event.data);
                }
            };

            ws.onerror = () => {
                // Connection error will be handled by onclose
            };

            ws.onclose = () => {
                setIsConnected(false);
                wsRef.current = null;

                // Only attempt to reconnect if component is still mounted
                if (!unmountedRef.current) {
                    reconnectTimeoutRef.current = window.setTimeout(() => {
                        if (connectRef.current && !unmountedRef.current) {
                            connectRef.current();
                        }
                    }, config.wsReconnectDelay);
                }
            };

            wsRef.current = ws;
        } catch (error) {
            console.error('WebSocket connection error:', error);
            setIsConnected(false);
        }
    }, [worldId]);

    // Store connect function in ref without mutating during render
    useEffect(() => {
        connectRef.current = connect;
    }, [connect]);

    useEffect(() => {
        // Mark as mounted
        unmountedRef.current = false;

        // WebSocket setup synchronizes with external server state
        connect();

        return () => {
            // Mark as unmounted to prevent reconnection
            unmountedRef.current = true;

            // Cleanup on unmount
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
                reconnectTimeoutRef.current = null;
            }
            if (wsRef.current) {
                wsRef.current.onclose = null;
                wsRef.current.onerror = null;
                wsRef.current.onmessage = null;
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, [connect]);

    const sendCommand = useCallback((command: Command) => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(command));
        }
    }, []);

    const sendCommandWithResponse = useCallback((command: Command): Promise<CommandResponse> => {
        return new Promise((resolve, reject) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                // Add a callback to handle the response
                const callbackId = Math.random().toString(36);
                responseCallbacksRef.current.set(callbackId, (data) => {
                    resolve(data);
                });

                // Set a timeout in case response never comes
                setTimeout(() => {
                    if (responseCallbacksRef.current.has(callbackId)) {
                        responseCallbacksRef.current.delete(callbackId);
                        reject(new Error('Command timeout'));
                    }
                }, 10000); // 10 second timeout

                wsRef.current.send(JSON.stringify(command));
            } else {
                reject(new Error('WebSocket not connected'));
            }
        });
    }, []);

    return {
        state,
        isConnected,
        sendCommand,
        sendCommandWithResponse,
        /** Current server URL for display */
        serverUrl: config.serverDisplay,
        /** Current world ID (from state, may lag behind connection) */
        worldId: state?.world_id ?? null,
        /** Connected world ID (available immediately after connection, before first update) */
        connectedWorldId,
    };
}

function applyDelta(state: SimulationUpdate, delta: DeltaUpdate): SimulationUpdate {
    // V1 Schema: All payloads require nested snapshot structure
    // Backend always sends delta.snapshot with updates/added/removed

    // Get delta data from snapshot (V1 schema - snapshot is required)
    const deltaSnapshot = delta.snapshot;
    if (!deltaSnapshot) {
        // Defensive: if no snapshot, return unchanged state
        console.warn('applyDelta: Received delta without snapshot, ignoring');
        return state;
    }

    const {
        updates,
        added,
        removed,
        frame: nextFrame,
        elapsed_time: nextElapsedTime,
        stats: deltaStats,
        poker_events: deltaEvents,
        soccer_events: deltaSoccerEvents,
        soccer_league_live: deltaSoccerLeagueLive,
    } = deltaSnapshot;
    const hasSoccerLeagueLive = Object.prototype.hasOwnProperty.call(
        deltaSnapshot,
        'soccer_league_live'
    );

    // Current state entities (from V1 snapshot)
    const currentSnapshot = state.snapshot;
    if (!currentSnapshot) {
        console.warn('applyDelta: Current state has no snapshot, ignoring delta');
        return state;
    }

    const currentEntities = currentSnapshot.entities;

    // Build a set of IDs to remove for O(1) lookup
    const removedIds = new Set(removed);

    // Build a map of updates for O(1) lookup
    const updateMap = new Map(updates.map(u => [u.id, u]));

    // Optimization: Only create copies of entities that are actually modified.
    const entities = currentEntities
        .filter(e => !removedIds.has(e.id))
        .map(e => {
            const update = updateMap.get(e.id);
            if (update) {
                // Only create a new object if there's actually an update
                return {
                    ...e,
                    x: update.x,
                    y: update.y,
                    vel_x: update.vel_x,
                    vel_y: update.vel_y,
                    ...(update.poker_effect_state !== undefined && { poker_effect_state: update.poker_effect_state }),
                    ...(update.soccer_effect_state !== undefined && { soccer_effect_state: update.soccer_effect_state }),
                };
            }
            // No update - reuse the same object reference
            return e;
        });

    // Add new entities
    added.forEach(entity => {
        if (!entities.some(e => e.id === entity.id)) {
            entities.push(entity);
        }
    });

    // Handle stats (use delta stats if present, otherwise preserve current)
    const nextStats = deltaStats ?? currentSnapshot.stats;

    // Handle poker events (use delta events if present, otherwise preserve current)
    const currentEvents = currentSnapshot.poker_events ?? [];
    const nextEvents = (deltaEvents && deltaEvents.length > 0) ? deltaEvents.slice(-100) : currentEvents;
    const currentSoccerEvents = currentSnapshot.soccer_events ?? [];
    const nextSoccerEvents = (deltaSoccerEvents && deltaSoccerEvents.length > 0)
        ? deltaSoccerEvents.slice(-100)
        : currentSoccerEvents;

    // Construct new snapshot
    const nextSnapshot = {
        ...currentSnapshot,
        frame: nextFrame,
        elapsed_time: nextElapsedTime,
        entities,
        stats: nextStats,
        poker_events: nextEvents,
        soccer_events: nextSoccerEvents,
        soccer_league_live: hasSoccerLeagueLive
            ? deltaSoccerLeagueLive
            : currentSnapshot.soccer_league_live,
    };

    return {
        ...state,
        world_id: delta.world_id ?? state.world_id,
        world_type: delta.world_type ?? state.world_type,
        view_mode: delta.view_mode ?? state.view_mode,
        mode_id: delta.mode_id ?? state.mode_id ?? 'tank',

        // V1: Snapshot is the source of truth
        snapshot: nextSnapshot,

        // Convenience fields (synced from snapshot for component access)
        frame: nextFrame,
        elapsed_time: nextElapsedTime,
        entities,
        poker_events: nextEvents,
        soccer_events: nextSoccerEvents,
        soccer_league_live: nextSnapshot.soccer_league_live,
        stats: nextStats,
        poker_leaderboard: state.poker_leaderboard,
    };
}
