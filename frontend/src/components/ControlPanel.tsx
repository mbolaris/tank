/**
 * Control panel component with simulation controls
 */

import { useState } from 'react';
import type { Command } from '../types/simulation';

interface ControlPanelProps {
  onCommand: (command: Command) => void;
  isConnected: boolean;
}

export function ControlPanel({ onCommand, isConnected }: ControlPanelProps) {
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
            <strong>Add Food:</strong> Drop food into the tank
          </li>
          <li>
            <strong>Spawn Fish:</strong> Add a new fish with random genetics
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
  container: {
    padding: '24px',
    background: 'linear-gradient(145deg, rgba(30,41,59,0.92), rgba(15,23,42,0.95))',
    borderRadius: '20px',
    color: '#e2e8f0',
    border: '1px solid rgba(148,163,184,0.18)',
    boxShadow: '0 35px 55px rgba(2,6,23,0.65)',
  },
  title: {
    margin: '0 0 16px 0',
    fontSize: '20px',
    fontWeight: 600,
  },
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
  button: {
    padding: '12px 16px',
    fontSize: '14px',
    fontWeight: 500,
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    boxShadow: '0 10px 25px rgba(15,23,42,0.45)',
  },
  buttonPrimary: {
    backgroundColor: '#3b82f6',
    color: '#ffffff',
  },
  buttonSuccess: {
    backgroundColor: '#10b981',
    color: '#ffffff',
  },
  buttonSecondary: {
    backgroundColor: '#8b5cf6',
    color: '#ffffff',
  },
  buttonDanger: {
    backgroundColor: '#ef4444',
    color: '#ffffff',
  },
  help: {
    marginTop: '24px',
    padding: '16px',
    backgroundColor: '#0f172a',
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
