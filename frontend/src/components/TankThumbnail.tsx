import { useMemo } from 'react';
import { Canvas } from './Canvas';
import { useWebSocket } from '../hooks/useWebSocket';

interface TankThumbnailProps {
    tankId: string;
    status: 'running' | 'paused' | 'stopped';
}

export function TankThumbnail({ tankId, status }: TankThumbnailProps) {
    const { state, isConnected } = useWebSocket(tankId);

    const badge = useMemo(() => {
        if (status === 'stopped') {
            return { label: 'Stopped', color: '#ef4444' };
        }
        if (status === 'paused') {
            return { label: 'Paused', color: '#f59e0b' };
        }
        return { label: 'Live', color: '#22c55e' };
    }, [status]);

    // Show error state if disconnected and no state yet
    const showError = !isConnected && !state;

    return (
        <div style={{ position: 'relative' }}>
            <div style={{
                borderRadius: '10px',
                overflow: 'hidden',
                border: '1px solid #334155',
                backgroundColor: '#0f172a',
            }}>
                <Canvas state={state} width={320} height={180} />
                {showError && (
                    <div style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        backgroundColor: '#0f172add',
                        color: '#ef4444',
                        fontSize: 12,
                        fontWeight: 600,
                    }}>
                        Connection Lost
                    </div>
                )}
            </div>
            <span style={{
                position: 'absolute',
                top: 8,
                left: 8,
                padding: '4px 8px',
                borderRadius: '9999px',
                backgroundColor: '#0f172acc',
                color: badge.color,
                fontSize: 12,
                fontWeight: 700,
                border: `1px solid ${badge.color}66`,
            }}>
                {badge.label}
            </span>
        </div>
    );
}
