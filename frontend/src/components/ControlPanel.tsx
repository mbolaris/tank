/**
 * Control panel component with simulation controls
 */

import { useState } from 'react';
import type { Command } from '../types/simulation';
import { colors, commonStyles } from '../styles/theme';

interface ControlPanelProps {
  onCommand: (command: Command) => void;
  isConnected: boolean;
  onPlayPoker?: () => void;
  onAutoEvaluatePoker?: () => void;
}

export function ControlPanel({ onCommand, isConnected, onPlayPoker, onAutoEvaluatePoker }: ControlPanelProps) {
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

  const handleSpawnJellyfish = () => {
    onCommand({ command: 'spawn_jellyfish' });
  };

  const handlePlayPoker = () => {
    if (onPlayPoker) {
      onPlayPoker();
    }
  };

  const handleAutoEvaluatePoker = () => {
    if (onAutoEvaluatePoker) {
      onAutoEvaluatePoker();
    }
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Controls</h2>

      <div style={styles.status}>
        <div
          style={{
            ...styles.statusDot,
            backgroundColor: isConnected ? '#4ade80' : '#ef4444',
          }}
        />
        <span style={styles.statusText}>
          {isConnected ? 'Connected' : 'Disconnected'}
        </span>
      </div>

      <div style={styles.buttons}>
        <button
          onClick={handlePlayPoker}
          disabled={!isConnected}
          style={{
            ...styles.button,
            ...styles.buttonPoker,
          }}
        >
          🃏 Play Poker
        </button>

        <button
          onClick={handleAutoEvaluatePoker}
          disabled={!isConnected}
          style={{
            ...styles.button,
            ...styles.buttonEvaluate,
          }}
        >
          📊 Auto-Evaluate Skill
        </button>

        <button
          onClick={handleAddFood}
          disabled={!isConnected}
          style={{
            ...styles.button,
            ...styles.buttonPrimary,
          }}
        >
          🍔 Add Food
        </button>

        <button
          onClick={handleSpawnFish}
          disabled={!isConnected}
          style={{
            ...styles.button,
            ...styles.buttonSuccess,
          }}
        >
          🐟 Spawn Fish
        </button>

        <button
          onClick={handleSpawnJellyfish}
          disabled={!isConnected}
          style={{
            ...styles.button,
            ...styles.buttonSpecial,
          }}
        >
          🎰 Spawn Poker Jellyfish
        </button>

        <button
          onClick={handlePause}
          disabled={!isConnected}
          style={{
            ...styles.button,
            ...styles.buttonSecondary,
          }}
        >
          {isPaused ? '▶️ Resume' : '⏸️ Pause'}
        </button>

        <button
          onClick={handleReset}
          disabled={!isConnected}
          style={{
            ...styles.button,
            ...styles.buttonDanger,
          }}
        >
          🔄 Reset
        </button>
      </div>

      <div style={styles.help}>
        <h3 style={styles.helpTitle}>Controls</h3>
        <ul style={styles.helpList}>
          <li>
            <strong>Play Poker:</strong> Play poker against the top 3 fish
          </li>
          <li>
            <strong>Auto-Evaluate Skill:</strong> Test top fish against standard algorithm (100 hands)
          </li>
          <li>
            <strong>Add Food:</strong> Drop food into the tank
          </li>
          <li>
            <strong>Spawn Fish:</strong> Add a new fish with random genetics
          </li>
          <li>
            <strong>Spawn Poker Jellyfish:</strong> Add a static poker evaluator that plays fish
          </li>
          <li>
            <strong>Pause:</strong> Pause/resume the simulation
          </li>
          <li>
            <strong>Reset:</strong> Restart with fresh population
          </li>
        </ul>
      </div>
    </div>
  );
}

const styles = {
  container: commonStyles.panelContainer,
  title: commonStyles.panelTitle,
  status: {
    display: 'flex',
    alignItems: 'center',
    marginBottom: '16px',
  },
  statusDot: {
    width: '12px',
    height: '12px',
    borderRadius: '50%',
    marginRight: '8px',
  },
  statusText: {
    fontSize: '14px',
  },
  buttons: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
  },
  button: commonStyles.button,
  buttonPrimary: {
    backgroundColor: colors.buttonPrimary,
    color: '#ffffff',
  },
  buttonSuccess: {
    backgroundColor: colors.buttonSuccess,
    color: '#ffffff',
  },
  buttonSecondary: {
    backgroundColor: colors.buttonSecondary,
    color: '#ffffff',
  },
  buttonDanger: {
    backgroundColor: colors.buttonDanger,
    color: '#ffffff',
  },
  buttonSpecial: {
    backgroundColor: '#f59e0b',
    color: '#ffffff',
  },
  buttonPoker: {
    backgroundColor: '#8b5cf6',
    color: '#ffffff',
    fontWeight: 'bold',
  },
  buttonEvaluate: {
    backgroundColor: '#06b6d4',
    color: '#ffffff',
    fontWeight: 'bold',
  },
  help: {
    marginTop: '24px',
    padding: '16px',
    backgroundColor: colors.bgDark,
    borderRadius: '6px',
  },
  helpTitle: {
    margin: '0 0 12px 0',
    fontSize: '16px',
    fontWeight: 500,
  },
  helpList: {
    margin: 0,
    paddingLeft: '20px',
    fontSize: '13px',
    lineHeight: '1.6',
  },
};
