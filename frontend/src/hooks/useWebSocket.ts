/**
 * WebSocket hook for real-time simulation updates
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import type { SimulationUpdate, Command, CommandResponse, DeltaUpdate } from '../types/simulation';
import { config } from '../config';

// Reuse a single TextDecoder to avoid GC pressure from allocating one per frame.
// At 30fps over long sessions, this prevents 100k+ short-lived allocations per hour.
const sharedTextDecoder = new TextDecoder();

export function useWebSocket(tankId?: string) {
    const [state, setState] = useState<SimulationUpdate | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<number | null>(null);
    const connectRef = useRef<(() => void) | null>(null);
    const responseCallbacksRef = useRef<Map<string, (data: CommandResponse) => void>>(new Map());
    const unmountedRef = useRef(false);  // Track if component is unmounted

    const connect = useCallback(() => {
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
            // Use tankId if provided, otherwise fall back to config
            const wsUrl = tankId ? config.getWsUrlForTank(tankId) : config.wsUrl;

            if (!wsUrl) {
                // No valid URL, cannot connect.
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
                        const update = data as SimulationUpdate;
                        // Normalize: Populate top-level fields from snapshot for convenience
                        if (update.snapshot) {
                            update.frame = update.snapshot.frame;
                            update.elapsed_time = update.snapshot.elapsed_time;
                            update.entities = update.snapshot.entities;
                            update.stats = update.snapshot.stats;
                            update.poker_events = update.snapshot.poker_events;
                            update.poker_leaderboard = update.snapshot.poker_leaderboard;
                            update.auto_evaluation = update.snapshot.auto_evaluation;
                        }
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
    }, [tankId]);

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
        /** Current tank ID (from state) */
        tankId: state?.tank_id ?? null,
    };
}

function applyDelta(state: SimulationUpdate, delta: DeltaUpdate): SimulationUpdate {
    // Optimization: Only create copies of entities that are actually modified.
    // Previously we spread-copied ALL entities every frame, creating ~45 objects x 30fps = 1350 allocations/sec.

    // Resolve delta inputs (support both nested snapshot and legacy fields)
    const updates = delta.snapshot?.updates ?? delta.updates ?? [];
    const added = delta.snapshot?.added ?? delta.added ?? [];
    const removed = delta.snapshot?.removed ?? delta.removed ?? [];

    // Resolve state inputs
    const currentEntities = state.snapshot?.entities ?? state.entities ?? [];

    // Build a set of IDs to remove for O(1) lookup
    const removedIds = new Set(removed);

    // Build a map of updates for O(1) lookup
    const updateMap = new Map(updates.map(u => [u.id, u]));

    // Filter out removed entities and update existing ones IN PLACE where possible
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
                };
            }
            // No update - reuse the same object reference
            return e;
        });

    // Add new entities
    added.forEach(entity => {
        // Only add if not already in the list (shouldn't happen but defensive)
        if (!entities.some(e => e.id === entity.id)) {
            entities.push(entity);
        }
    });

    // Resolve other fields
    const nextFrame = delta.snapshot?.frame ?? delta.frame ?? state.snapshot?.frame ?? state.frame ?? 0;
    const nextElapsedTime = delta.snapshot?.elapsed_time ?? delta.elapsed_time ?? state.snapshot?.elapsed_time ?? state.elapsed_time ?? 0;

    // Handle stats
    const nextStats = delta.snapshot?.stats ?? delta.stats ?? state.snapshot?.stats ?? state.stats!;

    // Handle poker events
    const deltaEvents = delta.snapshot?.poker_events ?? delta.poker_events;
    const currentEvents = state.snapshot?.poker_events ?? state.poker_events ?? [];
    const nextEvents = (deltaEvents && deltaEvents.length > 0) ? deltaEvents.slice(-100) : currentEvents;

    // Construct new snapshot if one exists or if we want to start maintaining one
    const nextSnapshot = state.snapshot ? {
        ...state.snapshot,
        frame: nextFrame,
        elapsed_time: nextElapsedTime,
        entities,
        stats: nextStats,
        poker_events: nextEvents,
        // Preserve leaderboard if not in delta (commonly isn't)
        poker_leaderboard: state.snapshot.poker_leaderboard,
    } : undefined;

    return {
        ...state,
        tank_id: delta.tank_id ?? state.tank_id,
        world_type: delta.world_type ?? state.world_type,
        view_mode: delta.view_mode ?? state.view_mode,
        mode_id: (delta as any).mode_id ?? (state as any).mode_id ?? 'tank',

        // Nested snapshot
        snapshot: nextSnapshot,

        // Sync flattened fields
        frame: nextFrame,
        elapsed_time: nextElapsedTime,
        entities,
        poker_events: nextEvents,
        stats: nextStats,
        // poker_leaderboard isn't usually in delta, so preserve state's
        poker_leaderboard: state.poker_leaderboard,
    };
}
