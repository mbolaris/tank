/**
 * WebSocket hook for real-time simulation updates
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import type { SimulationUpdate, Command, CommandResponse, DeltaUpdate } from '../types/simulation';
import { config } from '../config';

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
                        jsonString = new TextDecoder().decode(event.data);
                    } else {
                        jsonString = event.data;
                    }
                    const data = JSON.parse(jsonString);

                    if (data.type === 'update') {
                        setState(data as SimulationUpdate);
                    } else if (data.type === 'delta') {
                        setState((current) => (current ? applyDelta(current, data as DeltaUpdate) : current));
                    } else if (data.success !== undefined || data.state !== undefined || data.error !== undefined) {
                        // This is a command response (e.g., poker game state)
                        // Call any pending callbacks
                        responseCallbacksRef.current.forEach((callback) => callback(data));
                        responseCallbacksRef.current.clear();
                    }
                } catch {
                    // Silently ignore parse errors - malformed data
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
        } catch {
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
        // eslint-disable-next-line react-hooks/set-state-in-effect
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
    const entityMap = new Map(state.entities.map((e) => [e.id, { ...e }]));

    delta.removed.forEach((id) => entityMap.delete(id));
    delta.added.forEach((entity) => entityMap.set(entity.id, entity));

    delta.updates.forEach((update) => {
        const existing = entityMap.get(update.id);
        if (existing) {
            existing.x = update.x;
            existing.y = update.y;
            existing.vel_x = update.vel_x;
            existing.vel_y = update.vel_y;
            if (update.poker_effect_state !== undefined) {
                existing.poker_effect_state = update.poker_effect_state;
            }
        }
    });

    return {
        ...state,
        tank_id: delta.tank_id ?? state.tank_id,
        frame: delta.frame,
        elapsed_time: delta.elapsed_time,
        entities: Array.from(entityMap.values()),
        poker_events: delta.poker_events?.length ? delta.poker_events : state.poker_events,
        stats: delta.stats ?? state.stats,
    };
}
