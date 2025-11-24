/**
 * Configuration for Tank World frontend
 *
 * This module provides centralized configuration for the application,
 * supporting Tank World Net where users can connect to multiple tanks.
 */

/**
 * Get the tank ID from URL query parameter
 */
function getTankIdFromUrl(): string | null {
  if (typeof window !== 'undefined') {
    const params = new URLSearchParams(window.location.search);
    return params.get('tank');
  }
  return null;
}

/**
 * Get the base WebSocket URL (without tank ID)
 */
function getBaseWebSocketUrl(): string {
  // Check URL query parameter for remote server connection
  if (typeof window !== 'undefined') {
    const params = new URLSearchParams(window.location.search);
    const serverUrl = params.get('server');
    if (serverUrl) {
      // Remove any /ws or /ws/{tank_id} suffix to get base
      return serverUrl.replace(/\/ws(\/[^/]+)?$/, '');
    }
  }

  // Check environment variable
  const envUrl = import.meta.env.VITE_WS_URL;
  if (envUrl) {
    return envUrl.replace(/\/ws(\/[^/]+)?$/, '');
  }

  // Default: connect to same host as the page
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const port = import.meta.env.VITE_WS_PORT || '8000';
    return `${protocol}//${host}:${port}`;
  }

  // Fallback for SSR or tests
  return 'ws://localhost:8000';
}

/**
 * Determine WebSocket URL based on environment
 *
 * Priority order:
 * 1. URL query parameter (?server=ws://... and/or ?tank=uuid)
 * 2. Environment variable (VITE_WS_URL)
 * 3. Default to same host as page (for local development)
 */
function getWebSocketUrl(): string {
  const baseUrl = getBaseWebSocketUrl();
  const tankId = getTankIdFromUrl();

  // If a specific tank is requested, use /ws/{tank_id}
  if (tankId) {
    return `${baseUrl}/ws/${tankId}`;
  }

  // Default: use /ws (connects to default tank)
  return `${baseUrl}/ws`;
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

  /** Tank ID from URL (if specified) */
  tankId: getTankIdFromUrl(),

  /** Get the current server URL (for display purposes) */
  get serverDisplay(): string {
    return this.apiBaseUrl.replace(/^https?:\/\//, '');
  },

  /**
   * Get WebSocket URL for a specific tank
   * @param tankId - The tank ID to connect to
   */
  getWsUrlForTank(tankId: string): string {
    return `${getBaseWebSocketUrl()}/ws/${tankId}`;
  },

  /**
   * Get API URL for listing tanks
   */
  get tanksApiUrl(): string {
    return `${this.apiBaseUrl}/api/tanks`;
  },
} as const;

export type Config = typeof config;

/**
 * Tank information returned from the API
 */
export interface TankInfo {
  tank_id: string;
  name: string;
  description: string;
  created_at: string;
  owner: string | null;
  is_public: boolean;
  allow_transfers: boolean;
}

export interface TankStatsSummary {
  fish_count: number;
  generation: number;
  max_generation: number;
  total_energy: number;
  fish_energy: number;
  plant_energy: number;
}

/**
 * Tank status returned from the API
 */
export interface TankStatus {
  tank: TankInfo;
  running: boolean;
  client_count: number;
  frame: number;
  paused: boolean;
  stats?: TankStatsSummary;
}

/**
 * Response from GET /api/tanks
 */
export interface TanksListResponse {
  tanks: TankStatus[];
  count: number;
  default_tank_id: string;
}
