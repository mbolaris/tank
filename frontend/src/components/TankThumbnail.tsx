import { useMemo, useState, useEffect } from 'react';
import { Canvas } from './Canvas';
import { config } from '../config';
import { useViewMode } from '../hooks/useViewMode';
import type { SimulationUpdate } from '../types/simulation';

const TANK_ASPECT_RATIO = '1088 / 612';

interface TankThumbnailProps {
    tankId: string;
    status: 'running' | 'paused' | 'stopped';
}

export function TankThumbnail({ tankId, status }: TankThumbnailProps) {
    const [state, setState] = useState<SimulationUpdate | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const { effectiveViewMode } = useViewMode();

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
                    // Validate data has required fields (check both nested and legacy locations)
                    const entities = data?.snapshot?.entities ?? data?.entities;
                    if (data && entities && Array.isArray(entities)) {
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

        // Then fetch periodically to avoid overwhelming the browser
        const interval = setInterval(fetchSnapshot, 2000); // Update every 2 seconds

        return () => {
            mounted = false;
            clearInterval(interval);
        };
    }, [tankId]);

    const containerStyle = {
        position: 'relative' as const,
        borderRadius: '10px',
        overflow: 'hidden',
        border: '1px solid #334155',
        backgroundColor: '#0f172a',
        aspectRatio: TANK_ASPECT_RATIO,
        width: '100%',
    };

    const overlayStyle = {
        position: 'absolute' as const,
        inset: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
    };

    return (
        <div style={{ position: 'relative' }}>
            <div style={containerStyle}>
                {loading ? (
                    <div
                        style={{
                            ...overlayStyle,
                            color: '#64748b',
                            fontSize: '14px',
                        }}
                    >
                        Loading preview...
                    </div>
                ) : state ? (
                    <Canvas
                        state={state}
                        width={320}
                        height={180}
                        showEffects={false}
                        viewMode={effectiveViewMode}
                        style={{ width: '100%', height: '100%', display: 'block' }}
                    />
                ) : (
                    <div
                        style={{
                            ...overlayStyle,
                            color: '#ef4444',
                            fontSize: '12px',
                        }}
                    >
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
