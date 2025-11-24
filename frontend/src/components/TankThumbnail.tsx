import { useMemo } from 'react';
import { Canvas } from './Canvas';
import { useWebSocket } from '../hooks/useWebSocket';

interface TankThumbnailProps {
    tankId: string;
    status: 'running' | 'paused' | 'stopped';
}

export function TankThumbnail({ tankId, status }: TankThumbnailProps) {
    const { state } = useWebSocket(tankId);

    const badge = useMemo(() => {
        if (status === 'stopped') {
            return { label: 'Stopped', color: '#ef4444' };
        }
        if (status === 'paused') {
            return { label: 'Paused', color: '#f59e0b' };
        }
        return { label: 'Live', color: '#22c55e' };
    }, [status]);

    return (
        <div style={{ position: 'relative' }}>
            <div style={{
                borderRadius: '10px',
                overflow: 'hidden',
                border: '1px solid #334155',
                backgroundColor: '#0f172a',
            }}>
                <Canvas state={state} width={320} height={180} />
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
