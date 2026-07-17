import type { ConnectionStatus } from '../hooks/useWebSocket';

export const CONNECTION_STATUS_DISPLAY: Record<ConnectionStatus, { label: string; color: string }> = {
    live: { label: 'LIVE', color: 'var(--color-success)' },
    connecting: { label: 'CONNECTING', color: 'var(--color-primary)' },
    reconnecting: { label: 'RECONNECTING', color: 'var(--color-warning)' },
};
