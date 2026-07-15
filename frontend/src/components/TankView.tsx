import {
    lazy,
    Suspense,
    useState,
    useCallback,
    useEffect,
    useRef,
    type ChangeEvent,
    type ReactNode,
} from 'react';
import { useWebSocket, type ConnectionStatus } from '../hooks/useWebSocket';
import type { PursuitOverlayData, TargetMemoryOverlayData } from '../rendering/types';
import { useEntitySelection } from '../hooks/useEntitySelection';
import { useEntityPresenceReconciliation } from '../hooks/useEntityPresenceReconciliation';
import { useVisiblePanels } from '../hooks/useVisiblePanels';
import { Canvas } from './Canvas';
import { CommentaryFeed } from './CommentaryFeed';
import { ControlPanel } from './ControlPanel';
import { PanelToggleBar } from './PanelToggleBar';
import { PokerScoreDisplay } from './PokerScoreDisplay';
import { WorldModeSelector } from './WorldModeSelector';
import { useViewMode } from '../hooks/useViewMode';
import { PlantIcon } from './ui';
import styles from './TankView.module.css';

interface TankViewProps {
    worldId?: string;
}

const TransferDialog = lazy(() =>
    import('./TransferDialog').then((module) => ({ default: module.TransferDialog }))
);
const EntityInspectorDrawer = lazy(() =>
    import('./EntityInspectorDrawer').then((module) => ({ default: module.EntityInspectorDrawer }))
);
const TankSoccerTab = lazy(() =>
    import('./tank_tabs/TankSoccerTab').then((module) => ({ default: module.TankSoccerTab }))
);
const TankPokerTab = lazy(() =>
    import('./tank_tabs/TankPokerTab').then((module) => ({ default: module.TankPokerTab }))
);
const TankSkillsTab = lazy(() =>
    import('./tank_tabs/TankSkillsTab').then((module) => ({ default: module.TankSkillsTab }))
);
const TankEcosystemTab = lazy(() =>
    import('./tank_tabs/TankEcosystemTab').then((module) => ({ default: module.TankEcosystemTab }))
);
const TankGeneticsTab = lazy(() =>
    import('./tank_tabs/TankGeneticsTab').then((module) => ({ default: module.TankGeneticsTab }))
);
const TankTrendsTab = lazy(() =>
    import('./tank_tabs/TankTrendsTab').then((module) => ({ default: module.TankTrendsTab }))
);

const CONNECTION_STATUS_DISPLAY: Record<ConnectionStatus, { label: string; color: string }> = {
    live: { label: 'LIVE', color: 'var(--color-success)' },
    connecting: { label: 'CONNECTING', color: 'var(--color-primary)' },
    reconnecting: { label: 'RECONNECTING', color: 'var(--color-warning)' },
};

