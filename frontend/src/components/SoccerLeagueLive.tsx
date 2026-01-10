import { useEffect, useState } from 'react';
import type { SoccerLeagueLiveState } from '../types/simulation';
import { SoccerPitch } from './SoccerPitch';
import { Button } from './ui';

interface SoccerLeagueLiveProps {
    liveState?: SoccerLeagueLiveState | null;
    isConnected: boolean;
    onCommand: (command: { command: string; data?: Record<string, unknown> }) => void;
}

export function SoccerLeagueLive({ liveState, isConnected, onCommand }: SoccerLeagueLiveProps) {
    const [enabled, setEnabled] = useState(Boolean(liveState));
    const [matchEveryFrames, setMatchEveryFrames] = useState(60);
    const [cyclesPerFrame, setCyclesPerFrame] = useState(2);
    const [entryFeeEnergy, setEntryFeeEnergy] = useState(10);
    const [rewardMode, setRewardMode] = useState<'pot_payout' | 'refill_to_max'>('refill_to_max');
    const [reproCreditAward, setReproCreditAward] = useState(2);

    useEffect(() => {
        if (liveState) {
            setEnabled(true);
        }
    }, [liveState?.match_id]);

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

    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 0.8fr)', gap: '16px' }}>
            <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <div style={{ color: '#93c5fd', fontWeight: 700 }}>League Pitch</div>
                    <div style={{ color: '#e2e8f0', fontSize: '12px' }}>
                        {liveState ? `${liveState.score.left} - ${liveState.score.right}` : 'Idle'}
                    </div>
                </div>
                {liveState ? (
                    <SoccerPitch gameState={liveState} width={640} height={360} />
                ) : (
                    <div style={{ height: '360px', border: '1px dashed rgba(148,163,184,0.4)', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
                        League match idle
                    </div>
                )}
                {liveState?.last_goal && (
                    <div style={{ marginTop: '8px', color: '#cbd5f5', fontSize: '12px' }}>
                        Last goal: {liveState.last_goal.team?.toUpperCase()} @ {liveState.last_goal.frame ?? '-'}
                    </div>
                )}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ color: '#e2e8f0', fontWeight: 600 }}>League Controls</div>
                    <Button
                        onClick={handleToggle}
                        disabled={!isConnected}
                        variant={enabled ? 'secondary' : 'primary'}
                        style={{ padding: '6px 12px' }}
                    >
                        {enabled ? 'Disable' : 'Enable'}
                    </Button>
                </div>

                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', color: '#94a3b8', fontSize: '12px' }}>
                    Match every frames
                    <input
                        type="number"
                        min={1}
                        max={600}
                        value={matchEveryFrames}
                        onChange={(e) => setMatchEveryFrames(Number(e.target.value))}
                    />
                </label>

                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', color: '#94a3b8', fontSize: '12px' }}>
                    Cycles per frame
                    <input
                        type="number"
                        min={1}
                        max={20}
                        value={cyclesPerFrame}
                        onChange={(e) => setCyclesPerFrame(Number(e.target.value))}
                    />
                </label>

                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', color: '#94a3b8', fontSize: '12px' }}>
                    Entry fee energy
                    <input
                        type="number"
                        min={0}
                        max={500}
                        value={entryFeeEnergy}
                        onChange={(e) => setEntryFeeEnergy(Number(e.target.value))}
                    />
                </label>

                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', color: '#94a3b8', fontSize: '12px' }}>
                    Reward mode
                    <select
                        value={rewardMode}
                        onChange={(e) => setRewardMode(e.target.value as 'pot_payout' | 'refill_to_max')}
                    >
                        <option value="refill_to_max">Refill to max</option>
                        <option value="pot_payout">Pot payout</option>
                    </select>
                </label>

                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', color: '#94a3b8', fontSize: '12px' }}>
                    Repro credits per win
                    <input
                        type="number"
                        min={0}
                        max={10}
                        step={0.5}
                        value={reproCreditAward}
                        onChange={(e) => setReproCreditAward(Number(e.target.value))}
                    />
                </label>

                <Button onClick={handleApplyConfig} disabled={!isConnected} variant="secondary">
                    Apply League Settings
                </Button>
            </div>
        </div>
    );
}
