/**
 * Control panel component with simulation controls
 */

import { useEffect, useState } from 'react';
import type { Command } from '../types/simulation';
import { Button } from './ui';

interface ControlPanelProps {
    onCommand: (command: Command) => void;
    isConnected: boolean;
    fastForwardEnabled?: boolean;
    showEffects?: boolean;
    onToggleEffects?: () => void;
}

export function ControlPanel({ onCommand, isConnected, fastForwardEnabled, showEffects, onToggleEffects }: ControlPanelProps) {
    const [isPaused, setIsPaused] = useState(false);
    const [isFastForward, setIsFastForward] = useState(false);

    useEffect(() => {
        setIsFastForward(Boolean(fastForwardEnabled));
    }, [fastForwardEnabled]);

    const handleAddFood = () => onCommand({ command: 'add_food' });
    const handleSpawnFish = () => onCommand({ command: 'spawn_fish' });

    const handlePause = () => {
        if (isPaused) {
            onCommand({ command: 'resume' });
            setIsPaused(false);
        } else {
            onCommand({ command: 'pause' });
            setIsPaused(true);
        }
    };

    const handleFastForward = () => {
        const newState = !isFastForward;
        setIsFastForward(newState);
        onCommand({ command: 'fast_forward', data: { enabled: newState } });
    };

    const handleReset = () => {
        onCommand({ command: 'reset' });
        setIsPaused(false);
        setIsFastForward(false);
    };

    return (
        <div className="glass-panel" style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '12px 24px',
            width: '100%',
            gap: '24px',
        }}>
            {/* Primary Actions */}
            <div style={{ display: 'flex', gap: '12px' }}>
                <Button onClick={handleAddFood} disabled={!isConnected} variant="primary">
                    🍔 Add Food
                </Button>
                <Button onClick={handleSpawnFish} disabled={!isConnected} variant="success">
                    🐟 Spawn Fish
                </Button>
            </div>

            {/* Playback Controls */}
            <div style={{ display: 'flex', gap: '12px' }}>
                <Button onClick={handlePause} disabled={!isConnected} variant="secondary">
                    {isPaused ? '▶️ Resume' : '⏸️ Pause'}
                </Button>
                <Button onClick={handleFastForward} disabled={!isConnected} variant={isFastForward ? 'special' : 'secondary'}>
                    {isFastForward ? '⏩ Normal' : '⏩ Fast'}
                </Button>
                <Button onClick={handleReset} disabled={!isConnected} variant="danger">
                    🔄 Reset
                </Button>
            </div>

            {/* View Options */}
            <div style={{ display: 'flex', gap: '12px' }}>
                {onToggleEffects && (
                    <Button onClick={onToggleEffects} variant={showEffects ? 'primary' : 'secondary'}>
                        {showEffects ? 'Hide HUD' : '📊 HUD'}
                    </Button>
                )}
            </div>
        </div>
    );
}
