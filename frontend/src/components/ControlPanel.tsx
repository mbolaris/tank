/**
 * Control panel component with simulation controls
 */

import { useEffect, useState } from 'react';
import type { Command } from '../types/simulation';
import { Button } from './ui';
import styles from './ControlPanel.module.css';

interface ControlPanelProps {
    onCommand: (command: Command) => void;
    isConnected: boolean;
    onPlayPoker?: () => void;
    showTree?: boolean;
    onToggleTree?: () => void;
    fastForwardEnabled?: boolean;
    showEffects?: boolean;
    onToggleEffects?: () => void;
}

export function ControlPanel({ onCommand, isConnected, onPlayPoker, showTree, onToggleTree, fastForwardEnabled, showEffects, onToggleEffects }: ControlPanelProps) {
    const [isPaused, setIsPaused] = useState(false);
    const [isFastForward, setIsFastForward] = useState(false);

    useEffect(() => {
        setIsFastForward(Boolean(fastForwardEnabled));
    }, [fastForwardEnabled]);

    const handleAddFood = () => {
        onCommand({ command: 'add_food' });
    };

    const handleSpawnFish = () => {
        onCommand({ command: 'spawn_fish' });
    };

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
        onCommand({
            command: 'fast_forward',
            data: { enabled: newState }
        });
    };

    const handleReset = () => {
        onCommand({ command: 'reset' });
        setIsPaused(false);
        setIsFastForward(false);
    };

    const handlePlayPoker = () => {
        if (onPlayPoker) {
            onPlayPoker();
        }
    };

    return (
        <div className={styles.buttons}>
            <Button
                onClick={handlePlayPoker}
                disabled={!isConnected}
                variant="poker"
            >
                🃏 Play Poker
            </Button>

            <Button
                onClick={handleAddFood}
                disabled={!isConnected}
                variant="primary"
            >
                🍔 Add Food
            </Button>

            <Button
                onClick={handleSpawnFish}
                disabled={!isConnected}
                variant="success"
            >
                🐟 Spawn Fish
            </Button>

            <Button
                onClick={handlePause}
                disabled={!isConnected}
                variant="secondary"
            >
                {isPaused ? '▶️ Resume' : '⏸️ Pause'}
            </Button>

            <Button
                onClick={handleFastForward}
                disabled={!isConnected}
                variant={isFastForward ? 'special' : 'secondary'}
            >
                {isFastForward ? '⏩ Normal Speed' : '⏩ Fast Forward'}
            </Button>

            <Button
                onClick={handleReset}
                disabled={!isConnected}
                variant="danger"
            >
                🔄 Reset
            </Button>

            {onToggleTree && (
                <Button
                    onClick={onToggleTree}
                    variant={showTree ? 'primary' : 'secondary'}
                >
                    {showTree ? 'Hide Tree' : '🌳 Show Tree'}
                </Button>
            )}

            {onToggleEffects && (
                <Button
                    onClick={onToggleEffects}
                    variant={showEffects ? 'primary' : 'secondary'}
                >
                    {showEffects ? 'Hide Effects' : '✨ Show Effects'}
                </Button>
            )}
        </div>
    );
}
