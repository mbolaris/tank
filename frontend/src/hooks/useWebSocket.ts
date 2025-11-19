/**
 * WebSocket hook for real-time simulation updates
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import type { SimulationUpdate, Command } from '../types/simulation';

const WS_URL = 'ws://localhost:8000/ws';

export function useWebSocket() {
  const [state, setState] = useState<SimulationUpdate | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const connectRef = useRef<(() => void) | null>(null);

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
          }
        } catch (error) {
          // Silently handle parsing errors
        }
      };

      ws.onerror = () => {
        // Silently handle WebSocket errors
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;

        // Attempt to reconnect after 3 seconds
        reconnectTimeoutRef.current = window.setTimeout(() => {
          if (connectRef.current) {
            connectRef.current();
          }
        }, 3000);
      };

      wsRef.current = ws;
    } catch (error) {
      // Silently handle WebSocket creation errors
    }
  }, []);

  // Store connect function in ref
  connectRef.current = connect;

  useEffect(() => {
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

  return {
    state,
    isConnected,
    sendCommand,
  };
}
