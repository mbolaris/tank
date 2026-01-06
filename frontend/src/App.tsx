/**
 * Main App component with routing
 */

import { Routes, Route, Link, useParams, useLocation, useNavigate } from 'react-router-dom';
import { useState, useEffect, useCallback } from 'react';
import { ErrorBoundary } from './components/ErrorBoundary';
import { TankView } from './components/TankView';
import { NetworkDashboard } from './pages/NetworkDashboard';
import { config, type WorldStatus } from './config';
import { FishIcon, GlobeIcon, WaveIcon, ChevronLeftIcon, ChevronRightIcon } from './components/ui';
import './App.css';

interface TankNavigatorProps {
    currentTankId?: string;
}

function TankNavigator({ currentTankId }: TankNavigatorProps) {
    const navigate = useNavigate();
    const [worlds, setWorlds] = useState<WorldStatus[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchWorlds = useCallback(async () => {
        try {
            const response = await fetch(config.worldsApiUrl);
            if (response.ok) {
                const data = await response.json();
                setWorlds(data.worlds || []);
            }
        } catch {
            // Silent fail
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchWorlds();
        const interval = setInterval(fetchWorlds, 10000);
        return () => clearInterval(interval);
    }, [fetchWorlds]);

    const currentIndex = worlds.findIndex(w =>
        currentTankId ? w.world_id === currentTankId : true
    );
    const currentWorld = currentIndex >= 0 ? worlds[currentIndex] : null;

    const goToPrev = useCallback(() => {
        if (worlds.length === 0) return;
        const prevIndex = currentIndex <= 0 ? worlds.length - 1 : currentIndex - 1;
        const prev = worlds[prevIndex];
        navigate(`/tank/${prev.world_id}`);
    }, [worlds, currentIndex, navigate]);

    const goToNext = useCallback(() => {
        if (worlds.length === 0) return;
        const nextIndex = currentIndex >= worlds.length - 1 ? 0 : currentIndex + 1;
        const next = worlds[nextIndex];
        navigate(`/tank/${next.world_id}`);
    }, [worlds, currentIndex, navigate]);

    // Keyboard navigation
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                goToPrev();
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                goToNext();
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [goToPrev, goToNext]);

    if (loading || worlds.length <= 1) return null;

    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(2, 6, 23, 0.4)',
            borderRadius: 'var(--radius-full)',
            padding: '4px',
            border: '1px solid rgba(255,255,255,0.05)',
        }}>
            <button
                onClick={goToPrev}
                className="nav-btn"
                aria-label="Previous world"
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '28px',
                    height: '28px',
                    borderRadius: '50%',
                    border: 'none',
                    background: 'transparent',
                    color: 'var(--color-text-muted)',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(255,255,255,0.1)';
                    e.currentTarget.style.color = 'var(--color-text-main)';
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = 'var(--color-text-muted)';
                }}
            >
                <ChevronLeftIcon size={14} />
            </button>

            <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                minWidth: '100px',
                padding: '0 8px',
            }}>
                <span style={{
                    color: 'var(--color-text-main)',
                    fontSize: '12px',
                    fontWeight: 600,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    maxWidth: '120px',
                }}>
                    {currentWorld?.name || 'Default World'}
                </span>
                <span style={{
                    color: 'var(--color-text-dim)',
                    fontSize: '10px',
                }}>
                    {currentIndex + 1} / {worlds.length}
                </span>
            </div>

            <button
                onClick={goToNext}
                className="nav-btn"
                aria-label="Next tank"
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '28px',
                    height: '28px',
                    borderRadius: '50%',
                    border: 'none',
                    background: 'transparent',
                    color: 'var(--color-text-muted)',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(255,255,255,0.1)';
                    e.currentTarget.style.color = 'var(--color-text-main)';
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = 'var(--color-text-muted)';
                }}
            >
                <ChevronRightIcon size={14} />
            </button>
        </div>
    );
}

