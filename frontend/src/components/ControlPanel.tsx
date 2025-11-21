/**
 * Control panel component with simulation controls
 */

import { useState } from 'react';
import type { Command } from '../types/simulation';
import { Panel, Button } from './ui';
import styles from './ControlPanel.module.css';

interface ControlPanelProps {
    onCommand: (command: Command) => void;
    isConnected: boolean;
    onPlayPoker?: () => void;
}

export function ControlPanel({ onCommand, isConnected, onPlayPoker }: ControlPanelProps) {
    const [isPaused, setIsPaused] = useState(false);

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

    const handleReset = () => {
        onCommand({ command: 'reset' });
        setIsPaused(false);
    };

    const handlePlayPoker = () => {
        if (onPlayPoker) {
            onPlayPoker();
        }
    };

    return (
        <Panel title="Controls">
            <div className={styles.status}>
                <div
                    className={styles.statusDot}
                    style={{
                        backgroundColor: isConnected ? '#4ade80' : '#ef4444',
                    }}
                />
                <span className={styles.statusText}>
                    {isConnected ? 'Connected' : 'Disconnected'}
                </span>
            </div>

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
                    onClick={handleReset}
                    disabled={!isConnected}
                    variant="danger"
                >
                    🔄 Reset
                </Button>
            </div>
        </Panel>
    );
}
