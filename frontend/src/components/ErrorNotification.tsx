/**
 * Component for displaying error notifications to users
 * Shows errors in a fixed position with auto-dismiss functionality
 */

import type { ErrorNotification as ErrorNotificationType } from '../hooks/useErrorNotification';

interface ErrorNotificationProps {
    errors: ErrorNotificationType[];
    onDismiss: (timestamp: number) => void;
}

export function ErrorNotification({ errors, onDismiss }: ErrorNotificationProps) {
    if (errors.length === 0) return null;

    return (
        <div style={{
            position: 'fixed',
            top: 20,
            right: 20,
            zIndex: 10000,
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
            maxWidth: 400
        }}>
            {errors.map(error => (
                <div
                    key={error.timestamp}
                    style={{
                        backgroundColor: '#dc2626',
                        color: 'white',
                        padding: '12px 16px',
                        borderRadius: 8,
                        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)',
                        display: 'flex',
                        alignItems: 'start',
                        gap: 12
                    }}
                >
                    <div style={{ flex: 1, fontSize: 14 }}>
                        <div style={{ fontWeight: 600, marginBottom: 4 }}>Error</div>
                        <div style={{ opacity: 0.9 }}>{error.message}</div>
                    </div>
                    <button
                        onClick={() => onDismiss(error.timestamp)}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'white',
                            cursor: 'pointer',
                            fontSize: 20,
                            lineHeight: 1,
                            padding: 0,
                            opacity: 0.7
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                        onMouseLeave={(e) => e.currentTarget.style.opacity = '0.7'}
                    >
                        ×
                    </button>
                </div>
            ))}
        </div>
    );
}