function ViewToggle({ isNetwork }: { isNetwork: boolean }) {
    const navigate = useNavigate();

    return (
        <div
            style={{
                display: 'flex',
                background: 'rgba(2, 6, 23, 0.4)',
                borderRadius: 'var(--radius-full)',
                padding: '4px',
                border: '1px solid rgba(255,255,255,0.05)',
            }}
        >
            <button
                onClick={() => navigate('/')}
                className={`view-toggle-btn ${!isNetwork ? 'active' : ''}`}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 14px',
                    borderRadius: 'var(--radius-full)',
                    border: 'none',
                    background: !isNetwork ? 'var(--color-primary)' : 'transparent',
                    color: !isNetwork ? '#fff' : 'var(--color-text-muted)',
                    fontWeight: 600,
                    fontSize: '12px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    boxShadow: !isNetwork ? '0 0 15px var(--color-primary-glow)' : 'none',
                }}
            >
                <FishIcon size={14} />
                <span>Tank</span>
            </button>
            <button
                onClick={() => navigate('/network')}
                className={`view-toggle-btn ${isNetwork ? 'active' : ''}`}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 14px',
                    borderRadius: 'var(--radius-full)',
                    border: 'none',
                    background: isNetwork ? 'var(--color-secondary)' : 'transparent',
                    color: isNetwork ? '#fff' : 'var(--color-text-muted)',
                    fontWeight: 600,
                    fontSize: '12px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    boxShadow: isNetwork ? '0 0 15px var(--color-secondary-glow)' : 'none',
                }}
            >
                <GlobeIcon size={14} />
                <span>Network</span>
            </button>
        </div>
    );
}

function NavBar() {
    const location = useLocation();
    const isNetwork = location.pathname === '/network';
    const isTankView = location.pathname === '/' || location.pathname.startsWith('/tank/');

    const tankIdMatch = location.pathname.match(/^\/tank\/(.+)$/);
    const currentTankId = tankIdMatch ? tankIdMatch[1] : undefined;

    return (
        <nav style={{
            position: 'sticky',
            top: 0,
            zIndex: 50,
            background: 'rgba(2, 6, 23, 0.8)',
            backdropFilter: 'blur(12px)',
            borderBottom: '1px solid rgba(255,255,255,0.05)',
            padding: '12px 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
                <Link
                    to="/"
                    style={{
                        color: 'var(--color-text-main)',
                        textDecoration: 'none',
                        fontWeight: 700,
                        fontSize: '18px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        letterSpacing: '-0.02em',
                    }}
                >
                    <div style={{
                        width: '32px',
                        height: '32px',
                        borderRadius: '8px',
                        background: 'linear-gradient(135deg, var(--color-primary), var(--color-secondary))',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '18px',
                        boxShadow: '0 0 20px var(--color-primary-glow)',
                    }}>
                        <WaveIcon size={18} />
                    </div>
                    <span>Tank World</span>
                </Link>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <ViewToggle isNetwork={isNetwork} />
                {isTankView && <TankNavigator currentTankId={currentTankId} />}
            </div>

            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                minWidth: '150px',
                justifyContent: 'flex-end',
            }}>
                {isNetwork ? (
                    <div style={{
                        color: 'var(--color-success)',
                        fontSize: '12px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontWeight: 500,
                    }}>
                        <span style={{
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            backgroundColor: 'currentColor',
                            boxShadow: '0 0 10px currentColor',
                            animation: 'pulse 2s infinite',
                        }} />
                        Network Active
                    </div>
                ) : (
                    <div style={{
                        color: 'var(--color-text-dim)',
                        fontSize: '11px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                    }}>
                        <span style={{ opacity: 0.7 }}>Switch Tanks:</span>
                        <kbd style={{
                            padding: '2px 6px',
                            background: 'rgba(255,255,255,0.05)',
                            borderRadius: '4px',
                            border: '1px solid rgba(255,255,255,0.1)',
                            fontSize: '10px',
                            fontFamily: 'var(--font-mono)',
                        }}>←</kbd>
                        <kbd style={{
                            padding: '2px 6px',
                            background: 'rgba(255,255,255,0.05)',
                            borderRadius: '4px',
                            border: '1px solid rgba(255,255,255,0.1)',
                            fontSize: '10px',
                            fontFamily: 'var(--font-mono)',
                        }}>→</kbd>
                    </div>
                )}
            </div>
        </nav>
    );
}

function TankPage() {
    const { tankId } = useParams<{ tankId: string }>();
    const navigate = useNavigate();
    const [isValid, setIsValid] = useState<boolean | null>(null);

    useEffect(() => {
        if (!tankId) {
            navigate('/', { replace: true });
            return;
        }

        // Validate the world exists
        const validateWorld = async () => {
            try {
                const res = await fetch(`${config.apiBaseUrl}/api/worlds/${tankId}/snapshot`);
                if (res.ok) {
                    setIsValid(true);
                } else {
                    // World doesn't exist, redirect to home
                    console.warn(`World ${tankId} not found, redirecting to home`);
                    navigate('/', { replace: true });
                }
            } catch {
                // Network error, redirect to home
                navigate('/', { replace: true });
            }
        };

        validateWorld();
    }, [tankId, navigate]);

    // Show loading while validating
    if (isValid === null) {
        return (
            <div className="app">
                <main className="main" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                    <div style={{ color: '#888' }}>Loading world...</div>
                </main>
            </div>
        );
    }

    return (
        <div className="app">
            <main className="main">
                <TankView worldId={tankId} />
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
