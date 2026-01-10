import React from 'react';
import type { SoccerEventData } from '../types/simulation';

interface SoccerLeagueEventsProps {
    events: SoccerEventData[];
    currentFrame: number;
}

const SoccerLeagueEvents: React.FC<SoccerLeagueEventsProps> = ({ events, currentFrame }) => {
    const items = events.slice().reverse().slice(0, 8);

    return (
        <section aria-label="Recent soccer league results">
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                <h2 style={{ margin: 0, fontSize: '16px', color: '#93c5fd' }}>Soccer League</h2>
                <span style={{ fontSize: '12px', color: '#94a3b8' }}>{events.length} results</span>
            </div>

            {items.length === 0 ? (
                <div style={{
                    marginTop: '12px',
                    padding: '16px',
                    borderRadius: '10px',
                    backgroundColor: '#0f172a',
                    border: '1px dashed #334155',
                    color: '#94a3b8',
                    fontSize: '13px',
                    textAlign: 'center',
                }}>
                    No soccer matches recorded yet.
                </div>
            ) : (
                <div style={{ marginTop: '12px', display: 'grid', gap: '10px' }}>
                    {items.map((event, index) => {
                        const participants = (event.teams?.left?.length ?? 0) + (event.teams?.right?.length ?? 0);
                        const energyDelta = Object.values(event.energy_deltas ?? {}).reduce(
                            (total, value) => total + value,
                            0
                        );
                        const reproDelta = Object.values(event.repro_credit_deltas ?? {}).reduce(
                            (total, value) => total + value,
                            0
                        );
                        const age = currentFrame >= event.frame ? currentFrame - event.frame : 0;

                        const winnerTeam = event.winner_team ?? null;
                        const winnerLabel = event.skipped
                            ? 'SKIPPED'
                            : winnerTeam === 'draw' || winnerTeam === null
                                ? 'DRAW'
                                : winnerTeam === 'left'
                                    ? 'LEFT WIN'
                                    : 'RIGHT WIN';

                        const badgeColor = event.skipped
                            ? '#f59e0b'
                            : winnerTeam === 'draw' || winnerTeam === null
                                ? '#94a3b8'
                                : winnerTeam === 'left'
                                    ? '#60a5fa'
                                    : '#f87171';

                        return (
                            <div
                                key={`${event.match_id}-${index}`}
                                style={{
                                    padding: '12px',
                                    borderRadius: '12px',
                                    backgroundColor: '#0f172a',
                                    border: '1px solid #334155',
                                    display: 'grid',
                                    gap: '6px',
                                }}
                            >
                                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <span style={{
                                            padding: '2px 8px',
                                            borderRadius: '999px',
                                            backgroundColor: `${badgeColor}22`,
                                            color: badgeColor,
                                            fontSize: '11px',
                                            fontWeight: 700,
                                            letterSpacing: '0.03em',
                                        }}>
                                            {winnerLabel}
                                        </span>
                                        <span style={{ color: '#e2e8f0', fontWeight: 600 }}>
                                            {event.score_left} - {event.score_right}
                                        </span>
                                    </div>
                                    <span style={{ color: '#94a3b8', fontSize: '12px' }}>
                                        {age}f ago
                                    </span>
                                </div>

                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', fontSize: '12px' }}>
                                    <span style={{ color: '#94a3b8' }}>Players: {participants}</span>
                                    <span style={{ color: energyDelta >= 0 ? '#4ade80' : '#f87171' }}>
                                        Energy Delta {energyDelta >= 0 ? '+' : ''}{energyDelta.toFixed(1)}
                                    </span>
                                    <span style={{ color: reproDelta >= 0 ? '#38bdf8' : '#f87171' }}>
                                        Repro Delta {reproDelta >= 0 ? '+' : ''}{reproDelta.toFixed(1)}
                                    </span>
                                </div>

                                {event.last_goal && (
                                    <div style={{ color: '#cbd5f5', fontSize: '12px' }}>
                                        Last goal: {event.last_goal.team.toUpperCase()}
                                        {event.last_goal.scorer_id ? ` by ${event.last_goal.scorer_id}` : ''}
                                        {event.last_goal.assist_id ? ` (assist ${event.last_goal.assist_id})` : ''}
                                    </div>
                                )}

                                {event.skipped && event.skip_reason && (
                                    <div style={{ color: '#fbbf24', fontSize: '12px' }}>
                                        Reason: {event.skip_reason}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </section>
    );
};

export default SoccerLeagueEvents;
