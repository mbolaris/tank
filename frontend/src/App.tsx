/**
 * Main App component
 */

import { useWebSocket } from './hooks/useWebSocket';
import { Canvas } from './components/Canvas';
import { ControlPanel } from './components/ControlPanel';
import { StatsPanel } from './components/StatsPanel';
import PokerEvents from './components/PokerEvents';
import { PokerLeaderboard } from './components/PokerLeaderboard';
import { PhylogeneticTree } from './components/PhylogeneticTree';
import './App.css';

function App() {
  const { state, isConnected, sendCommand } = useWebSocket();

  return (
    <div className="app">
      <header className="header">
        <h1 className="title">Tank World Evolution via Pull Request</h1>
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
        </div>

        <div className="sidebar">
          <ControlPanel onCommand={sendCommand} isConnected={isConnected} />
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
