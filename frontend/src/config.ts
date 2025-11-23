/**
 * Configuration for Tank World frontend
 *
 * This module provides centralized configuration for the application,
 * preparing for Tank World Net where users can connect to remote tanks.
 */

/**
 * Determine WebSocket URL based on environment
 *
 * Priority order:
 * 1. URL query parameter (?server=ws://...)
 * 2. Environment variable (VITE_WS_URL)
 * 3. Default to same host as page (for local development)
 */
function getWebSocketUrl(): string {
  // Check URL query parameter for remote tank connection
  if (typeof window !== 'undefined') {
    const params = new URLSearchParams(window.location.search);
    const serverUrl = params.get('server');
    if (serverUrl) {
      return serverUrl;
    }
  }

  // Check environment variable
  const envUrl = import.meta.env.VITE_WS_URL;
  if (envUrl) {
    return envUrl;
  }

  // Default: connect to same host as the page
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const port = import.meta.env.VITE_WS_PORT || '8000';
    return `${protocol}//${host}:${port}/ws`;
  }

  // Fallback for SSR or tests
  return 'ws://localhost:8000/ws';
}

/**
 * Determine API base URL based on environment
 */
function getApiBaseUrl(): string {
  // Check URL query parameter
  if (typeof window !== 'undefined') {
    const params = new URLSearchParams(window.location.search);
    const serverUrl = params.get('server');
    if (serverUrl) {
      // Convert ws:// to http://
      return serverUrl.replace(/^wss?:/, 'http:').replace(/\/ws$/, '');
    }
  }

  // Check environment variable
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl) {
    return envUrl;
  }

  // Default: connect to same host as the page
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    const port = import.meta.env.VITE_API_PORT || '8000';
    return `http://${host}:${port}`;
  }

  // Fallback
  return 'http://localhost:8000';
}

export const config = {
  /** WebSocket URL for real-time simulation updates */
  wsUrl: getWebSocketUrl(),

  /** API base URL for HTTP endpoints */
  apiBaseUrl: getApiBaseUrl(),

  /** WebSocket reconnect delay in milliseconds */
  wsReconnectDelay: 3000,

  /** Get the current server URL (for display purposes) */
  get serverDisplay(): string {
    return this.apiBaseUrl.replace(/^https?:\/\//, '');
  },
} as const;

export type Config = typeof config;
