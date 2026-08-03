import type { SoccerLeagueLiveState } from '../types/simulation';
import type { SkillLadder } from '../types/skill';
import { useBreakthroughs } from '../hooks/useBreakthroughs';
import { useSkillSnapshots } from '../hooks/useSkillSnapshots';
import { BreakthroughCard } from './BreakthroughCard';
import { FormChips } from './FormChips';
import { ReferenceLadder } from './ReferenceLadder';
import { TopPerformers } from './TopPerformers';
import styles from './TeamProgressPanel.module.css';

type ProgressLiveState = SoccerLeagueLiveState & {
    team_form?: Record<string, string[]>;
    team_positions?: Record<string, number>;
};

function latestLadder(snapshots: { summary: SkillLadder }[]): SkillLadder | undefined {
    return snapshots.at(-1)?.summary;
}

function tankTeamId(liveState: ProgressLiveState): string | null {
    const active = liveState.active_match;
    const tankEntry = liveState.leaderboard.find((entry) => entry.source === 'tank');
    if (!tankEntry) return null;
    if (active?.home_id === tankEntry.team_id || active?.away_id === tankEntry.team_id) return tankEntry.team_id;
    return tankEntry.team_id;
}

export function TeamProgressPanel({ worldId, liveState }: { worldId?: string; liveState: SoccerLeagueLiveState | null }) {
    const { data, loading } = useSkillSnapshots(worldId);
    const progressState = liveState as ProgressLiveState | null;
    const unseenBreakthroughs = useBreakthroughs(data?.breakthroughs ?? [], worldId);
    const snapshots = data?.snapshots ?? [];
    const ladder = latestLadder(snapshots);
    const firstScore = snapshots[0]?.summary.skill_index;
    const currentScore = ladder?.skill_index ?? data?.tank_best ?? 0;
    const delta = firstScore === undefined ? null : currentScore - firstScore;
    const teamId = progressState ? tankTeamId(progressState) : null;
    const position = teamId ? progressState?.team_positions?.[teamId] : undefined;
    const entry = teamId ? progressState?.leaderboard.find((item) => item.team_id === teamId) : undefined;
    const form = teamId ? progressState?.team_form?.[teamId] ?? [] : [];

    return (
        <div className={styles.panel} data-testid="soccer-team-progress">
            <div className={styles.heading}>
                <h3>Soccer Progress</h3>
                <span className={styles.label}>SKILL</span>
            </div>
            {unseenBreakthroughs.at(-1) && <BreakthroughCard record={unseenBreakthroughs.at(-1)!} />}
            {loading && !data ? <div className={styles.emptySection}>Loading skill snapshots...</div> : (
                <>
                    <section className={styles.section} aria-label="Team skill">
                        <div className={styles.sectionTitle}>Team skill · longitudinal</div>
                        <div className={styles.skillRow}>
                            <span className={styles.skillValue}>{currentScore.toFixed(0)}</span>
                            {delta !== null && <span className={styles.skillDelta}>{delta >= 0 ? '↑' : '↓'}{Math.abs(delta).toFixed(0)}</span>}
                        </div>
                        <div className={styles.sparkline}>{snapshots.map((item) => '▁▂▃▄▅▆▇'[Math.max(0, Math.min(6, Math.round(item.summary.skill_index / 15)))]).join(' ') || 'No history yet'}</div>
                    </section>
                    <section className={styles.section} aria-label="Reference ladder">
                        <div className={styles.sectionTitle}>Reference ladder · frozen rulers</div>
                        <ReferenceLadder ladder={ladder} />
                    </section>
                    <section className={styles.section} aria-label="League form">
                        <div className={styles.sectionTitle}>League · relative context</div>
                        <div className={styles.leagueSummary}>
                            <span>{position ? `${position}${position === 1 ? 'st' : position === 2 ? 'nd' : position === 3 ? 'rd' : 'th'} of ${progressState?.leaderboard.length ?? '?'}` : 'Position pending'}</span>
                            <span>{entry ? `${entry.points} pts` : '—'}</span>
                        </div>
                        <FormChips form={form} />
                    </section>
                    <section className={styles.section} aria-label="Top performers">
                        <div className={styles.sectionTitle}>Top performers · match records</div>
                        <TopPerformers leaders={progressState?.fish_leaders ?? []} />
                    </section>
                </>
            )}
        </div>
    );
}
