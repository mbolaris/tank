/**
 * Evolution Benchmark Display Component
 *
 * Displays comprehensive poker skill evolution metrics including:
 * - Population bb/100 (big blinds won per 100 hands)
 * - Performance vs baseline opponent tiers (trivial/weak/moderate/strong)
 * - Longitudinal trend charts
 * - Strategy distribution and improvement metrics
 *
 * Split into focused modules (god-class ratchet harvest):
 * - evolutionBenchmarkStyles.ts: shared inline-style objects
 * - EvolutionBenchmarkMetrics.tsx: score/baseline/improvement/certainty cards
 * - EvolutionBenchmarkChart.tsx: the longitudinal trend chart
 * This file keeps the data-fetching top-level component and view-mode
 * switching.
 */

import { useState, useEffect, useMemo } from 'react';
import { colors } from '../styles/theme';
import type { BenchmarkImprovementMetrics, EvolutionBenchmarkData } from '../types/simulation';
import { CollapsibleSection } from './ui';
import { LongitudinalChart, type LongitudinalMetric } from './EvolutionBenchmarkChart';
import {
    BbPer100Display,
    PokerScore,
    BaselineBreakdown,
    ImprovementBanner,
    BenchmarkCertainty,
} from './EvolutionBenchmarkMetrics';
import { evolutionBenchmarkStyles as styles } from './evolutionBenchmarkStyles';

type ViewMode = 'overview' | 'vs_baselines' | 'longitudinal';

