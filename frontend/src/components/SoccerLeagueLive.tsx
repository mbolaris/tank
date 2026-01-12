import { useEffect, useState } from 'react';
import type { LeagueLeaderboardEntry, SoccerLeagueLiveState } from '../types/simulation';
import { SoccerPitch } from './SoccerPitch';

interface SoccerLeagueLiveProps {
    liveState?: SoccerLeagueLiveState | null;
    isConnected: boolean;
    onCommand: (command: { command: string; data?: Record<string, unknown> }) => void;
}

export function SoccerLeagueLive({ liveState, isConnected }: SoccerLeagueLiveProps) {
    // We only need to know if there's an active match for display purposes
    const activeMatch = liveState?.active_match;

    const getScoreDisplay = () => {
        if (!activeMatch) return 'League Idle';
        const homeName = activeMatch.home_name || activeMatch.home_id || 'Home';
        const awayName = activeMatch.away_name || activeMatch.away_id || 'Away';
        return `${homeName} ${activeMatch.score.left} - ${activeMatch.score.right} ${awayName}`;
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', height: '100%' }}>
            {/* Top Section: Header & Pitch */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {!activeMatch ? (
                    <div style={{
                        width: '100%', textAlign: 'center', padding: '12px',
                        background: 'rgba(15, 23, 42, 0.6)', borderRadius: '8px',
                        color: '#94a3b8', fontSize: '14px', fontWeight: 600, border: '1px solid rgba(148,163,184,0.1)'
                    }}>
                        {(() => {
                            if (!liveState?.availability) return 'League Idle';
                            const teams = Object.values(liveState.availability);
                            const unavailable = teams.filter(t => !t.available && !t.reason.includes('Bot'));
                            if (unavailable.length > 0) {
                                return `Waiting for Players (${unavailable.length} teams unavailable)`;
                            }
                            return 'League Active - Scheduling...';
                        })()}
                    </div>
                ) : (
                    <div style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        background: 'rgba(15, 23, 42, 0.8)',
                        padding: '12px 20px', borderRadius: '12px',
                        border: '1px solid rgba(148, 163, 184, 0.2)',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                    }}>
                        <div style={{
                            color: '#94a3b8', fontSize: '11px', fontWeight: 700,
                            textTransform: 'uppercase', letterSpacing: '0.05em', width: '80px'
                        }}>
                            Round {activeMatch.league_round ?? '?'}
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', flex: 1, justifyContent: 'center' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '24px', width: '100%', justifyContent: 'center' }}>
                                <div style={{ textAlign: 'right', flex: 1 }}>
                                    <div style={{ color: '#facc15', fontSize: '16px', fontWeight: 700, textShadow: '0 0 10px rgba(250, 204, 21, 0.2)' }}>
                                        {activeMatch.home_name || activeMatch.home_id || 'Home'}
                                    </div>
                                </div>

                                <div style={{
                                    display: 'flex', alignItems: 'center', gap: '12px',
                                    background: '#0f172a', padding: '6px 16px', borderRadius: '8px',
                                    border: '1px solid #334155'
                                }}>
                                    <span style={{ color: '#facc15', fontSize: '24px', fontWeight: 800, fontFamily: 'monospace', lineHeight: 1 }}>
                                        {activeMatch.score.left}
                                    </span>
                                    <span style={{ color: '#64748b', fontSize: '14px', fontWeight: 600 }}>-</span>
                                    <span style={{ color: '#f87171', fontSize: '24px', fontWeight: 800, fontFamily: 'monospace', lineHeight: 1 }}>
                                        {activeMatch.score.right}
                                    </span>
                                </div>

                                <div style={{ textAlign: 'left', flex: 1 }}>
                                    <div style={{ color: '#f87171', fontSize: '16px', fontWeight: 700, textShadow: '0 0 10px rgba(248, 113, 113, 0.2)' }}>
                                        {activeMatch.away_name || activeMatch.away_id || 'Away'}
                                    </div>
                                </div>
                            </div>

                            <div style={{
                                color: '#e2e8f0',
                                fontSize: '14px',
                                fontFamily: 'monospace',
                                fontWeight: 600,
                                background: 'rgba(15, 23, 42, 0.5)',
                                padding: '2px 8px',
                                borderRadius: '4px',
                                border: '1px solid rgba(148, 163, 184, 0.1)'
                            }}>
                                {(() => {
                                    const seconds = Math.floor((activeMatch.frame || 0) / 10);
                                    const mins = Math.floor(seconds / 60);
                                    const secs = seconds % 60;
                                    return `${mins}:${secs.toString().padStart(2, '0')}`;
                                })()}
                            </div>
                        </div>

                        <div style={{ width: '80px', textAlign: 'right' }}>
                            {/* Empty spacer or status icon */}
                            <span style={{
                                width: '8px', height: '8px', borderRadius: '50%',
                                background: '#22c55e', display: 'inline-block',
                                boxShadow: '0 0 8px #22c55e'
                            }} />
                        </div>
                    </div>
                )}

                {activeMatch ? (
                    <SoccerPitch gameState={activeMatch} width={undefined} height={undefined} style={{ flex: 1, minHeight: '300px' }} />
                ) : (
                    <div style={{
                        flex: 1,
                        minHeight: '300px',
                        border: '1px dashed rgba(148,163,184,0.4)',
                        borderRadius: '8px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#94a3b8',
                        background: 'rgba(15, 23, 42, 0.3)'
                    }}>
                        Waiting for scheduled match...
                    </div>
                )}
            </div>

            {/* Bottom Section: Leaderboard */}
            <div style={{ background: 'rgba(15, 23, 42, 0.5)', borderRadius: '8px', padding: '16px', border: '1px solid rgba(148,163,184,0.1)' }}>
                <div style={{ color: '#e2e8f0', fontWeight: 600, marginBottom: '12px' }}>League Standings</div>
                {liveState?.leaderboard ? (
                    <LeaderboardTable entries={liveState.leaderboard} />
                ) : (
                    <div style={{ color: '#64748b', fontSize: '12px', padding: '8px' }}>No stats available</div>
                )}
            </div>
        </div>
    );
}

