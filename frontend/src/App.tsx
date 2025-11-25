/**
 * Main App component with routing
 */

import { Routes, Route, Link, useParams, useLocation } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import { TankView } from './components/TankView';
import { NetworkDashboard } from './pages/NetworkDashboard';
import './App.css';

function TankPage() {
    const { tankId } = useParams<{ tankId: string }>();
    return (
        <div className="app">
            <main className="main">
                <TankView tankId={tankId} />
            </main>
            <footer className="footer">
                <p>Built with React + FastAPI + WebSocket | Running at ~30 FPS</p>
            </footer>
        </div>
    );
}

function HomePage() {
    return (
        <div className="app">
            <main className="main">
                <TankView />
            </main>
            <footer className="footer">
                <p>Built with React + FastAPI + WebSocket | Running at ~30 FPS</p>
            </footer>
        </div>
    );
}

function NavBar() {
    const location = useLocation();
    const isNetwork = location.pathname === '/network';

    return (
        <nav style={{
            backgroundColor: '#0f172a',
            borderBottom: '1px solid #1e293b',
            padding: '12px 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
                <Link
                    to="/"
                    style={{
                        color: '#3b82f6',
                        textDecoration: 'none',
                        fontWeight: 700,
                        fontSize: '18px',
                    }}
                >
                    Tank World
                </Link>
                <div style={{ display: 'flex', gap: '16px' }}>
                    <Link
                        to="/network"
                        style={{
                            color: isNetwork ? '#f1f5f9' : '#94a3b8',
                            textDecoration: 'none',
                            fontSize: '14px',
                            fontWeight: isNetwork ? 600 : 400,
                            padding: '6px 12px',
                            borderRadius: '6px',
                            backgroundColor: isNetwork ? '#1e293b' : 'transparent',
                        }}
                    >
                        Network
                    </Link>
                </div>
            </div>
        </nav>
    );
}

function App() {
    return (
        <ErrorBoundary>
            <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
                <NavBar />
                <div style={{ flex: 1 }}>
                    <Routes>
                        <Route path="/" element={<HomePage />} />
                        <Route path="/tank/:tankId" element={<TankPage />} />
                        <Route path="/network" element={<NetworkDashboard />} />
                    </Routes>
                </div>
            </div>
        </ErrorBoundary>
    );
}

export default App;
