import { useEffect, useState } from 'react';
import type { LeagueLeaderboardEntry, SoccerLeagueLiveState, TeamAvailability } from '../types/simulation';
import { SoccerPitch } from './SoccerPitch';
import { Button } from './ui';

interface SoccerLeagueLiveProps {
    liveState?: SoccerLeagueLiveState | null;
    isConnected: boolean;
    onCommand: (command: { command: string; data?: Record<string, unknown> }) => void;
}

export function SoccerLeagueLive({ liveState, isConnected, onCommand }: SoccerLeagueLiveProps) {
    const [enabled, setEnabled] = useState(Boolean(liveState?.active_match));

    // Config state
    const [matchEveryFrames, setMatchEveryFrames] = useState(60);
    const [cyclesPerFrame, setCyclesPerFrame] = useState(2);
    const [entryFeeEnergy, setEntryFeeEnergy] = useState(10);
    const [rewardMode, setRewardMode] = useState<'pot_payout' | 'refill_to_max'>('refill_to_max');
    const [reproCreditAward, setReproCreditAward] = useState(2);

    const activeMatch = liveState?.active_match;

    useEffect(() => {
        if (activeMatch) {
            setEnabled(true);
        }
    }, [activeMatch?.match_id]);

    const handleToggle = () => {
        const next = !enabled;
        setEnabled(next);
        onCommand({ command: 'set_soccer_league_enabled', data: { enabled: next } });
    };

    const handleApplyConfig = () => {
        onCommand({
            command: 'set_soccer_league_config',
            data: {
                match_every_frames: matchEveryFrames,
                cycles_per_frame: cyclesPerFrame,
                entry_fee_energy: entryFeeEnergy,
                reward_mode: rewardMode,
                repro_credit_award: reproCreditAward,
            },
        });
    };

    const getScoreDisplay = () => {
        if (!activeMatch) return 'League Idle';
        const homeName = activeMatch.home_id || 'Home';
        const awayName = activeMatch.away_id || 'Away';
        return `${homeName} ${activeMatch.score.left} - ${activeMatch.score.right} ${awayName}`;
    };

    return (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '16px', height: '100%' }}>
            {/* Left Column: Pitch */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ color: '#93c5fd', fontWeight: 700 }}>
                        {activeMatch ? `Round ${activeMatch.league_round ?? '?'} Match` : 'League Pitch'}
                    </div>
                    <div style={{ color: '#e2e8f0', fontSize: '14px', fontWeight: 600 }}>
                        {getScoreDisplay()}
                    </div>
                </div>

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

                {/* Availability Diagnostics */}
                {liveState?.availability && <AvailabilityPanel availability={liveState.availability} />}
            </div>

            {/* Right Column: Leaderboard & Controls */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

                {/* Leaderboard */}
                <div style={{ background: 'rgba(15, 23, 42, 0.5)', borderRadius: '8px', padding: '12px', border: '1px solid rgba(148,163,184,0.1)' }}>
                    <div style={{ color: '#e2e8f0', fontWeight: 600, marginBottom: '8px' }}>League Standings</div>
                    {liveState?.leaderboard ? (
                        <LeaderboardTable entries={liveState.leaderboard} />
                    ) : (
                        <div style={{ color: '#64748b', fontSize: '12px', padding: '8px' }}>No stats available</div>
                    )}
                </div>

                {/* Controls */}
                <div style={{ background: 'rgba(15, 23, 42, 0.5)', borderRadius: '8px', padding: '12px', border: '1px solid rgba(148,163,184,0.1)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                        <div style={{ color: '#e2e8f0', fontWeight: 600 }}>League Admin</div>
                        <Button
                            onClick={handleToggle}
                            disabled={!isConnected}
                            variant={enabled ? 'secondary' : 'primary'}
                            style={{ padding: '4px 8px', fontSize: '12px' }}
                        >
                            {enabled ? 'Disable' : 'Enable'}
                        </Button>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <ConfigInput label="Match Frequency (frames)" value={matchEveryFrames} onChange={setMatchEveryFrames} min={1} max={600} />
                        <ConfigInput label="Sim Speed (cycles/frame)" value={cyclesPerFrame} onChange={setCyclesPerFrame} min={1} max={20} />
                        <ConfigInput label="Entry Fee" value={entryFeeEnergy} onChange={setEntryFeeEnergy} min={0} max={500} />

                        <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#94a3b8', fontSize: '11px' }}>
                            Reward Mode
                            <select
                                value={rewardMode}
                                onChange={(e) => setRewardMode(e.target.value as any)}
                                style={{ background: '#1e293b', border: '1px solid #334155', color: '#e2e8f0', borderRadius: '4px', fontSize: '11px', padding: '2px' }}
                            >
                                <option value="refill_to_max">Refill Max</option>
                                <option value="pot_payout">Pot Payout</option>
                            </select>
                        </label>

                        <ConfigInput label="Repro Credits" value={reproCreditAward} onChange={setReproCreditAward} step={0.5} />

                        <Button onClick={handleApplyConfig} disabled={!isConnected} variant="secondary" style={{ marginTop: '4px', fontSize: '11px', padding: '4px' }}>
                            Apply Settings
                        </Button>
                    </div>
                </div>
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
                        <th style={{ padding: '4px' }}>Team</th>
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
                            <td style={{ padding: '4px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '100px' }} title={entry.display_name}>
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

function AvailabilityPanel({ availability }: { availability: Record<string, TeamAvailability> }) {
    const teams = Object.entries(availability).sort();

    return (
        <div style={{
            background: 'rgba(15, 23, 42, 0.5)',
            borderRadius: '8px',
            padding: '8px 12px',
            border: '1px solid rgba(148,163,184,0.1)',
            maxHeight: '150px',
            overflowY: 'auto'
        }}>
            <div style={{ color: '#94a3b8', fontSize: '11px', fontWeight: 600, marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Team Status
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '6px' }}>
                {teams.map(([teamId, status]) => (
                    <div key={teamId} style={{
                        display: 'flex',
                        alignItems: 'center',
                        fontSize: '10px',
                        padding: '4px 6px',
                        background: status.available ? 'rgba(74, 222, 128, 0.1)' : 'rgba(148, 163, 184, 0.1)',
                        borderRadius: '4px',
                        border: `1px solid ${status.available ? 'rgba(74, 222, 128, 0.2)' : 'rgba(148, 163, 184, 0.2)'}`,
                    }}
                        title={status.reason}>
                        <div style={{
                            width: '6px',
                            height: '6px',
                            borderRadius: '50%',
                            background: status.available ? '#4ade80' : '#64748b',
                            marginRight: '6px'
                        }} />
                        <div style={{ color: status.available ? '#cbd5e1' : '#64748b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {teamId}: {status.count} eligible
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function ConfigInput({ label, value, onChange, min, max, step }: any) {
    return (
        <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#94a3b8', fontSize: '11px' }}>
            {label}
            <input
                type="number"
                min={min}
                max={max}
                step={step}
                value={value}
                onChange={(e) => onChange(Number(e.target.value))}
                style={{
                    width: '60px',
                    background: '#1e293b',
                    border: '1px solid #334155',
                    color: '#e2e8f0',
                    borderRadius: '4px',
                    fontSize: '11px',
                    padding: '2px 4px',
                    textAlign: 'right'
                }}
            />
        </label>
    );
}