// Subcomponents

function LeaderboardTable({ entries }: { entries: LeagueLeaderboardEntry[] }) {
    return (
        <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', fontSize: '11px', borderCollapse: 'collapse', color: '#cbd5e1' }}>
                <thead>
                    <tr style={{ borderBottom: '1px solid #334155', textAlign: 'left' }}>
                        <th style={{ padding: '6px 8px 6px 4px' }}>Team</th>
                        <th style={{ padding: '4px', textAlign: 'center' }}>P</th>
                        <th style={{ padding: '4px', textAlign: 'center' }}>W</th>
                        <th style={{ padding: '4px', textAlign: 'center' }}>D</th>
                        <th style={{ padding: '4px', textAlign: 'center' }}>L</th>
                        <th style={{ padding: '4px', textAlign: 'center' }}>Pts</th>
                    </tr>
                </thead>
                <tbody>
                    {entries.map((entry) => (
                        <tr key={entry.team_id} style={{ borderBottom: '1px solid rgba(51, 65, 85, 0.3)' }}>
                            <td style={{ padding: '4px 8px 4px 4px', fontWeight: 500 }} title={entry.display_name}>
                                {entry.display_name}
                            </td>
                            <td style={{ padding: '4px', textAlign: 'center', color: '#94a3b8' }}>{entry.matches_played}</td>
                            <td style={{ padding: '4px', textAlign: 'center', color: '#4ade80' }}>{entry.wins}</td>
                            <td style={{ padding: '4px', textAlign: 'center', color: '#94a3b8' }}>{entry.draws}</td>
                            <td style={{ padding: '4px', textAlign: 'center', color: '#f87171' }}>{entry.losses}</td>
                            <td style={{ padding: '4px', textAlign: 'center', fontWeight: 'bold', color: '#fbbf24' }}>{entry.points}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