export function TankView({ worldId }: TankViewProps) {
    const { state, isConnected, connectionStatus, sendCommand, sendCommandWithResponse, connectedWorldId, schemaError } =
        useWebSocket(worldId);
    const [showEffects, setShowEffects] = useState(true);
    const [showSoccer, setShowSoccer] = useState<boolean | null>(null);  // null = not yet synced from server
    const [showResourcePatches, setShowResourcePatches] = useState(false);
    const userToggledSoccer = useRef(false);  // Track if user manually toggled
    const { visible, toggle, isVisible } = useVisiblePanels(['skills', 'soccer', 'ecosystem', 'insights']);

    // Sync showSoccer state from server on initial load and ongoing updates
    useEffect(() => {
        if (state?.tank_soccer_enabled !== undefined && !userToggledSoccer.current) {
            setShowSoccer(state.tank_soccer_enabled);
        }
    }, [state?.tank_soccer_enabled]);

    // Derive effective showSoccer: null (unknown) defaults to false until server confirms
    const effectiveShowSoccer = showSoccer ?? false;

    // Plant energy input control
    const [plantEnergyInput, setPlantEnergyInput] = useState(0.5);

    const handlePlantEnergyChange = useCallback(
        (e: ChangeEvent<HTMLInputElement>) => {
            const rate = parseFloat(e.target.value);
            setPlantEnergyInput(rate);
            sendCommand({ command: 'set_plant_energy_input', data: { rate } });
        },
        [sendCommand]
    );

    // Entity selection: a click opens the inspector; transfer is an explicit
    // secondary action inside it (U4/E1).
    const selection = useEntitySelection();

    // Selected fish's pursuit vectors, owned here so Canvas can read them too.
    const [pursuitOverlay, setPursuitOverlay] = useState<PursuitOverlayData | null>(null);
    const [targetMemoryOverlay, setTargetMemoryOverlay] = useState<TargetMemoryOverlayData | null>(null);
    useEffect(() => {
        setPursuitOverlay(null);
        setTargetMemoryOverlay(null);
    }, [selection.selectedEntityId]);

    const serverViewMode =
        state?.view_mode === 'side' || state?.view_mode === 'topdown'
            ? state.view_mode
            : undefined;

    const {
        effectiveViewMode,
        worldType,
        setWorldType,
    } = useViewMode(serverViewMode, state?.world_type, worldId || state?.world_id);

    // Effective world type for rendering - prefer server state when available
    const effectiveWorldType = state?.world_type ?? worldType;

    // Effective world ID - use connected ID which is available immediately
    const effectiveWorldId = worldId || connectedWorldId || state?.world_id;

    const liveEntities = state?.snapshot?.entities ?? state?.entities ?? [];
    useEffect(() => {
        if (liveEntities.some((entity) => entity.type === 'resource_patch')) {
            setShowResourcePatches(true);
        }
    }, [liveEntities]);
    const selectedEntity =
        selection.selectedEntityId !== null
            ? liveEntities.find((e) => e.id === selection.selectedEntityId) ?? null
            : null;

    useEntityPresenceReconciliation(liveEntities, selection.reconcileEntities);

    return (
        <>
            {schemaError && (
                <div className={styles.schemaError} role="alert">
                    {schemaError}
                </div>
            )}
            {/* Single row of compact controls */}
            <div className={styles.controlBar}>
                <ControlPanel
                    onCommand={sendCommand}
                    isConnected={isConnected}
                    fastForwardEnabled={state?.stats?.fast_forward}
                    showEffects={showEffects}
                    onToggleEffects={() => setShowEffects(!showEffects)}
                    showSoccer={effectiveShowSoccer}
                    onToggleSoccer={() => {
                        userToggledSoccer.current = true;  // Mark as user-initiated
                        const newValue = !effectiveShowSoccer;
                        setShowSoccer(newValue);
                        sendCommand({
                            command: 'set_tank_soccer_enabled',
                            data: { enabled: newValue },
                        });
                    }}
                    showResourcePatches={showResourcePatches}
                    onToggleResourcePatches={() => {
                        const newValue = !showResourcePatches;
                        setShowResourcePatches(newValue);
                        sendCommand({
                            command: 'set_local_resource_patches',
                            data: { enabled: newValue },
                        });
                    }}
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
                    style={{ padding: '12px 20px', display: 'flex', alignItems: 'center', gap: '12px 32px', flexWrap: 'wrap' }}
                >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span
                            className={`status-dot ${connectionStatus}${connectionStatus !== 'live' ? ' animate-pulse' : ''}`}
                            style={{
                                width: 8,
                                height: 8,
                                borderRadius: '50%',
                                background: CONNECTION_STATUS_DISPLAY[connectionStatus].color,
                                boxShadow: connectionStatus === 'live'
                                    ? '0 0 8px var(--color-success)'
                                    : 'none',
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
                            {CONNECTION_STATUS_DISPLAY[connectionStatus].label}
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
                                    SIM FPS
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
                        onEntityClick={selection.selectEntity}
                        selectedEntityId={selection.selectedEntityMissing ? null : selection.selectedEntityId}
                        pursuitOverlay={selection.selectedEntityMissing ? null : pursuitOverlay}
                        targetMemoryOverlay={selection.selectedEntityMissing ? null : targetMemoryOverlay}
                        followEntityId={
                            selection.followEnabled && !selection.selectedEntityMissing
                                ? selection.selectedEntityId
                                : null
                        }
                        showEffects={showEffects}
                        showSoccer={effectiveShowSoccer}
                        viewMode={effectiveViewMode as 'side' | 'topdown'}
                        worldType={effectiveWorldType}
                    />
                    <div className="canvas-glow" aria-hidden />
                    <div className="canvas-hud">
                        <div className="hud-group">
                            <div className="hud-item">
                                <span
                                    className={`status-dot ${connectionStatus}${connectionStatus !== 'live' ? ' animate-pulse' : ''}`}
                                    style={{
                                        width: 6,
                                        height: 6,
                                        borderRadius: '50%',
                                        background: CONNECTION_STATUS_DISPLAY[connectionStatus].color,
                                    }}
                                />
                                {CONNECTION_STATUS_DISPLAY[connectionStatus].label}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Panel Toggle Bar */}
            <PanelToggleBar visible={visible} onToggle={toggle} />

            {/* Panel Grid */}
            {visible.length > 0 && (
                <div className={styles.panelGrid}>
                    {isVisible('insights') && (
                        <Panel title="Board" icon="📋" onClose={() => toggle('insights')}>
                            <CommentaryFeed worldId={effectiveWorldId} />
                        </Panel>
                    )}

                    {isVisible('skills') && (
                        <Panel title="Skills & Benchmarks" icon="🎯" onClose={() => toggle('skills')}>
                            <Suspense fallback={<PanelLoading />}>
                                <TankSkillsTab worldId={effectiveWorldId} onSelectEntity={selection.selectEntity} />
                            </Suspense>
                        </Panel>
                    )}

                    {isVisible('soccer') && (
                        <Panel title="Soccer League" icon="⚽" onClose={() => toggle('soccer')}>
                            <Suspense fallback={<PanelLoading />}>
                                <TankSoccerTab
                                    liveState={state?.soccer_league_live ?? null}
                                    events={state?.soccer_events ?? []}
                                    currentFrame={state?.snapshot?.frame ?? state?.frame ?? 0}
                                />
                            </Suspense>
                        </Panel>
                    )}

                    {isVisible('poker') && (
                        <Panel title="Poker" icon="♠" onClose={() => toggle('poker')}>
                            <Suspense fallback={<PanelLoading />}>
                                <TankPokerTab
                                    worldId={effectiveWorldId}
                                    isConnected={isConnected}
                                    pokerLeaderboard={state?.poker_leaderboard ?? []}
                                    pokerEvents={state?.poker_events ?? []}
                                    pokerStats={state?.stats?.poker_stats}
                                    currentFrame={state?.snapshot?.frame ?? state?.frame ?? 0}
                                    sendCommandWithResponse={sendCommandWithResponse}
                                    worldType={effectiveWorldType}
                                />
                            </Suspense>
                        </Panel>
                    )}

                    {isVisible('trends') && (
                        <Panel title="Trends" icon="📈" onClose={() => toggle('trends')}>
                            <Suspense fallback={<PanelLoading />}>
                                <TankTrendsTab history={state?.metrics_history ?? null} />
                            </Suspense>
                        </Panel>
                    )}

                    {isVisible('ecosystem') && (
                        <Panel title="Ecosystem" icon="🌿" onClose={() => toggle('ecosystem')}>
                            <Suspense fallback={<PanelLoading />}>
                                <TankEcosystemTab
                                    stats={state?.stats ?? null}
                                    autoEvaluation={state?.auto_evaluation}
                                />
                            </Suspense>
                        </Panel>
                    )}

                    {isVisible('genetics') && (
                        <Panel title="Genetics" icon="🧬" onClose={() => toggle('genetics')}>
                            <Suspense fallback={<PanelLoading />}>
                                <TankGeneticsTab worldId={effectiveWorldId} />
                            </Suspense>
                        </Panel>
                    )}
                </div>
            )}

            {/* Entity Inspector Drawer */}
            {selection.inspectorOpen &&
                selection.selectedEntityId !== null &&
                selection.selectedEntityType !== null && (
                    <Suspense fallback={null}>
                        <EntityInspectorDrawer
                            entityId={selection.selectedEntityId}
                            entityType={selection.selectedEntityType}
                            entity={selectedEntity}
                            isConnected={isConnected}
                            sendCommandWithResponse={sendCommandWithResponse}
                            onClose={selection.closeInspector}
                            onRequestTransfer={selection.openTransfer}
                            followEnabled={selection.followEnabled}
                            onToggleFollow={selection.toggleFollow}
                            onPursuitOverlayChange={setPursuitOverlay}
                            onTargetMemoryOverlayChange={setTargetMemoryOverlay}
                        />
                    </Suspense>
                )}

            {/* Transfer Dialog (explicit secondary action from the inspector) */}
            {selection.transferOpen &&
                selection.selectedEntityId !== null &&
                selection.selectedEntityType !== null &&
                state?.world_id && (
                    <Suspense fallback={null}>
                        <TransferDialog
                            entityId={selection.selectedEntityId}
                            entityType={selection.selectedEntityType}
                            sourceWorldId={state.world_id}
                            sourceWorldName={state.world_id}
                            onClose={selection.closeTransfer}
                            onTransferComplete={selection.completeTransfer}
                        />
                    </Suspense>
                )}

            {/* Transfer Notification */}
            {selection.transferMessage && (
                <div
                    style={{
                        position: 'fixed',
                        bottom: '20px',
                        right: '20px',
                        padding: '16px 20px',
                        borderRadius: '8px',
                        backgroundColor:
                            selection.transferMessage.type === 'success' ? '#166534' : '#7f1d1d',
                        color: selection.transferMessage.type === 'success' ? '#bbf7d0' : '#fecaca',
                        border: `1px solid ${selection.transferMessage.type === 'success' ? '#22c55e' : '#ef4444'}`,
                        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
                        zIndex: 1001,
                        maxWidth: '400px',
                        fontWeight: 500,
                    }}
                >
                    {selection.transferMessage.text}
                </div>
            )}
        </>
    );
}

function PanelLoading() {
    return (
        <div
            style={{
                minHeight: '96px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-text-muted)',
                fontSize: '12px',
                fontWeight: 600,
            }}
        >
            Loading panel...
        </div>
    );
}

function Panel({
    title,
    icon,
    onClose,
    children,
}: {
    title: string;
    icon: string;
    onClose: () => void;
    children: ReactNode;
}) {
    return (
        <div className={styles.dashboardPanel} style={{ padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div className={styles.panelHeader}>
                <div className={styles.panelHeaderTitle}>
                    <span style={{ fontSize: '16px' }}>{icon}</span>
                    <span>{title}</span>
                </div>
                <button
                    className={styles.panelClose}
                    onClick={onClose}
                    aria-label={`Hide ${title} panel`}
                    title={`Hide ${title} panel`}
                >
                    ×
                </button>
            </div>
            <div className={styles.panelBody}>{children}</div>
        </div>
    );
}
