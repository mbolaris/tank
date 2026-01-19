/**
 * Control panel component with simulation controls
 */

import { useEffect, useState } from 'react';
import type { Command } from '../types/simulation';
import { Button, FoodIcon, FishIcon, PlayIcon, PauseIcon, FastForwardIcon, ResetIcon, EyeIcon, EyeOffIcon } from './ui';

interface ControlPanelProps {
    onCommand: (command: Command) => void;
    isConnected: boolean;
    fastForwardEnabled?: boolean;
    showEffects?: boolean;
    onToggleEffects?: () => void;
    showSoccer?: boolean;
    onToggleSoccer?: () => void;
}

export function ControlPanel({ onCommand, isConnected, fastForwardEnabled, showEffects, onToggleEffects, ...props }: ControlPanelProps & { showSoccer?: boolean, onToggleSoccer?: () => void }) {
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
                    <FoodIcon size={14} /> Add Food
                </Button>
                <Button onClick={handleSpawnFish} disabled={!isConnected} variant="success">
                    <FishIcon size={14} /> Spawn Fish
                </Button>
            </div>

            {/* Playback Controls */}
            <div style={{ display: 'flex', gap: '12px' }}>
                <Button onClick={handlePause} disabled={!isConnected} variant="secondary">
                    {isPaused ? <><PlayIcon size={12} /> Resume</> : <><PauseIcon size={12} /> Pause</>}
                </Button>
                <Button onClick={handleFastForward} disabled={!isConnected} variant={isFastForward ? 'special' : 'secondary'}>
                    <FastForwardIcon size={12} /> {isFastForward ? 'Normal' : 'Fast'}
                </Button>
                <Button onClick={handleReset} disabled={!isConnected} variant="danger">
                    <ResetIcon size={14} /> Reset
                </Button>
            </div>

            {/* View Options */}
            <div style={{ display: 'flex', gap: '12px' }}>
                {onToggleEffects && (
                    <Button onClick={onToggleEffects} variant={showEffects ? 'primary' : 'secondary'}>
                        {showEffects ? <><EyeOffIcon size={14} /> Hide HUD</> : <><EyeIcon size={14} /> Show HUD</>}
                    </Button>
                )}

                {props.onToggleSoccer && (
                    <Button onClick={props.onToggleSoccer} variant={props.showSoccer ? 'primary' : 'secondary'} title={props.showSoccer ? "Hide Ball/Goals" : "Show Ball/Goals"}>
                        <span style={{ fontSize: '14px' }}>⚽</span>
                    </Button>
                )}
            </div>
        </div>
    );
}

