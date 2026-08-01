import { useEffect, useState } from 'react';
import type { SkillSnapshot, SkillSnapshotsResponse } from '../types/skill';
import { getRungHumanName } from '../utils/rungMapping';
import styles from './SoccerSkillProgress.module.css';

export type SkillProgressDomain = 'soccer' | 'poker';

interface SkillProgressProps {
    worldId?: string;
    domain: SkillProgressDomain;
}

const DOMAIN_COPY: Record<SkillProgressDomain, {
    title: string;
    badge: string;
    empty: string;
    subjectLabel: string;
    metricSuffix: string;
}> = {
    soccer: {
        title: 'Soccer Progress',
        badge: 'Live Ladder Evaluation',
        empty: 'Awaiting first ladder evaluation',
        subjectLabel: 'Best Team Skill',
        metricSuffix: 'goals/match',
    },
    poker: {
        title: 'Poker Progress',
        badge: 'Frozen Ladder Evaluation',
        empty: 'Awaiting first poker ladder evaluation',
        subjectLabel: 'Best Fish Skill',
        metricSuffix: 'bb/100',
    },
};

export function SkillProgress({ worldId = 'default', domain }: SkillProgressProps) {
    const [snapshotsResponse, setSnapshotsResponse] = useState<SkillSnapshotsResponse | null>(null);
    const copy = DOMAIN_COPY[domain];

    useEffect(() => {
        let isMounted = true;

        async function fetchSnapshots() {
            try {
                const targetWorld = worldId || 'default';
                const url = `/api/skill/snapshots?world_id=${encodeURIComponent(targetWorld)}&domain=${domain}&limit=100`;
                const res = await fetch(url);
                if (!res.ok) return;
                const json: SkillSnapshotsResponse = await res.json();
                if (isMounted) {
                    setSnapshotsResponse(json);
                }
            } catch {
                // Ignore network errors during polling / unmount
            }
        }

        fetchSnapshots();
        const interval = setInterval(fetchSnapshots, 10000);

        return () => {
            isMounted = false;
            clearInterval(interval);
        };
    }, [worldId, domain]);

    const snapshots = snapshotsResponse?.snapshots ?? [];
    if (snapshots.length === 0) {
        return (
            <div className={styles.container} aria-label={copy.title}>
                <div className={styles.header}>
                    <div className={styles.titleGroup}>
                        <h3 className={styles.title}>{copy.title}</h3>
                        <span className={styles.badge}>{copy.badge}</span>
                    </div>
                </div>
                <div className={styles.emptyState}>{copy.empty}</div>
            </div>
        );
    }

    const latestSnapshot: SkillSnapshot = snapshots[snapshots.length - 1];
    const oldestSnapshot: SkillSnapshot = snapshots[0];
    const summary = latestSnapshot.summary;
    const beatenRungs = summary.rungs.filter(r => r.beaten);
    const highestBeaten = beatenRungs.length > 0 ? beatenRungs[beatenRungs.length - 1] : null;
    const highestBeatenName = highestBeaten
        ? getRungHumanName(highestBeaten.rung_id, highestBeaten.rung)
        : 'Unranked';
    const rungsBeatenCount = summary.rungs_beaten ?? beatenRungs.length;
    const totalRungsCount = summary.total_rungs ?? summary.rungs.length;
    const skillIndexVal = Math.round(summary.skill_index);
    const nextUnbeaten = summary.rungs.find(r => !r.beaten);
    const targetRung = nextUnbeaten || summary.rungs[summary.rungs.length - 1];
    const targetRungName = targetRung
        ? getRungHumanName(targetRung.rung_id, targetRung.rung)
        : 'Ceiling';
    const currentMetric = targetRung ? targetRung.metric : 0;

    let previousMetric: number | null = null;
    if (snapshots.length >= 2) {
        const previousSnapshot = snapshots[snapshots.length - 2];
        const previousRung = previousSnapshot.summary.rungs.find(
            r => r.rung_id === targetRung?.rung_id,
        ) || previousSnapshot.summary.rungs.find(r => !r.beaten);
        if (previousRung) previousMetric = previousRung.metric;
    }

    let metricComparisonText = '';
    if (previousMetric !== null) {
        const delta = currentMetric - previousMetric;
        const formattedPrev = `${previousMetric >= 0 ? '+' : ''}${previousMetric.toFixed(1)}`;
        const formattedDelta = `${delta >= 0 ? '+' : ''}${delta.toFixed(1)}`;
        metricComparisonText = `, was ${formattedPrev} (${formattedDelta})`;
    }

    const sinceGen = oldestSnapshot.generation;
    const skillDelta = Math.round(summary.skill_index - oldestSnapshot.summary.skill_index);
    const skillDeltaText = `${skillDelta >= 0 ? '+' : ''}${skillDelta}`;

    return (
        <div className={styles.container} aria-label={copy.title}>
            <div className={styles.header}>
                <div className={styles.titleGroup}>
                    <h3 className={styles.title}>{copy.title}</h3>
                    <span className={styles.badge}>{copy.badge}</span>
                </div>
            </div>

            <div className={styles.grid}>
                <div className={styles.statCard}>
                    <span className={styles.statLabel}>Tank Level</span>
                    <span className={styles.statValue}>
                        {highestBeaten ? `L${beatenRungs.length} ${highestBeatenName} beaten` : 'Unranked'}
                    </span>
                </div>

                <div className={styles.statCard}>
                    <span className={styles.statLabel}>{copy.subjectLabel}</span>
                    <span className={styles.statValue}>
                        {skillIndexVal} <span className={styles.subText}>({rungsBeatenCount}/{totalRungsCount} rungs)</span>
                    </span>
                    <span className={styles.subText}>
                        vs {targetRungName}: {currentMetric >= 0 ? '+' : ''}{currentMetric.toFixed(1)} {copy.metricSuffix}{metricComparisonText}
                    </span>
                </div>

                <div className={styles.statCard}>
                    <span className={styles.statLabel}>Skill Delta</span>
                    <span className={styles.statValue}>
                        Since gen {sinceGen}: <span className={skillDelta >= 0 ? styles.positive : styles.negative}>{skillDeltaText} skill</span>
                    </span>
                </div>
            </div>
        </div>
    );
}

export function SoccerSkillProgress({ worldId = 'default' }: { worldId?: string }) {
    return <SkillProgress worldId={worldId} domain="soccer" />;
}

export function PokerSkillProgress({ worldId = 'default' }: { worldId?: string }) {
    return <SkillProgress worldId={worldId} domain="poker" />;
}
