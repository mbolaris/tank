/**
 * Control panel component with simulation controls
 */

import { memo, useEffect, useRef, useState, type ReactNode } from 'react';
import type { Command, CommandResponse } from '../types/simulation';
import { Button, FoodIcon, FishIcon, PlayIcon, PauseIcon, FastForwardIcon, ResetIcon, EyeIcon, EyeOffIcon } from './ui';
import styles from './ControlPanel.module.css';

interface ControlPanelProps {
    onCommand: (command: Command) => void;
    isConnected: boolean;
    paused?: boolean;
    onPauseCommand?: (command: Command) => Promise<CommandResponse>;
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
export const ControlPanel = memo(function ControlPanel({ onCommand, isConnected, paused, onPauseCommand, fastForwardEnabled, showEffects, onToggleEffects, showSoccer, onToggleSoccer, viewOptions, advancedOptions }: ControlPanelProps) {
    const [isFastForward, setIsFastForward] = useState(false);

    useEffect(() => {
        setIsFastForward(Boolean(fastForwardEnabled));
    }, [fastForwardEnabled]);

    const handleAddFood = () => onCommand({ command: 'add_food' });
    const handleSpawnFish = () => onCommand({ command: 'spawn_fish' });

    const handleFastForward = () => {
        const newState = !isFastForward;
        setIsFastForward(newState);
        onCommand({ command: 'fast_forward', data: { enabled: newState } });
    };

    const handleReset = () => {
        onCommand({ command: 'reset' });
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
                <PauseControl paused={paused} isConnected={isConnected} send={onPauseCommand} />
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

function PauseControl({ paused, isConnected, send }: { paused?: boolean; isConnected: boolean; send?: (command: Command) => Promise<CommandResponse> }) {
    const [pending, setPending] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const flight = useRef(0);
    const busy = useRef(false);
    useEffect(() => {
        const lifetime = flight;
        const pendingCommand = busy;
        if (!isConnected) {
            busy.current = false;
            setPending(false);
        }
        return () => { lifetime.current++; pendingCommand.current = false; };
    }, [isConnected]);
    const toggle = async () => {
        if (!send || busy.current || paused === undefined || !isConnected) return;
        const token = ++flight.current;
        busy.current = true;
        setPending(true);
        setError(null);
        try {
            const response = await send({ command: paused ? 'resume' : 'pause' });
            if (!response.success || typeof response.paused !== 'boolean') {
                throw new Error(response.error || 'Pause command was not acknowledged');
            }
            // The shared server snapshot owns the button label, including
            // commands from other clients. An acknowledgement only ends flight.
        } catch (e) {
            if (flight.current === token) setError(e instanceof Error ? e.message : 'Pause failed');
        } finally {
            if (flight.current === token) { busy.current = false; setPending(false); }
        }
    };
    return <>
        <Button onClick={toggle} disabled={!isConnected || paused === undefined || !send || pending} variant="secondary">
            {pending ? 'Waiting…' : paused ? <><PlayIcon size={12} /> Resume</> : <><PauseIcon size={12} /> Pause</>}
        </Button>
        {error && <span role="alert">{error}</span>}
    </>;
}
