import React from 'react';
import type { PokerEventData, SoccerEventData } from '../types/simulation';

/**
 * Reward logs shown under the soccer field and the poker table.
 *
 * Each entry describes, per fish, what a match or hand actually paid out:
 * net energy (winnings minus fees/bets), reproduction credits banked, and
 * any reproduction the win earned.
 */

interface FishReward {
    fishId: string;
    energyDelta?: number;
    reproCredits?: number;
    babyId?: number | null;
    tag?: string;       // e.g. team side or WIN/LOSS
    tagColor?: string;
}

interface RewardLogEntry {
    key: string;
    title: string;
    ageFrames: number;
    rewards: FishReward[];
}

const panelStyle: React.CSSProperties = {
    padding: '10px 12px',
    borderRadius: '10px',
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    display: 'grid',
    gap: '6px',
};

const emptyStyle: React.CSSProperties = {
    marginTop: '10px',
    padding: '14px',
    borderRadius: '10px',
    backgroundColor: '#0f172a',
    border: '1px dashed #334155',
    color: '#94a3b8',
    fontSize: '13px',
    textAlign: 'center',
};

function formatEnergy(value: number): string {
    return `${value >= 0 ? '+' : ''}${value.toFixed(1)}⚡`;
}

function FishRewardRow({ reward }: { reward: FishReward }) {
    return (
        <div
            style={{
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                gap: '8px',
                fontSize: '12px',
            }}
        >
            {reward.tag && (
                <span
                    style={{
                        padding: '1px 6px',
                        borderRadius: '999px',
                        backgroundColor: `${reward.tagColor ?? '#94a3b8'}22`,
                        color: reward.tagColor ?? '#94a3b8',
                        fontSize: '10px',
                        fontWeight: 700,
                        letterSpacing: '0.03em',
                        minWidth: '38px',
                        textAlign: 'center',
                    }}
                >
                    {reward.tag}
                </span>
            )}
            <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{`Fish #${reward.fishId}`}</span>
            {reward.energyDelta !== undefined && (
                <span style={{ color: reward.energyDelta >= 0 ? '#4ade80' : '#f87171' }}>
                    {formatEnergy(reward.energyDelta)}
                </span>
            )}
            {reward.reproCredits !== undefined && reward.reproCredits > 0 && (
                <span style={{ color: '#38bdf8' }}>
                    {`+${reward.reproCredits.toFixed(1)} repro credit${reward.reproCredits === 1 ? '' : 's'}`}
                </span>
            )}
            {reward.babyId !== undefined && reward.babyId !== null && (
                <span style={{ color: '#facc15' }}>{`🐣 reproduced — baby #${reward.babyId}`}</span>
            )}
        </div>
    );
}

function RewardLogList({
    title,
    entries,
    emptyMessage,
}: {
    title: string;
    entries: RewardLogEntry[];
    emptyMessage: string;
}) {
    return (
        <section aria-label={title} style={{ marginTop: '14px' }}>
            <h3 style={{ margin: 0, fontSize: '14px', color: '#93c5fd' }}>{title}</h3>
            {entries.length === 0 ? (
                <div style={emptyStyle}>{emptyMessage}</div>
            ) : (
                <div style={{ marginTop: '10px', display: 'grid', gap: '8px' }}>
                    {entries.map((entry) => (
                        <div key={entry.key} style={panelStyle}>
                            <div
                                style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    gap: '12px',
                                    fontSize: '12px',
                                }}
                            >
                                <span style={{ color: '#cbd5f5', fontWeight: 600 }}>{entry.title}</span>
                                <span style={{ color: '#94a3b8' }}>{`${entry.ageFrames}f ago`}</span>
                            </div>
                            {entry.rewards.length === 0 ? (
                                <div style={{ color: '#94a3b8', fontSize: '12px' }}>
                                    No fish rewards recorded.
                                </div>
                            ) : (
                                entry.rewards.map((reward) => (
                                    <FishRewardRow key={`${entry.key}-${reward.fishId}`} reward={reward} />
                                ))
                            )}
                        </div>
                    ))}
                </div>
            )}
        </section>
    );
}

const MAX_LOG_ENTRIES = 6;

