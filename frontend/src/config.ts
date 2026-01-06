/**
 * Configuration for Tank World frontend
 *
 * This module provides centralized configuration for the application,
 * supporting Tank World Net where users can connect to multiple tanks.
 */

/**
 * Get the world ID from URL query parameter
 */
function getWorldIdFromUrl(): string | null {
    if (typeof window !== 'undefined') {
        const params = new URLSearchParams(window.location.search);
        return params.get('world') || params.get('tank');
    }
    return null;
}

/**
 * @deprecated Use getWorldIdFromUrl instead
 */
function getTankIdFromUrl(): string | null {
    return getWorldIdFromUrl();
}

/**
 * Get the base WebSocket URL (without world ID)
 */
function getBaseWebSocketUrl(): string {
    // Check URL query parameter for remote server connection
    if (typeof window !== 'undefined') {
        const params = new URLSearchParams(window.location.search);
        const serverUrl = params.get('server');
        if (serverUrl) {
            // Remove any /ws or /ws/{world_id} suffix to get base
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
 * 1. URL query parameter (?server=ws://... and/or ?world=uuid)
 * 2. Environment variable (VITE_WS_URL)
 * 3. Default to same host as page (for local development)
 */
function getWebSocketUrl(): string {
    const baseUrl = getBaseWebSocketUrl();
    const worldId = getWorldIdFromUrl();

    // If a specific world is requested, use /ws/world/{world_id}
    if (worldId) {
        return `${baseUrl}/ws/world/${worldId}`;
    }

    // Default: no world selected. The application must identify a world before connecting.
    return '';
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

    /** World ID from URL (if specified) */
    worldId: getWorldIdFromUrl(),

    /** @deprecated Use worldId instead */
    tankId: getTankIdFromUrl(),

    /** Get the current server URL (for display purposes) */
    get serverDisplay(): string {
        return this.apiBaseUrl.replace(/^https?:\/\//, '');
    },

    /**
     * Get WebSocket URL for a specific world
     * @param worldId - The world ID to connect to
     */
    getWsUrlForWorld(worldId: string): string {
        return `${getBaseWebSocketUrl()}/ws/world/${worldId}`;
    },

    /**
     * @deprecated Use getWsUrlForWorld instead
     */
    getWsUrlForTank(tankId: string): string {
        return `${getBaseWebSocketUrl()}/ws/world/${tankId}`;
    },

    /**
     * Get API URL for listing worlds
     */
    get worldsApiUrl(): string {
        return `${this.apiBaseUrl}/api/worlds`;
    },

    /**
     * Get API URL for default world ID
     */
    get defaultWorldIdUrl(): string {
        return `${this.apiBaseUrl}/api/worlds/default/id`;
    },

    /**
     * Get API URL for listing servers
     */
    get serversApiUrl(): string {
        return `${this.apiBaseUrl}/api/servers`;
    },
} as const;

export type Config = typeof config;

/**
 * Server information returned from the API
 */
export interface ServerInfo {
    server_id: string;
    hostname: string;
    host: string;
    port: number;
    status: 'online' | 'offline' | 'degraded';
    world_count: number;
    version: string;
    uptime_seconds: number;
    cpu_percent?: number;
    memory_mb?: number;
    is_local: boolean;
    platform?: string;
    architecture?: string;
    hardware_model?: string;
    logical_cpus?: number;
}

/**
 * Server with worlds list
 */
export interface ServerWithWorlds {
    server: ServerInfo;
    worlds: WorldStatus[];
}

/**
 * @deprecated Use ServerWithWorlds instead
 */
export interface ServerWithTanks {
    server: ServerInfo;
    tanks: WorldStatus[];
}

/**
 * World information returned from the API
 */
export interface WorldInfo {
    world_id: string;
    name: string;
    description: string;
    created_at: string;
    owner: string | null;
    server_id: string;
    is_public: boolean;
    allow_transfers: boolean;
}

/**
 * @deprecated Use WorldInfo instead
 */
export interface TankInfo extends WorldInfo {
    tank_id: string;
}

export interface WorldStatsSummary {
    fish_count: number;
    generation: number;
    max_generation: number;
    total_extinctions?: number;
    total_energy: number;
    fish_energy: number;
    plant_energy: number;
    poker_score?: number;
    poker_score_history?: number[];
    poker_elo?: number;
    poker_elo_history?: number[];
    poker_stats?: {
        total_games: number;
        total_wins: number;
        total_losses: number;
        total_ties: number;
        win_rate?: number;
        net_energy: number;
        total_energy_won: number;
        total_energy_lost: number;
    };
}

/**
 * @deprecated Use WorldStatsSummary instead
 */
export type TankStatsSummary = WorldStatsSummary;

/**
 * Tank status returned from the API
 */
/**
 * World status returned from the API (/api/worlds)
 * Matches backend WorldStatus
 */
export interface WorldStatus {
    world_id: string;
    world_type: string;
    mode_id: string;
    name: string;
    view_mode: string;
    persistent: boolean;
    frame_count: number;
    paused: boolean;
    description: string;
    // Optional compatibility fields if needed?
}

/**
 * Response from GET /api/worlds
 */
export interface WorldsListResponse {
    worlds: WorldStatus[];
    count: number;
}

