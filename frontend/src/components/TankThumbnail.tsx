import { useMemo, useState, useEffect } from 'react';
import { Canvas } from './Canvas';
import { config } from '../config';
import type { SimulationUpdate } from '../types/simulation';

interface TankThumbnailProps {
    tankId: string;
    status: 'running' | 'paused' | 'stopped';
}

export function TankThumbnail({ tankId, status }: TankThumbnailProps) {
    const [state, setState] = useState<SimulationUpdate | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const badge = useMemo(() => {
        if (status === 'stopped') {
            return { label: 'Stopped', color: '#ef4444' };
        }
        if (status === 'paused') {
            return { label: 'Paused', color: '#f59e0b' };
        }
        return { label: 'Live', color: '#22c55e' };
    }, [status]);

    // Fetch snapshot periodically via REST API (no WebSocket!)
    useEffect(() => {
        let mounted = true;

        const fetchSnapshot = async () => {
            try {
                const response = await fetch(`${config.apiBaseUrl}/api/tanks/${tankId}/snapshot`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                if (mounted) {
                    const data = await response.json();
                    // Validate data has required fields
                    if (data && data.entities && Array.isArray(data.entities)) {
                        setState(data);
                        setError(null);
                    } else {
                        throw new Error('Invalid snapshot data');
                    }
                    setLoading(false);
                }
            } catch (err) {
                // On error, keep showing last known state
                if (mounted) {
                    setError(err instanceof Error ? err.message : 'Failed to load');
                    setLoading(false);
                }
            }
        };

        // Fetch immediately
        fetchSnapshot();

        // Then fetch every 2 seconds for infrequent updates
        const interval = setInterval(fetchSnapshot, 2000);

        return () => {
            mounted = false;
            clearInterval(interval);
        };
    }, [tankId]);

    return (
        <div style={{ position: 'relative' }}>
            <div style={{
                borderRadius: '10px',
                overflow: 'hidden',
                border: '1px solid #334155',
                backgroundColor: '#0f172a',
                minHeight: '180px',
            }}>
                {loading ? (
                    <div style={{
                        height: '180px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#64748b',
                        fontSize: '14px',
                    }}>
                        Loading preview...
                    </div>
                ) : state ? (
                    <Canvas state={state} width={320} height={180} />
                ) : (
                    <div style={{
                        height: '180px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#ef4444',
                        fontSize: '12px',
                    }}>
                        {error || 'No data'}
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
