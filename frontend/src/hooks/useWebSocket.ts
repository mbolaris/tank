/**
 * WebSocket hook for real-time simulation updates
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import type { SimulationUpdate, Command, CommandResponse } from '../types/simulation';

const WS_URL = 'ws://localhost:8000/ws';
const WS_RECONNECT_DELAY = 3000; // 3 seconds

export function useWebSocket() {
  const [state, setState] = useState<SimulationUpdate | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const connectRef = useRef<(() => void) | null>(null);
  const responseCallbacksRef = useRef<Map<string, (data: CommandResponse) => void>>(new Map());

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'update') {
            setState(data as SimulationUpdate);
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

        // Attempt to reconnect after delay
        reconnectTimeoutRef.current = window.setTimeout(() => {
          if (connectRef.current) {
            connectRef.current();
          }
        }, WS_RECONNECT_DELAY);
      };

      wsRef.current = ws;
    } catch {
      setIsConnected(false);
    }
  }, []);

  // Store connect function in ref without mutating during render
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    // WebSocket setup synchronizes with external server state
    // eslint-disable-next-line react-hooks/set-state-in-effect
    connect();

    return () => {
      // Cleanup on unmount
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
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
  };
}
