/**
 * WebSocket hook for real-time simulation updates
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import type { SimulationUpdate, Command } from '../types/simulation';

const WS_URL = 'ws://localhost:8000/ws';
const WS_RECONNECT_DELAY = 3000; // 3 seconds

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
          console.error('WebSocket: Failed to parse message:', error, 'Data:', event.data);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket: Connection error:', error);
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;

        // Attempt to reconnect after delay
        reconnectTimeoutRef.current = window.setTimeout(() => {
          if (connectRef.current) {
            console.log(`WebSocket: Attempting to reconnect to ${WS_URL}...`);
            connectRef.current();
          }
        }, WS_RECONNECT_DELAY);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('WebSocket: Failed to create connection:', error);
      setIsConnected(false);
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
