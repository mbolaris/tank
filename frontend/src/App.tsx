/**
 * Main App component with routing
 */

import { Routes, Route, Link, useParams, useLocation, useNavigate } from 'react-router-dom';
import { useState, useEffect, useCallback } from 'react';
import { ErrorBoundary } from './components/ErrorBoundary';
import { TankView } from './components/TankView';
import { NetworkDashboard } from './pages/NetworkDashboard';
import { config, type TankStatus } from './config';
import './App.css';

interface TankNavigatorProps {
    currentTankId?: string;
}

function TankNavigator({ currentTankId }: TankNavigatorProps) {
    const navigate = useNavigate();
    const [tanks, setTanks] = useState<TankStatus[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchTanks = useCallback(async () => {
        try {
            const response = await fetch(config.tanksApiUrl);
            if (response.ok) {
                const data = await response.json();
                setTanks(data.tanks || []);
            }
        } catch {
            // Silent fail - tanks list not critical
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchTanks();
        // Refresh tank list every 10 seconds
        const interval = setInterval(fetchTanks, 10000);
        return () => clearInterval(interval);
    }, [fetchTanks]);

    // Find current tank index
    const currentIndex = tanks.findIndex(t => 
        currentTankId ? t.tank.tank_id === currentTankId : true
    );
    const currentTank = currentIndex >= 0 ? tanks[currentIndex] : null;

    const goToPrevTank = useCallback(() => {
        if (tanks.length === 0) return;
        const prevIndex = currentIndex <= 0 ? tanks.length - 1 : currentIndex - 1;
        const prevTank = tanks[prevIndex];
        navigate(`/tank/${prevTank.tank.tank_id}`);
    }, [tanks, currentIndex, navigate]);

    const goToNextTank = useCallback(() => {
        if (tanks.length === 0) return;
        const nextIndex = currentIndex >= tanks.length - 1 ? 0 : currentIndex + 1;
        const nextTank = tanks[nextIndex];
        navigate(`/tank/${nextTank.tank.tank_id}`);
    }, [tanks, currentIndex, navigate]);

    // Keyboard navigation
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Don't capture if user is typing in an input
            if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
                return;
            }
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                goToPrevTank();
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                goToNextTank();
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [goToPrevTank, goToNextTank]);

    if (loading || tanks.length <= 1) {
        // Don't show navigator if only 1 tank or still loading
        return null;
    }

    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: '#0f172a',
            borderRadius: '8px',
            padding: '4px 8px',
            border: '1px solid #334155',
        }}>
            <button
                onClick={goToPrevTank}
                aria-label="Previous tank"
                title="Previous tank (←)"
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '28px',
                    height: '28px',
                    borderRadius: '6px',
                    border: 'none',
                    backgroundColor: 'transparent',
                    color: '#94a3b8',
                    fontSize: '14px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = 'rgba(59, 130, 246, 0.2)';
                    e.currentTarget.style.color = '#e2e8f0';
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.color = '#94a3b8';
                }}
            >
                ←
            </button>
            
            <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                minWidth: '120px',
                padding: '0 8px',
            }}>
                <span style={{
                    color: '#e2e8f0',
                    fontSize: '13px',
                    fontWeight: 600,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    maxWidth: '140px',
                }}>
                    {currentTank?.tank.name || 'Default Tank'}
                </span>
                <span style={{
                    color: '#64748b',
                    fontSize: '10px',
                }}>
                    {currentIndex + 1} of {tanks.length}
                </span>
            </div>

            <button
                onClick={goToNextTank}
                aria-label="Next tank"
                title="Next tank (→)"
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '28px',
                    height: '28px',
                    borderRadius: '6px',
                    border: 'none',
                    backgroundColor: 'transparent',
                    color: '#94a3b8',
                    fontSize: '14px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = 'rgba(59, 130, 246, 0.2)';
                    e.currentTarget.style.color = '#e2e8f0';
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.color = '#94a3b8';
                }}
            >
                →
            </button>
        </div>
    );
}

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

function ViewToggle({ isNetwork }: { isNetwork: boolean }) {
    const navigate = useNavigate();

    return (
        <div 
            style={{
                display: 'flex',
                backgroundColor: '#0f172a',
                borderRadius: '10px',
                padding: '4px',
                border: '1px solid #334155',
            }}
            role="tablist"
            aria-label="View mode"
        >
            <button
                onClick={() => navigate('/')}
                role="tab"
                aria-selected={!isNetwork}
                aria-label="Single tank view"
                className={`view-toggle-btn ${!isNetwork ? 'active' : ''}`}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '8px 16px',
                    borderRadius: '7px',
                    border: 'none',
                    backgroundColor: !isNetwork ? '#3b82f6' : 'transparent',
                    color: !isNetwork ? '#fff' : '#94a3b8',
                    fontWeight: 600,
                    fontSize: '13px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                }}
            >
                <span style={{ fontSize: '16px' }}>🐟</span>
                <span>Single Tank</span>
            </button>
            <button
                onClick={() => navigate('/network')}
                role="tab"
                aria-selected={isNetwork}
                aria-label="Network overview"
                className={`view-toggle-btn ${isNetwork ? 'active' : ''}`}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '8px 16px',
                    borderRadius: '7px',
                    border: 'none',
                    backgroundColor: isNetwork ? '#3b82f6' : 'transparent',
                    color: isNetwork ? '#fff' : '#94a3b8',
                    fontWeight: 600,
                    fontSize: '13px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                }}
            >
                <span style={{ fontSize: '16px' }}>🌐</span>
                <span>Network</span>
            </button>
        </div>
    );
}

function NavBar() {
    const location = useLocation();
    const isNetwork = location.pathname === '/network';
    const isTankView = location.pathname === '/' || location.pathname.startsWith('/tank/');
    
    // Extract tankId from URL path
    const tankIdMatch = location.pathname.match(/^\/tank\/(.+)$/);
    const currentTankId = tankIdMatch ? tankIdMatch[1] : undefined;

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
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                    }}
                >
                    <span style={{ fontSize: '22px' }}>🌊</span>
                    Tank World
                </Link>
            </div>

            {/* Central area: View toggle + Tank navigator */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <ViewToggle isNetwork={isNetwork} />
                {isTankView && <TankNavigator currentTankId={currentTankId} />}
            </div>

            {/* Right side - status/hints */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                minWidth: '150px',
                justifyContent: 'flex-end',
            }}>
                {isNetwork ? (
                    <div style={{
                        color: '#64748b',
                        fontSize: '12px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                    }}>
                        <span style={{
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            backgroundColor: '#22c55e',
                            animation: 'pulse 2s infinite',
                        }} />
                        Monitoring network
                    </div>
                ) : (
                    <div style={{
                        color: '#475569',
                        fontSize: '11px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                    }}>
                        <kbd style={{
                            padding: '2px 6px',
                            backgroundColor: '#1e293b',
                            borderRadius: '4px',
                            border: '1px solid #334155',
                            fontSize: '10px',
                        }}>←</kbd>
                        <kbd style={{
                            padding: '2px 6px',
                            backgroundColor: '#1e293b',
                            borderRadius: '4px',
                            border: '1px solid #334155',
                            fontSize: '10px',
                        }}>→</kbd>
                        <span>switch tanks</span>
                    </div>
                )}
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
