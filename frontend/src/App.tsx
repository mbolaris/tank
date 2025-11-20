/**
 * Main App component
 */

import { useState } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { Canvas } from './components/Canvas';
import { ControlPanel } from './components/ControlPanel';
import { StatsPanel } from './components/StatsPanel';
import PokerEvents from './components/PokerEvents';
import { PokerLeaderboard } from './components/PokerLeaderboard';
import { PhylogeneticTree } from './components/PhylogeneticTree';
import { PokerGame } from './components/PokerGame';
import { AutoEvaluateDisplay } from './components/AutoEvaluateDisplay';
import type { PokerGameState, AutoEvaluateStats } from './types/simulation';
import './App.css';

function App() {
  const { state, isConnected, sendCommand, sendCommandWithResponse } = useWebSocket();
  const [pokerGameState, setPokerGameState] = useState<PokerGameState | null>(null);
  const [showPokerGame, setShowPokerGame] = useState(false);
  const [pokerLoading, setPokerLoading] = useState(false);

  // Auto-evaluation state
  const [autoEvaluateStats, setAutoEvaluateStats] = useState<AutoEvaluateStats | null>(null);
  const [showAutoEvaluate, setShowAutoEvaluate] = useState(false);
  const [autoEvaluateLoading, setAutoEvaluateLoading] = useState(false);

  const handleStartPoker = async () => {
    try {
      setPokerLoading(true);
      setShowPokerGame(true);

      const response = await sendCommandWithResponse({
        command: 'start_poker',
        data: { energy: 500 },
      });

      if (response.success === false) {
        alert(response.error || 'Failed to start poker game');
        setShowPokerGame(false);
      } else if (response.state) {
        setPokerGameState(response.state);
      }
    } catch (error) {
      alert('Failed to start poker game. Please try again.');
      setShowPokerGame(false);
    } finally {
      setPokerLoading(false);
    }
  };

  const handlePokerAction = async (action: string, amount?: number) => {
    try {
      setPokerLoading(true);

      const response = await sendCommandWithResponse({
        command: 'poker_action',
        data: { action, amount: amount || 0 },
      });

      if (response.success === false) {
        alert(response.error || 'Invalid action');
      } else if (response.state) {
        setPokerGameState(response.state);
      }
    } catch (error) {
      alert('Failed to send action. Please try again.');
    } finally {
      setPokerLoading(false);
    }
  };

  const handleClosePoker = () => {
    setShowPokerGame(false);
    setPokerGameState(null);
  };

  const handleAutoEvaluatePoker = async () => {
    try {
      setAutoEvaluateLoading(true);
      setShowAutoEvaluate(true);

      const response = await sendCommandWithResponse({
        command: 'auto_evaluate_poker',
        data: { standard_energy: 500, max_hands: 1000 },
      });

      if (response.success === false) {
        alert(response.error || 'Failed to run auto-evaluation');
        setShowAutoEvaluate(false);
      } else if (response.stats) {
        setAutoEvaluateStats(response.stats);
      }
    } catch (error) {
      alert('Failed to run auto-evaluation. Please try again.');
      setShowAutoEvaluate(false);
    } finally {
      setAutoEvaluateLoading(false);
    }
  };

  const handleCloseAutoEvaluate = () => {
    setShowAutoEvaluate(false);
    setAutoEvaluateStats(null);
  };

  return (
    <div className="app">
      <header className="header">
        <h1 className="title">Tank World</h1>
        <p className="subtitle">
          An ecosystem where fish play Poker for energy and an autonomous AI rewrites their source code to ensure survival.
        </p>
      </header>

      <main className="main">
        <div className="canvas-section">
          <div className="canvas-wrapper">
            <div className="canvas-meta">
              <div>
                <p className="canvas-label">Simulation</p>
                <p className="canvas-value">
                  {state?.stats?.frame ? state.stats.frame.toLocaleString() : '—'}{' '}
                  <span>frames</span>
                </p>
              </div>
              <div>
                <p className="canvas-label">Population</p>
                <p className="canvas-value">
                  {state?.stats?.fish_count ?? 0}
                  <span> fish</span>
                </p>
              </div>
              <div>
                <p className="canvas-label">Status</p>
                <p className={`canvas-status ${isConnected ? 'online' : 'offline'}`}>
                  {isConnected ? 'Connected' : 'Waiting'}
                </p>
              </div>
            </div>
            <Canvas state={state} width={800} height={600} />
            <div className="canvas-glow" aria-hidden />
          </div>
          <PokerEvents
            events={state?.poker_events ?? []}
            currentFrame={state?.frame ?? 0}
          />
          <PokerLeaderboard leaderboard={state?.poker_leaderboard ?? []} />
          <div style={{ marginTop: '20px' }}>
            <h2 style={{ color: '#00ff00', marginBottom: '10px', fontSize: '20px' }}>
              Phylogenetic Tree
            </h2>
            <PhylogeneticTree />
          </div>

          {/* Poker Game */}
          {showPokerGame && (
            <div style={{ marginTop: '20px', width: '100%', maxWidth: '820px' }}>
              <PokerGame
                onClose={handleClosePoker}
                onAction={handlePokerAction}
                gameState={pokerGameState}
                loading={pokerLoading}
              />
            </div>
          )}

          {/* Auto-Evaluation Display */}
          {showAutoEvaluate && (
            <div style={{ marginTop: '20px', width: '100%', maxWidth: '820px' }}>
              <AutoEvaluateDisplay
                stats={autoEvaluateStats}
                onClose={handleCloseAutoEvaluate}
                loading={autoEvaluateLoading}
              />
            </div>
          )}
        </div>

        <div className="sidebar">
          <ControlPanel
            onCommand={sendCommand}
            isConnected={isConnected}
            onPlayPoker={handleStartPoker}
            onAutoEvaluatePoker={handleAutoEvaluatePoker}
          />
          <StatsPanel stats={state?.stats ?? null} />
        </div>
      </main>

      <footer className="footer">
        <p>
          Built with React + FastAPI + WebSocket | Running at ~30 FPS
        </p>
      </footer>
    </div>
  );
}

export default App;