export function EvolutionBenchmarkDisplay({ worldId }: { worldId?: string }) {
    const [data, setData] = useState<EvolutionBenchmarkData | null>(null);
    const [viewMode, setViewMode] = useState<ViewMode>('overview');
    const [expanded, setExpanded] = useState(true);
    const [loading, setLoading] = useState(true);
    const [longitudinalMetric, setLongitudinalMetric] = useState<LongitudinalMetric>('confidence');

    const isImprovementMetrics = (
        value: EvolutionBenchmarkData['improvement'],
    ): value is BenchmarkImprovementMetrics => {
        return (
            typeof value === 'object' &&
            value !== null &&
            'status' in value &&
            (value as { status?: unknown }).status !== undefined
        );
    };

    useEffect(() => {
        let cancelled = false;
        const url = worldId ? `/api/worlds/${worldId}/evolution-benchmark` : '/api/worlds/evolution-benchmark';

        const fetchData = async () => {
            try {
                const response = await fetch(url);

                // Check content type
                const contentType = response.headers.get('content-type');
                if (!contentType?.includes('application/json')) {
                    // API not available - silently fail
                    if (!cancelled) setLoading(false);
                    return;
                }

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const json = await response.json();
                if (!cancelled) setData(json);
            } catch (e) {
                // Silently fail - API might not be implemented yet
                console.debug('Evolution benchmark API not available:', e);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };

        setLoading(true);
        fetchData();
        const interval = setInterval(fetchData, 30000); // Refresh every 30s
        return () => {
            cancelled = true;
            clearInterval(interval);
        };
    }, [worldId]);

    const latest = data?.latest ?? null;
    const history = useMemo(() => {
        const fullHistory = data?.history ?? [];
        // Limit to most recent 200 snapshots to prevent memory growth
        return fullHistory.length > 200 ? fullHistory.slice(-200) : fullHistory;
    }, [data?.history]);
    const improvementValue = data?.improvement ?? {};
    const improvement: BenchmarkImprovementMetrics = isImprovementMetrics(improvementValue)
        ? (improvementValue as BenchmarkImprovementMetrics)
        : { status: 'insufficient_data', snapshots_collected: 0 };

    useEffect(() => {
        if (longitudinalMetric !== 'confidence') return;
        if (!history.length) return;
        const hasConfidence = history.some((h) => typeof h.conf_strong === 'number' || typeof h.conf_weak === 'number');
        if (!hasConfidence) setLongitudinalMetric('bb100');
    }, [history, longitudinalMetric]);

    if (loading) {
        return (
            <div className="glass-panel" style={{ padding: '16px' }}>
                <CollapsibleSection
                    title={
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', width: '100%' }}>
                            <span style={{ fontSize: '16px', fontWeight: 600, color: colors.primary }}>Poker Evolution Benchmark</span>
                        </div>
                    }
                    defaultExpanded={true}
                >
                    <div style={styles.noData}>Loading benchmark data...</div>
                </CollapsibleSection>
            </div>
        );
    }

    if (!data || data.status === 'not_available' || !latest) {
        return (
            <div className="glass-panel" style={{ padding: '16px' }}>
                <CollapsibleSection
                    title={
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', width: '100%' }}>
                            <span style={{ fontSize: '16px', fontWeight: 600, color: colors.primary }}>Poker Evolution Benchmark</span>
                        </div>
                    }
                    defaultExpanded={true}
                >
                    <div style={styles.noData}>
                        {data?.status === 'not_available'
                            ? 'Benchmark is disabled on the server (TANK_EVOLUTION_BENCHMARK_ENABLED=0).'
                            : (
                                <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <span style={{
                                        display: 'inline-block',
                                        width: '8px',
                                        height: '8px',
                                        borderRadius: '50%',
                                        backgroundColor: '#818cf8',
                                        animation: 'pulse 1.5s ease-in-out infinite',
                                    }} />
                                    Running first benchmark...
                                </span>
                            )}
                        <br />
                        <span style={{ fontSize: '11px', color: colors.textSecondary }}>
                            {data?.status === 'not_available'
                                ? 'Set TANK_EVOLUTION_BENCHMARK_ENABLED=1 and restart the server.'
                                : 'Evaluating fish poker skill against baseline opponents (~30s)'}
                        </span>
                        <style>{`@keyframes pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }`}</style>
                    </div>
                </CollapsibleSection>
            </div>
        );
    }

    return (
        <div className="glass-panel" style={{ padding: '16px' }}>
            <CollapsibleSection
                title={
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flex: 1, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '16px', fontWeight: 600, color: '#818cf8' }}>Poker Evolution Benchmark</span>
                        {expanded && (
                            <div style={styles.tabs} onClick={(e) => e.stopPropagation()}>
                                {(['overview', 'vs_baselines', 'longitudinal'] as ViewMode[]).map(mode => (
                                    <button
                                        key={mode}
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            setViewMode(mode);
                                        }}
                                        style={viewMode === mode ? styles.activeTab : styles.tab}
                                    >
                                        {mode === 'overview' ? 'Overview' :
                                            mode === 'vs_baselines' ? 'vs Baselines' :
                                                'Evolution'}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                }
                expanded={expanded}
                onToggle={setExpanded}
            >
                <div style={{ marginTop: '0px' }}>

                    {viewMode === 'overview' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            {/* Top Row: Score + Metrics */}
                            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 1fr) 2fr', gap: '12px' }}>
                                {/* Left: Prominent Poker Score */}
                                <div>
                                    {latest.conf_strong !== undefined && (
                                        <PokerScore
                                            confStrong={latest.conf_strong}
                                            confExpert={latest.conf_expert}
                                            trend={improvement.status === 'tracked' ? improvement.trend_direction : undefined}
                                        />
                                    )}
                                </div>

                                {/* Right: Metrics Grid (2x2) */}
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', alignContent: 'start' }}>
                                    <BbPer100Display
                                        value={latest.pop_bb_per_100}
                                        label="Population bb/100"
                                    />
                                    <BbPer100Display
                                        value={latest.vs_weak}
                                        label="vs Weak"
                                        showRating={false}
                                    />
                                    <BbPer100Display
                                        value={latest.vs_moderate}
                                        label="vs Moderate"
                                        showRating={false}
                                    />
                                    <BbPer100Display
                                        value={latest.vs_strong}
                                        label="vs Strong"
                                        showRating={false}
                                    />
                                </div>
                            </div>

                            {/* Bottom Row: Best Performer + Improvement */}
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '12px', alignItems: 'center' }}>
                                <div style={{ ...styles.bestPerformer, marginBottom: 0, padding: '6px 12px' }}>
                                    <span style={{ color: colors.textSecondary, fontSize: '11px' }}>Best:</span>
                                    <span style={{ color: '#22c55e', fontWeight: 600 }}>
                                        +{latest.best_bb.toFixed(1)} bb/100
                                    </span>
                                    <span style={styles.strategyTag}>{latest.best_strategy ?? latest.dominant_strategy}</span>
                                </div>

                                <div>
                                    <ImprovementBanner improvement={improvement} />
                                </div>
                            </div>

                            <BenchmarkCertainty latest={latest} />
                        </div>
                    )}

                    {viewMode === 'vs_baselines' && (
                        <BaselineBreakdown perBaseline={latest.per_baseline} />
                    )}

                    {viewMode === 'longitudinal' && (
                        <div style={styles.longitudinalView}>
                            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
                                <div style={styles.miniTabs}>
                                    {(['confidence', 'elo', 'bb100'] as LongitudinalMetric[]).map(m => (
                                        <button
                                            key={m}
                                            onClick={() => setLongitudinalMetric(m)}
                                            style={longitudinalMetric === m ? styles.activeMiniTab : styles.miniTab}
                                        >
                                            {m === 'confidence' ? 'Confidence' : m === 'elo' ? 'Elo' : 'bb/100'}
                                        </button>
                                    ))}
                                </div>
                            </div>
                            <LongitudinalChart history={history} metric={longitudinalMetric} />
                            {improvement.status === 'tracked' && (
                                <div style={styles.trendSummary}>
                                    <div>
                                        <span style={{ color: colors.textSecondary }}>Strategy: </span>
                                        {improvement.dominant_strategy_start} &gt; {improvement.dominant_strategy_end}
                                    </div>
                                    <div>
                                        <span style={{ color: colors.textSecondary }}>Generations: </span>
                                        {improvement.generation_start} &gt; {improvement.generation_end}
                                    </div>
                                    <div>
                                        <span style={{ color: colors.textSecondary }}>Snapshots: </span>
                                        {history.length}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                </div>

                <div style={styles.footer}>
                    <span style={{ color: colors.textSecondary, fontSize: '10px' }}>
                        Gen {latest.generation} | bb/100 = big blinds won per 100 hands
                    </span>
                </div>
            </CollapsibleSection>
        </div>
    );
}
