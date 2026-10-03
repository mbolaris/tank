/**
 * Control panel component with simulation controls
 */

import { memo, useEffect, useState, type ReactNode } from 'react';
import type { Command } from '../types/simulation';
import { Button, FoodIcon, FishIcon, PlayIcon, PauseIcon, FastForwardIcon, ResetIcon, EyeIcon, EyeOffIcon } from './ui';
import styles from './ControlPanel.module.css';

interface ControlPanelProps {
    onCommand: (command: Command) => void;
    isConnected: boolean;
    fastForwardEnabled?: boolean;
    showEffects?: boolean;
    onToggleEffects?: () => void;
    showSoccer?: boolean;
    onToggleSoccer?: () => void;
    viewOptions?: ReactNode;
    advancedOptions?: ReactNode;
}

// Memoized: its props change only on user action, but TankView re-renders
// on every WebSocket payload.
export const ControlPanel = memo(function ControlPanel({ onCommand, isConnected, fastForwardEnabled, showEffects, onToggleEffects, showSoccer, onToggleSoccer, viewOptions, advancedOptions }: ControlPanelProps) {
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
        <div className={`glass-panel ${styles.panel}`}>
            <div className={styles.group} role="group" aria-label="World actions">
                <span className={styles.groupLabel}>World actions</span>
                <div className={styles.buttons}>
                <Button onClick={handleAddFood} disabled={!isConnected} variant="primary">
                    <FoodIcon size={14} /> Add Food
                </Button>
                <Button onClick={handleSpawnFish} disabled={!isConnected} variant="success">
                    <FishIcon size={14} /> Spawn Fish
                </Button>
                </div>
            </div>

            {/* Playback Controls */}
            <div className={styles.group} role="group" aria-label="Simulation">
                <span className={styles.groupLabel}>Simulation</span>
                <div className={styles.buttons}>
                <Button onClick={handlePause} disabled={!isConnected} variant="secondary">
                    {isPaused ? <><PlayIcon size={12} /> Resume</> : <><PauseIcon size={12} /> Pause</>}
                </Button>
                <Button onClick={handleFastForward} disabled={!isConnected} variant={isFastForward ? 'special' : 'secondary'}>
                    <FastForwardIcon size={12} /> {isFastForward ? 'Normal' : 'Fast'}
                </Button>
                </div>
            </div>

            {/* View Options */}
            <div className={styles.group} role="group" aria-label="View">
                <span className={styles.groupLabel}>View</span>
                <div className={styles.buttons}>
                {onToggleEffects && (
                    <Button onClick={onToggleEffects} variant={showEffects ? 'primary' : 'secondary'}>
                        {showEffects ? <><EyeOffIcon size={14} /> Hide HUD</> : <><EyeIcon size={14} /> Show HUD</>}
                    </Button>
                )}

                {onToggleSoccer && (
                    <Button
                        onClick={onToggleSoccer}
                        variant={showSoccer ? 'primary' : 'secondary'}
                        title={showSoccer ? "Hide Ball and goals" : "Show Ball and goals"}
                        aria-label={showSoccer ? "Hide Ball and goals" : "Show Ball and goals"}
                        aria-pressed={Boolean(showSoccer)}
                    >
                        <span style={{ fontSize: '14px' }}>⚽</span> Soccer
                    </Button>
                )}
                {viewOptions}
                </div>
            </div>
            <details className={styles.advanced}>
                <summary>Advanced</summary>
                <div className={styles.advancedContent}>
                    {advancedOptions}
                    <Button onClick={handleReset} disabled={!isConnected} variant="danger">
                        <ResetIcon size={14} /> Reset world
                    </Button>
                </div>
            </details>
        </div>
    );
});
