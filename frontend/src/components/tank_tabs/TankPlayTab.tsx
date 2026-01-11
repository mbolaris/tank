import { Canvas } from '../Canvas';
import type { SimulationUpdate } from '../../types/simulation';
import styles from './TankPlayTab.module.css';

interface TankPlayTabProps {
    state: SimulationUpdate | null;
    onEntityClick: (entityId: number, entityType: string) => void;
    selectedEntityId: number | null;
    showEffects: boolean;
    effectiveViewMode: 'side' | 'topdown';
    effectiveWorldType: string;
}

export function TankPlayTab({
    state,
    onEntityClick,
    selectedEntityId,
    showEffects,
    effectiveViewMode,
    effectiveWorldType,
}: TankPlayTabProps) {
    // Summary stats for compact display
    const soccerLeague = state?.soccer_league_live;
    const pokerStats = state?.stats?.poker_stats;
    const population = state?.stats?.fish_count ?? 0;
    const generation = state?.stats?.max_generation ?? state?.stats?.generation ?? 0;

    return (
        <div className={styles.playTab}>
            {/* Main Canvas */}
            <div className="top-section">
                <div className="canvas-wrapper">
                    <Canvas
                        state={state}
                        width={1088}
                        height={612}
                        onEntityClick={onEntityClick}
                        selectedEntityId={selectedEntityId}
                        showEffects={showEffects}
                        viewMode={effectiveViewMode}
                        worldType={effectiveWorldType}
                    />
                    <div className="canvas-glow" aria-hidden />
                </div>
            </div>

            {/* Compact Activity Summary Cards */}
            <div className={styles.summaryGrid}>
                {/* Population Card */}
                <div className={styles.summaryCard}>
                    <div className={styles.cardIcon}>🐟</div>
                    <div className={styles.cardContent}>
                        <div className={styles.cardLabel}>Population</div>
                        <div className={styles.cardValue}>{population.toLocaleString()}</div>
                        <div className={styles.cardSub}>Gen {generation}</div>
                    </div>
                </div>

                {/* Soccer League Status Card */}
                <div className={styles.summaryCard}>
                    <div className={styles.cardIcon}>⚽</div>
                    <div className={styles.cardContent}>
                        <div className={styles.cardLabel}>Soccer League</div>
                        {soccerLeague && !soccerLeague.game_over ? (
                            <>
                                <div className={styles.cardValue}>
                                    {soccerLeague.score.left} - {soccerLeague.score.right}
                                </div>
                                <div className={styles.cardSub}>Match in progress</div>
                            </>
                        ) : (
                            <>
                                <div className={styles.cardValue}>
                                    {state?.soccer_events?.length ?? 0} matches
                                </div>
                                <div className={styles.cardSub}>
                                    {soccerLeague ? 'Idle' : 'No league data'}
                                </div>
                            </>
                        )}
                    </div>
                </div>

                {/* Poker Status Card */}
                <div className={styles.summaryCard}>
                    <div className={styles.cardIcon}>♠</div>
                    <div className={styles.cardContent}>
                        <div className={styles.cardLabel}>Poker</div>
                        <div className={styles.cardValue}>
                            {pokerStats?.total_games?.toLocaleString() ?? 0} games
                        </div>
                        <div className={styles.cardSub}>
                            Plant WR: {pokerStats?.plant_win_rate_pct ?? '0%'}
                        </div>
                    </div>
                </div>

                {/* Energy Status Card */}
                <div className={styles.summaryCard}>
                    <div className={styles.cardIcon}>⚡</div>
                    <div className={styles.cardContent}>
                        <div className={styles.cardLabel}>Fish Energy</div>
                        <div className={styles.cardValue}>
                            {Math.round(state?.stats?.fish_energy ?? 0).toLocaleString()}
                        </div>
                        <div className={styles.cardSub}>
                            Avg: {Math.round(state?.stats?.avg_fish_energy ?? 0)}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