function sortByEnergyDesc(a: FishReward, b: FishReward): number {
    return (b.energyDelta ?? 0) - (a.energyDelta ?? 0);
}

/** Per-fish rewards from recent soccer league matches, shown under the field. */
export function SoccerRewardLog({
    events,
    currentFrame,
}: {
    events: SoccerEventData[];
    currentFrame: number;
}) {
    const entries: RewardLogEntry[] = events
        .filter((event) => !event.skipped)
        .slice()
        .reverse()
        .slice(0, MAX_LOG_ENTRIES)
        .map((event, index) => {
            const leftIds = new Set((event.teams?.left ?? []).map(String));
            const rightIds = new Set((event.teams?.right ?? []).map(String));
            const credits = event.repro_credit_deltas ?? {};
            const deltas = event.energy_deltas ?? {};
            const fishIds = new Set([...Object.keys(deltas), ...Object.keys(credits)]);

            const rewards: FishReward[] = [...fishIds]
                .map((fishId) => {
                    const side = leftIds.has(fishId) ? 'LEFT' : rightIds.has(fishId) ? 'RIGHT' : undefined;
                    return {
                        fishId,
                        energyDelta: deltas[fishId],
                        reproCredits: credits[fishId],
                        tag: side,
                        tagColor: side === 'LEFT' ? '#60a5fa' : side === 'RIGHT' ? '#f87171' : undefined,
                    };
                })
                .sort(sortByEnergyDesc);

            const winner =
                event.winner_team === 'draw' || !event.winner_team
                    ? 'Draw'
                    : `${event.winner_team === 'left' ? 'Left' : 'Right'} win`;

            return {
                key: `${event.match_id}-${event.frame}-${index}`,
                title: `${winner} ${event.score_left}-${event.score_right}`,
                ageFrames: Math.max(0, currentFrame - event.frame),
                rewards,
            };
        })
        // Bot wins clear all rewards; skip matches with nothing to report.
        .filter((entry) => entry.rewards.length > 0);

    return (
        <RewardLogList
            title="Reward Log — energy & reproduction earned"
            entries={entries}
            emptyMessage="No match rewards yet. Rewards for each fish appear here after league matches finish."
        />
    );
}

/** Per-fish rewards from recent tank poker hands, shown under the table. */
export function PokerRewardLog({
    events,
    currentFrame,
}: {
    events: PokerEventData[];
    currentFrame: number;
}) {
    const entries: RewardLogEntry[] = events
        .slice()
        .reverse()
        .slice(0, MAX_LOG_ENTRIES)
        .map((event, index) => {
            const credits = event.repro_credit_deltas ?? {};
            const deltas = event.energy_deltas ?? {};
            const fishIds = new Set([...Object.keys(deltas), ...Object.keys(credits)]);
            const isTie = event.winner_id === -1;
            const babyId = event.reproduction?.baby_id ?? null;
            const parentId = event.reproduction?.parent_id;

            const rewards: FishReward[] = [...fishIds]
                .map((fishId) => {
                    const won = !isTie && String(event.winner_id) === fishId;
                    return {
                        fishId,
                        energyDelta: deltas[fishId],
                        reproCredits: credits[fishId],
                        babyId: parentId !== undefined && String(parentId) === fishId ? babyId : undefined,
                        tag: isTie ? 'TIE' : won ? 'WIN' : 'LOSS',
                        tagColor: isTie ? '#94a3b8' : won ? '#4ade80' : '#f87171',
                    };
                })
                .sort(sortByEnergyDesc);

            const title = isTie
                ? `Tie — ${event.winner_hand}`
                : `${event.winner_hand} wins pot${event.pot ? ` (${event.pot.toFixed(1)}⚡)` : ''}`;

            return {
                key: `${event.frame}-${index}`,
                title,
                ageFrames: Math.max(0, currentFrame - event.frame),
                rewards,
            };
        })
        // Older backends emit events without per-fish detail; skip those rows.
        .filter((entry) => entry.rewards.length > 0);

    return (
        <RewardLogList
            title="Reward Log — energy & reproduction earned"
            entries={entries}
            emptyMessage="No table rewards yet. Rewards for each fish appear here after poker hands finish."
        />
    );
}
