/**
 * Skill Ladder Panel
 *
 * Shows, per domain (poker / foraging / soccer / ...), how the evolved agents
 * measure against that domain's frozen ruler ladder: a normalized skill index
 * and the per-rung standings. Data comes from GET /api/skill/ladders, which
 * reads the champion registry. This is the "absolute skill + distance to
 * ceiling" view the raw self-play numbers can't give.
 */

import { useEffect, useState } from 'react';
import { colors } from '../styles/theme';
import type { SkillLadder, SkillLaddersResponse } from '../types/skill';
import { CollapsibleSection } from './ui';

function skillColor(index: number): string {
    if (index >= 90) return colors.success;
    if (index >= 60) return '#84cc16';
    if (index >= 30) return colors.warning;
    return colors.danger;
}

function formatMetric(value: number): string {
    return `${value >= 0 ? '+' : ''}${value.toFixed(1)}`;
}

export function LadderCard({ ladder }: { ladder: SkillLadder }) {
    const index = ladder.skill_index;
    const color = skillColor(index);
    const rungProgress = `${ladder.rungs_beaten}/${ladder.total_rungs} rungs`;

    return (
        <div style={styles.card}>
            <div style={styles.cardHeader}>
                <span style={styles.domain}>{ladder.domain}</span>
                <span style={styles.benchmarkId}>{ladder.benchmark_id}</span>
                <span style={{ ...styles.rungsBeaten, color }}>{rungProgress}</span>
            </div>

            <div style={styles.indexRow}>
                <div style={styles.indexBarTrack}>
                    <div
                        style={{
                            ...styles.indexBarFill,
                            width: `${Math.max(0, Math.min(100, index))}%`,
                            backgroundColor: color,
                        }}
                    />
                </div>
                <span style={{ ...styles.indexValue, color }}>{index.toFixed(0)}</span>
                <span style={styles.indexUnit}>/ 100 skill</span>
            </div>

            <div style={styles.rungList}>
                {ladder.rungs.map(rung => (
                    <div key={rung.rung_id} style={styles.rungRow}>
                        <span style={styles.rungLabel}>
                            {rung.rung} {rung.rung_id}
                        </span>
                        <span
                            style={{
                                ...styles.rungMetric,
                                color: rung.beaten ? colors.success : colors.textSecondary,
                            }}
                        >
                            {formatMetric(rung.metric)}
                            <span style={styles.metricName}> {ladder.metric_name}</span>
                        </span>
                        <span
                            style={{
                                ...styles.rungBadge,
                                color: rung.beaten ? colors.success : colors.danger,
                            }}
                        >
                            {rung.beaten ? 'beaten' : 'not yet'}
                        </span>
                    </div>
                ))}
            </div>

            {ladder.notes && <div style={styles.notes}>{ladder.notes}</div>}
        </div>
    );
}

export function SkillLadderList({ ladders }: { ladders: SkillLadder[] }) {
    if (ladders.length === 0) {
        return (
            <div style={styles.noData}>
                No skill ladders recorded yet. Run a ladder benchmark (e.g. poker/ladder_20k)
                and register its champion.
            </div>
        );
    }
    return (
        <div style={styles.list}>
            {ladders.map(ladder => (
                <LadderCard key={ladder.benchmark_id} ladder={ladder} />
            ))}
        </div>
    );
}

export function SkillLadderPanel() {
    const [ladders, setLadders] = useState<SkillLadder[] | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;

        const fetchData = async () => {
            try {
                const response = await fetch('/api/skill/ladders');
                const contentType = response.headers.get('content-type');
                if (!contentType?.includes('application/json') || !response.ok) {
                    if (!cancelled) setLoading(false);
                    return;
                }
                const json: SkillLaddersResponse = await response.json();
                if (!cancelled) setLadders(json.ladders ?? []);
            } catch (e) {
                console.debug('Skill ladder API not available:', e);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };

        setLoading(true);
        fetchData();
        const interval = setInterval(fetchData, 60000);
        return () => {
            cancelled = true;
            clearInterval(interval);
        };
    }, []);

    return (
        <div className="glass-panel" style={{ padding: '16px' }}>
            <CollapsibleSection
                title={
                    <span style={{ fontSize: '16px', fontWeight: 600, color: colors.primary }}>
                        Skill Ladders (vs frozen rulers)
                    </span>
                }
                defaultExpanded={true}
            >
                {loading ? (
                    <div style={styles.noData}>Loading skill ladders...</div>
                ) : (
                    <SkillLadderList ladders={ladders ?? []} />
                )}
            </CollapsibleSection>
        </div>
    );
}

const styles = {
    list: {
        display: 'flex',
        flexDirection: 'column' as const,
        gap: '12px',
    },
    card: {
        backgroundColor: colors.bgLight,
        borderRadius: '10px',
        padding: '12px',
        border: `1px solid ${colors.border}`,
        display: 'flex',
        flexDirection: 'column' as const,
        gap: '8px',
    },
    cardHeader: {
        display: 'flex',
        alignItems: 'baseline',
        gap: '10px',
        flexWrap: 'wrap' as const,
    },
    domain: {
        color: colors.text,
        fontSize: '15px',
        fontWeight: 700,
        textTransform: 'capitalize' as const,
    },
    benchmarkId: {
        color: colors.textSecondary,
        fontSize: '11px',
        fontFamily: 'var(--font-mono)',
    },
    rungsBeaten: {
        marginLeft: 'auto',
        fontSize: '12px',
        fontWeight: 700,
    },
    indexRow: {
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
    },
    indexBarTrack: {
        flex: 1,
        height: '10px',
        borderRadius: '5px',
        backgroundColor: 'rgba(15,23,42,0.6)',
        overflow: 'hidden',
    },
    indexBarFill: {
        height: '100%',
        borderRadius: '5px',
    },
    indexValue: {
        fontSize: '20px',
        fontWeight: 700,
        fontFamily: 'var(--font-mono)',
    },
    indexUnit: {
        color: colors.textSecondary,
        fontSize: '10px',
    },
    rungList: {
        display: 'flex',
        flexDirection: 'column' as const,
        gap: '4px',
    },
    rungRow: {
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        fontSize: '12px',
    },
    rungLabel: {
        color: colors.text,
        width: '180px',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap' as const,
    },
    rungMetric: {
        marginLeft: 'auto',
        fontFamily: 'var(--font-mono)',
        fontWeight: 600,
    },
    metricName: {
        color: colors.textSecondary,
        fontWeight: 400,
        fontSize: '10px',
    },
    rungBadge: {
        width: '64px',
        textAlign: 'right' as const,
        fontSize: '11px',
        fontWeight: 600,
    },
    notes: {
        color: colors.textSecondary,
        fontSize: '11px',
        lineHeight: 1.4,
        borderTop: `1px solid ${colors.border}`,
        paddingTop: '6px',
    },
    noData: {
        padding: '20px',
        textAlign: 'center' as const,
        color: colors.textSecondary,
        fontSize: '13px',
    },
} as const;
