import { useEffect, useState } from 'react';
import type { SkillSnapshot, SkillSnapshotsResponse } from '../types/skill';
import { getRungHumanName } from '../utils/rungMapping';
import styles from './SoccerSkillProgress.module.css';


interface SoccerSkillProgressProps {
    worldId?: string;
}

export function SoccerSkillProgress({ worldId = 'default' }: SoccerSkillProgressProps) {
    const [snapshotsResponse, setSnapshotsResponse] = useState<SkillSnapshotsResponse | null>(null);

    useEffect(() => {
        let isMounted = true;

        async function fetchSnapshots() {
            try {
                const targetWorld = worldId || 'default';
                const url = `/api/skill/snapshots?world_id=${encodeURIComponent(targetWorld)}&domain=soccer&limit=100`;
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
    }, [worldId]);

    const snapshots = snapshotsResponse?.snapshots ?? [];
    const hasData = snapshots.length > 0;

    if (!hasData) {
        return (
            <div className={styles.container} aria-label="Soccer Progress">
                <div className={styles.header}>
                    <div className={styles.titleGroup}>
                        <h3 className={styles.title}>Soccer Progress</h3>
                        <span className={styles.badge}>Live Ladder Evaluation</span>
                    </div>
                </div>
                <div className={styles.emptyState}>
                    Awaiting first ladder evaluation
                </div>
            </div>
        );
    }

    const latestSnapshot: SkillSnapshot = snapshots[snapshots.length - 1];
    const oldestSnapshot: SkillSnapshot = snapshots[0];
    const summary = latestSnapshot.summary;

    // Highest beaten rung
    const beatenRungs = summary.rungs.filter(r => r.beaten);
    const highestBeaten = beatenRungs.length > 0 ? beatenRungs[beatenRungs.length - 1] : null;
    const highestBeatenName = highestBeaten
        ? getRungHumanName(highestBeaten.rung_id, highestBeaten.rung)
        : 'Unranked';

    // Rung progress & skill index
    const rungsBeatenCount = summary.rungs_beaten ?? beatenRungs.length;
    const totalRungsCount = summary.total_rungs ?? summary.rungs.length;
    const skillIndexVal = Math.round(summary.skill_index);

    // Target (next unbeaten) rung
    const nextUnbeaten = summary.rungs.find(r => !r.beaten);
    const targetRung = nextUnbeaten || summary.rungs[summary.rungs.length - 1];
    const targetRungName = targetRung
        ? getRungHumanName(targetRung.rung_id, targetRung.rung)
        : 'Ceiling';
    const currentMetric = targetRung ? targetRung.metric : 0;

    // Previous metric comparison
    let prevMetric: number | null = null;
    if (snapshots.length >= 2) {
        const prevSnap = snapshots[snapshots.length - 2];
        const prevTargetRung = prevSnap.summary.rungs.find(r => r.rung_id === targetRung?.rung_id) ||
            prevSnap.summary.rungs.find(r => !r.beaten);
        if (prevTargetRung) {
            prevMetric = prevTargetRung.metric;
        }
    } else if (latestSnapshot.previous_score !== undefined && latestSnapshot.previous_score !== null) {
        prevMetric = latestSnapshot.previous_score;
    }

    let metricComparisonText = '';
    if (prevMetric !== null) {
        const delta = currentMetric - prevMetric;
        const formattedPrev = `${prevMetric >= 0 ? '+' : ''}${prevMetric.toFixed(1)}`;
        const formattedDelta = `${delta >= 0 ? '+' : ''}${delta.toFixed(1)}`;
        metricComparisonText = `, was ${formattedPrev} (${formattedDelta})`;
    }

    // Since generation N delta
    const sinceGen = oldestSnapshot.generation;
    const skillDelta = Math.round(summary.skill_index - oldestSnapshot.summary.skill_index);
    const skillDeltaText = `${skillDelta >= 0 ? '+' : ''}${skillDelta}`;

    return (
        <div className={styles.container} aria-label="Soccer Progress">
            <div className={styles.header}>
                <div className={styles.titleGroup}>
                    <h3 className={styles.title}>Soccer Progress</h3>
                    <span className={styles.badge}>Live Ladder Evaluation</span>
                </div>
            </div>

            <div className={styles.grid}>
                {/* Tank Level / Highest Beaten Rung */}
                <div className={styles.statCard}>
                    <span className={styles.statLabel}>Tank Level</span>
                    <span className={styles.statValue}>
                        {highestBeaten ? `L${beatenRungs.length} ${highestBeatenName} beaten` : 'Unranked'}
                    </span>
                </div>

                {/* Best Team Skill & Goal Diff vs Next Unbeaten Rung */}
                <div className={styles.statCard}>
                    <span className={styles.statLabel}>Best Team Skill</span>
                    <span className={styles.statValue}>
                        {skillIndexVal} <span className={styles.subText}>({rungsBeatenCount}/{totalRungsCount} rungs)</span>
                    </span>
                    <span className={styles.subText}>
                        vs {targetRungName}: {currentMetric >= 0 ? '+' : ''}{currentMetric.toFixed(1)} goals/match{metricComparisonText}
                    </span>
                </div>

                {/* Since Generation N Progress */}
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
