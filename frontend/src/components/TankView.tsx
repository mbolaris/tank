import { useState, useCallback } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useVisiblePanels, type PanelId } from '../hooks/useVisiblePanels';
import { Canvas } from './Canvas';
import { ControlPanel } from './ControlPanel';
import { PokerScoreDisplay } from './PokerScoreDisplay';
import { WorldModeSelector } from './WorldModeSelector';
import { useViewMode } from '../hooks/useViewMode';
import { initRenderers } from '../renderers/init';
import { TransferDialog } from './TransferDialog';
import { PlantIcon } from './ui';
import {
    TankSoccerTab,
    TankPokerTab,
    TankEcosystemTab,
    TankGeneticsTab,
} from './tank_tabs';
import styles from './TankView.module.css';

interface TankViewProps {
    worldId?: string;
}

const PANEL_CONFIG: { id: PanelId; label: string; icon: string }[] = [
    { id: 'soccer', label: 'Soccer', icon: '⚽' },
    { id: 'poker', label: 'Poker', icon: '♠' },
    { id: 'ecosystem', label: 'Ecosystem', icon: '🌿' },
    { id: 'genetics', label: 'Genetics', icon: '🧬' },
];

export function TankView({ worldId }: TankViewProps) {
    const { state, isConnected, sendCommand, sendCommandWithResponse, connectedWorldId } =
        useWebSocket(worldId);
    const [showEffects, setShowEffects] = useState(true);
    const { visible, toggle, isVisible } = useVisiblePanels(['soccer', 'ecosystem']);

    // Plant energy input control
    const [plantEnergyInput, setPlantEnergyInput] = useState(0.15);

    const handlePlantEnergyChange = useCallback(
        (e: React.ChangeEvent<HTMLInputElement>) => {
            const rate = parseFloat(e.target.value);
            setPlantEnergyInput(rate);
            sendCommand({ command: 'set_plant_energy_input', data: { rate } });
        },
        [sendCommand]
    );

    // Entity transfer state
    const [selectedEntityId, setSelectedEntityId] = useState<number | null>(null);
    const [selectedEntityType, setSelectedEntityType] = useState<string | null>(null);
    const [showTransferDialog, setShowTransferDialog] = useState(false);
    const [transferMessage, setTransferMessage] = useState<{
        type: 'success' | 'error';
        text: string;
    } | null>(null);

    const {
        effectiveViewMode,
        setOverrideViewMode: _setOverrideViewMode,
        worldType,
        setWorldType,
    } = useViewMode(state?.view_mode as any, state?.world_type, worldId || state?.world_id);

    // Effective world type for rendering - prefer server state when available
    const effectiveWorldType = state?.world_type ?? worldType;

    // Effective world ID - use connected ID which is available immediately
    const effectiveWorldId = worldId || connectedWorldId || state?.world_id;

    // Ensure renderers are initialized
    initRenderers();

    const handleEntityClick = (entityId: number, entityType: string) => {
        setSelectedEntityId(entityId);
        setSelectedEntityType(entityType);
        setShowTransferDialog(true);
    };

    const handleTransferComplete = (success: boolean, message: string) => {
        setTransferMessage({ type: success ? 'success' : 'error', text: message });
        setSelectedEntityId(null);
        setSelectedEntityType(null);
        setTimeout(() => setTransferMessage(null), 5000);
    };

    const handleCloseTransferDialog = () => {
        setShowTransferDialog(false);
        setSelectedEntityId(null);
        setSelectedEntityType(null);
    };

    return (
        <>
            {/* Single row of compact controls */}
            <div className={styles.controlBar}>
                <ControlPanel
                    onCommand={sendCommand}
                    isConnected={isConnected}
                    fastForwardEnabled={state?.stats?.fast_forward}
                    showEffects={showEffects}
                    onToggleEffects={() => setShowEffects(!showEffects)}
                />

                <WorldModeSelector worldType={worldType} onChange={setWorldType} />

                {/* Plant Energy Input Control */}
                <div className={`glass-panel ${styles.plantEnergyControl}`}>
                    <span className={styles.plantEnergyLabel}>
                        <PlantIcon size={12} /> PLANT ENERGY
                    </span>
                    <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.01"
                        value={plantEnergyInput}
                        onChange={handlePlantEnergyChange}
                        disabled={!isConnected}
                        className={styles.plantEnergySlider}
                    />
                    <span className={styles.plantEnergyValue}>{plantEnergyInput.toFixed(2)}</span>
                </div>
            </div>

            {/* Simulation Stats Panel */}
            <div
                style={{
                    marginBottom: '20px',
                    width: '100%',
                    maxWidth: '1140px',
                    marginLeft: 'auto',
                    marginRight: 'auto',
                }}
            >
                <div
                    className="glass-panel"
                    style={{ padding: '12px 20px', display: 'flex', alignItems: 'center', gap: '32px' }}
                >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span
                            className={`status-dot ${isConnected ? 'online' : 'offline'}`}
                            style={{
                                width: 8,
                                height: 8,
                                borderRadius: '50%',
                                background: isConnected ? 'var(--color-success)' : 'var(--color-warning)',
                                boxShadow: isConnected ? '0 0 8px var(--color-success)' : 'none',
                            }}
                        />
                        <span
                            style={{
                                color: 'var(--color-text-muted)',
                                fontSize: '12px',
                                fontWeight: 600,
                                letterSpacing: '0.05em',
                            }}
                        >
                            {isConnected ? 'LIVE' : 'OFFLINE'}
                        </span>
                    </div>

                    {/* Mode/View Debug Badge */}
                    <div className={styles.divider} />
                    <div style={{ display: 'flex', gap: '8px' }}>
                        <span className={`${styles.badge} ${styles.purple}`}>
                            MODE: {(state as any)?.mode_id ?? state?.world_type ?? 'tank'}
                        </span>
                        <span className={`${styles.badge} ${styles.blue}`}>VIEW: {effectiveViewMode}</span>
                    </div>

                    <div
                        style={{ width: '1px', height: '16px', background: 'rgba(255,255,255,0.1)' }}
                    />

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span
                            style={{
                                color: 'var(--color-text-dim)',
                                fontSize: '11px',
                                fontWeight: 600,
                                letterSpacing: '0.05em',
                            }}
                        >
                            FRAME
                        </span>
                        <span
                            style={{
                                color: 'var(--color-text-main)',
                                fontFamily: 'var(--font-mono)',
                                fontSize: '14px',
                                fontWeight: 500,
                            }}
                        >
                            {state?.stats?.frame ? state.stats.frame.toLocaleString() : '—'}
                        </span>
                    </div>

                    <div
                        style={{ width: '1px', height: '16px', background: 'rgba(255,255,255,0.1)' }}
                    />

                    {state?.stats?.fps !== undefined && (
                        <>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span
                                    style={{
                                        color: 'var(--color-text-dim)',
                                        fontSize: '11px',
                                        fontWeight: 600,
                                        letterSpacing: '0.05em',
                                    }}
                                >
                                    FPS
                                </span>
                                <span
                                    style={{
                                        color: 'var(--color-text-main)',
                                        fontFamily: 'var(--font-mono)',
                                        fontSize: '14px',
                                        fontWeight: 500,
                                    }}
                                >
                                    {state.stats.fps.toFixed(1)}
                                </span>
                            </div>
                            <div
                                style={{
                                    width: '1px',
                                    height: '16px',
                                    background: 'rgba(255,255,255,0.1)',
                                }}
                            />
                        </>
                    )}

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span
                            style={{
                                color: 'var(--color-text-dim)',
                                fontSize: '11px',
                                fontWeight: 600,
                                letterSpacing: '0.05em',
                            }}
                        >
                            POPULATION
                        </span>
                        <span
                            style={{
                                color: 'var(--color-text-main)',
                                fontFamily: 'var(--font-mono)',
                                fontSize: '14px',
                                fontWeight: 500,
                            }}
                        >
                            {state?.stats?.fish_count ? state.stats.fish_count.toLocaleString() : '0'}
                        </span>
                    </div>

                    <div
                        style={{ width: '1px', height: '16px', background: 'rgba(255,255,255,0.1)' }}
                    />

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span
                            style={{
                                color: 'var(--color-text-dim)',
                                fontSize: '11px',
                                fontWeight: 600,
                                letterSpacing: '0.05em',
                            }}
                        >
                            MAX GEN
                        </span>
                        <span
                            style={{
                                color: 'var(--color-text-main)',
                                fontFamily: 'var(--font-mono)',
                                fontSize: '14px',
                                fontWeight: 500,
                            }}
                        >
                            {state?.stats
                                ? (state.stats.max_generation ?? state.stats.generation ?? 0)
                                : '0'}
                        </span>
                    </div>

                    {/* Poker Score */}
                    {(state?.stats?.poker_elo !== undefined ||
                        state?.stats?.poker_score !== undefined) && (
                            <>
                                <div
                                    style={{
                                        width: '1px',
                                        height: '16px',
                                        background: 'rgba(255,255,255,0.1)',
                                    }}
                                />
                                <PokerScoreDisplay
                                    score={state.stats.poker_score}
                                    elo={state.stats.poker_elo}
                                    history={
                                        state.stats.poker_elo &&
                                            state.stats.poker_elo_history &&
                                            state.stats.poker_elo_history.length > 0
                                            ? state.stats.poker_elo_history
                                            : state.stats.poker_score_history || []
                                    }
                                    compact={true}
                                />
                            </>
                        )}
                </div>
            </div>

            {/* Always-visible Canvas */}
            <div className="top-section">
                <div className="canvas-wrapper">
                    <Canvas
                        state={state}
                        width={1088}
                        height={612}
                        onEntityClick={handleEntityClick}
                        selectedEntityId={selectedEntityId}
                        showEffects={showEffects}
                        viewMode={effectiveViewMode as 'side' | 'topdown'}
                        worldType={effectiveWorldType}
                    />
                    <div className="canvas-glow" aria-hidden />
                </div>
            </div>

            {/* Panel Toggle Bar */}
            <div className={styles.panelToggleBar}>
                <span className={styles.panelToggleLabel}>Show panels:</span>
                {PANEL_CONFIG.map(({ id, label, icon }) => (
                    <button
                        key={id}
                        className={`${styles.panelToggle} ${isVisible(id) ? styles.active : ''}`}
                        onClick={() => toggle(id)}
                        aria-pressed={isVisible(id)}
                    >
                        <span className={styles.panelToggleIcon}>{icon}</span>
                        <span>{label}</span>
                    </button>
                ))}
            </div>

            {/* Panel Grid */}
            {visible.length > 0 && (
                <div className={styles.panelGrid}>
                    {isVisible('soccer') && (
                        <CollapsiblePanel title="Soccer League" icon="⚽">
                            <TankSoccerTab
                                liveState={state?.soccer_league_live ?? null}
                                events={state?.soccer_events ?? []}
                                currentFrame={state?.snapshot?.frame ?? state?.frame ?? 0}
                                isConnected={isConnected}
                                onCommand={sendCommand as any}
                                sendCommandWithResponse={sendCommandWithResponse as any}
                            />
                        </CollapsiblePanel>
                    )}

                    {isVisible('poker') && (
                        <CollapsiblePanel title="Poker" icon="♠">
                            <TankPokerTab
                                worldId={effectiveWorldId}
                                isConnected={isConnected}
                                pokerLeaderboard={state?.poker_leaderboard ?? []}
                                pokerEvents={state?.poker_events ?? []}
                                pokerStats={state?.stats?.poker_stats}
                                currentFrame={state?.snapshot?.frame ?? state?.frame ?? 0}
                                sendCommandWithResponse={sendCommandWithResponse}
                            />
                        </CollapsiblePanel>
                    )}

                    {isVisible('ecosystem') && (
                        <CollapsiblePanel title="Ecosystem" icon="🌿">
                            <TankEcosystemTab
                                stats={state?.stats ?? null}
                                autoEvaluation={state?.auto_evaluation}
                            />
                        </CollapsiblePanel>
                    )}

                    {isVisible('genetics') && (
                        <CollapsiblePanel title="Genetics" icon="🧬">
                            <TankGeneticsTab worldId={effectiveWorldId} />
                        </CollapsiblePanel>
                    )}
                </div>
            )}

            {/* Transfer Dialog */}
            {showTransferDialog &&
                selectedEntityId !== null &&
                selectedEntityType !== null &&
                state?.world_id && (
                    <TransferDialog
                        entityId={selectedEntityId}
                        entityType={selectedEntityType}
                        sourceWorldId={state.world_id}
                        sourceWorldName={state.world_id}
                        onClose={handleCloseTransferDialog}
                        onTransferComplete={handleTransferComplete}
                    />
                )}

            {/* Transfer Notification */}
            {transferMessage && (
                <div
                    style={{
                        position: 'fixed',
                        bottom: '20px',
                        right: '20px',
                        padding: '16px 20px',
                        borderRadius: '8px',
                        backgroundColor:
                            transferMessage.type === 'success' ? '#166534' : '#7f1d1d',
                        color: transferMessage.type === 'success' ? '#bbf7d0' : '#fecaca',
                        border: `1px solid ${transferMessage.type === 'success' ? '#22c55e' : '#ef4444'}`,
                        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
                        zIndex: 1001,
                        maxWidth: '400px',
                        fontWeight: 500,
                    }}
                >
                    {transferMessage.text}
                </div>
            )}
        </>
    );
}

function CollapsiblePanel({ title, icon, children }: { title: string; icon: string; children: React.ReactNode }) {
    const [isOpen, setIsOpen] = useState(true);

    return (
        <div className={styles.dashboardPanel} style={{ padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    width: '100%',
                    padding: '12px 16px',
                    background: 'rgba(255, 255, 255, 0.03)',
                    border: 'none',
                    borderBottom: isOpen ? '1px solid var(--card-border)' : 'none',
                    color: 'var(--color-text-main)',
                    cursor: 'pointer',
                    fontSize: '14px',
                    fontWeight: 600,
                    transition: 'background 0.2s',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)'}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '16px' }}>{icon}</span>
                    <span>{title}</span>
                </div>
                <div style={{
                    transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.2s',
                    opacity: 0.5
                }}>
                    ▼
                </div>
            </button>
            {isOpen && (
                <div style={{ padding: '16px' }}>
                    {children}
                </div>
            )}
        </div>
    );
}
