import { useState, useCallback, useRef, useEffect } from 'react';
import { PokerGame } from '../PokerGame';
import { PokerLeaderboard } from '../PokerLeaderboard';
import PokerEvents from '../PokerEvents';
import { EvolutionBenchmarkDisplay } from '../EvolutionBenchmarkDisplay';
import { Button, CardsIcon, PlantIcon, CollapsibleSection } from '../ui';
import type {
    Command,
    CommandResponse,
    PokerGameState,
    PokerLeaderboardEntry,
    PokerEventData,
    PokerStatsData,
} from '../../types/simulation';
import styles from './TankPokerTab.module.css';

interface TankPokerTabProps {
    worldId: string | undefined;
    isConnected: boolean;
    pokerLeaderboard: PokerLeaderboardEntry[];
    pokerEvents: PokerEventData[];
    pokerStats: PokerStatsData | undefined;
    currentFrame: number;
    sendCommandWithResponse: (command: Command) => Promise<PokerCommandResponse>;
}

type PokerCommandResponse = CommandResponse & {
    action?: string;
    amount?: number;
};

export function TankPokerTab({
    worldId,
    isConnected,
    pokerLeaderboard,
    pokerEvents,
    pokerStats,
    currentFrame,
    sendCommandWithResponse,
}: TankPokerTabProps) {
    const [pokerGameState, setPokerGameState] = useState<PokerGameState | null>(null);
    const [showPokerGame, setShowPokerGame] = useState(true);
    const [pokerLoading, setPokerLoading] = useState(false);
    const [pokerError, setPokerError] = useState<string | null>(null);
    const [restartCountdown, setRestartCountdown] = useState<number | null>(null);

    const handlePokerError = (message: string, error?: unknown) => {
        const errorDetail = error instanceof Error ? error.message : String(error ?? '');
        const fullMessage = errorDetail ? `${message}: ${errorDetail}` : message;
        setPokerError(fullMessage);
        setTimeout(() => setPokerError(null), 5000);
    };

    // Process AI turns one at a time with delay for visual feedback
    const processAiTurnsWithDelay = useCallback(async () => {
        const AI_TURN_DELAY = 1000;

        const processNextAiTurn = async (): Promise<void> => {
            try {
                await new Promise(resolve => setTimeout(resolve, AI_TURN_DELAY));

                const response = await sendCommandWithResponse({
                    command: 'poker_process_ai_turn',
                    data: {},
                });

                if (response.state) {
                    setPokerGameState(response.state);
                }

                if (response.action_taken) {
                    await processNextAiTurn();
                }
            } catch (error) {
                handlePokerError('Failed to process AI turn', error);
            }
        };

        await processNextAiTurn();
    }, [sendCommandWithResponse]);

    const handleStartPoker = useCallback(async () => {
        try {
            setPokerLoading(true);
            setShowPokerGame(true);
            const response = await sendCommandWithResponse({
                command: 'start_poker',
                data: { energy: 500 },
            });
            if (response.success === false) {
                console.warn("Failed to auto-start poker:", response.error);
                handlePokerError('Failed to start poker game', response.error);
            } else if (response.state) {
                setPokerGameState(response.state);
                if (!response.state.is_your_turn && !response.state.game_over) {
                    processAiTurnsWithDelay();
                }
            }
        } catch (error) {
            handlePokerError('Failed to start poker game', error);
            setShowPokerGame(false);
        } finally {
            setPokerLoading(false);
        }
    }, [sendCommandWithResponse, processAiTurnsWithDelay]);

    // Auto-restart game when session ends
    useEffect(() => {
        let timer: NodeJS.Timeout;
        let countdownInterval: NodeJS.Timeout;

        if (showPokerGame && pokerGameState?.session_over) {
            setRestartCountdown(3);

            // Countdown visual update
            countdownInterval = setInterval(() => {
                setRestartCountdown(prev => (prev !== null && prev > 0 ? prev - 1 : 0));
            }, 1000);

            timer = setTimeout(() => {
                // Call the start logic
                handleStartPoker().then(() => {
                    setRestartCountdown(null);
                });
            }, 3000); // 3 seconds delay
        } else {
            setRestartCountdown(null);
        }

        return () => {
            clearTimeout(timer);
            clearInterval(countdownInterval);
        };
    }, [showPokerGame, pokerGameState?.session_over, handleStartPoker]);

    // Effect to start game once connected
    const hasStartedRef = useRef(false);
    useEffect(() => {
        if (isConnected && !hasStartedRef.current && !pokerGameState && !pokerLoading) {
            hasStartedRef.current = true;
            handleStartPoker();
        }
    }, [isConnected, pokerGameState, pokerLoading, handleStartPoker]);

    const handlePokerAction = async (action: string, amount?: number) => {
        try {
            setPokerLoading(true);
            const response = await sendCommandWithResponse({
                command: 'poker_action',
                data: { action, amount: amount || 0 },
            });
            if (response.success === false) {
                alert(response.error || 'Invalid action');
            } else if (response.state) {
                setPokerGameState(response.state);
                processAiTurnsWithDelay();
            }
        } catch (error) {
            handlePokerError('Failed to send poker action', error);
        } finally {
            setPokerLoading(false);
        }
    };

    const handleClosePoker = () => {
        setShowPokerGame(false);
        setPokerGameState(null);
    };

    const handleNewRound = async () => {
        try {
            setPokerLoading(true);
            const response = await sendCommandWithResponse({
                command: 'poker_new_round',
                data: {},
            });
            if (response.success === false) {
                alert(response.error || 'Failed to start new round');
            } else if (response.state) {
                setPokerGameState(response.state);
                if (!response.state.is_your_turn && !response.state.game_over) {
                    processAiTurnsWithDelay();
                }
            }
        } catch (error) {
            handlePokerError('Failed to start new poker round', error);
        } finally {
            setPokerLoading(false);
        }
    };

    const handleGetAutopilotAction = async () => {
        const response = await sendCommandWithResponse({
            command: 'poker_autopilot_action',
            data: {},
        });
        return response as { success: boolean; action?: string; amount?: number };
    };

    return (
        <div className={styles.pokerTab}>
            {/* Play Poker Section */}
            <div className="glass-panel" style={{ padding: '16px' }}>
                <h2 className={styles.sectionTitle}>
                    <CardsIcon size={20} style={{ color: '#a78bfa' }} />
                    Play Poker
                    {showPokerGame && (
                        <span className={styles.activeBadge}>Active Game</span>
                    )}
                </h2>

                <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'center' }}>
                    {!showPokerGame ? (
                        <div className={styles.welcomeSection}>
                            <CardsIcon size={48} style={{ color: '#a78bfa' }} />
                            <div className={styles.welcomeText}>
                                Ready to play a hand against the population?
                            </div>
                            <Button
                                onClick={handleStartPoker}
                                disabled={!isConnected || pokerLoading}
                                variant="poker"
                                style={{ padding: '12px 32px', fontSize: '16px' }}
                            >
                                <CardsIcon size={16} /> {pokerLoading ? 'Loading...' : 'Sit Down & Play'}
                            </Button>
                        </div>
                    ) : (
                        <div style={{ position: 'relative' }}>
                            <PokerGame
                                onClose={handleClosePoker}
                                onAction={handlePokerAction}
                                onNewRound={handleNewRound}
                                onGetAutopilotAction={handleGetAutopilotAction}
                                gameState={pokerGameState}
                                loading={pokerLoading}
                            />
                            {restartCountdown !== null && (
                                <div style={{
                                    position: 'absolute',
                                    bottom: '80px',
                                    left: '50%',
                                    transform: 'translateX(-50%)',
                                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                                    color: '#fff',
                                    padding: '8px 16px',
                                    borderRadius: '20px',
                                    zIndex: 10,
                                    border: '1px solid #a78bfa',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
                                }}>
                                    <span style={{ fontSize: '18px' }}>🔄</span>
                                    <span>Starting new game in {restartCountdown}...</span>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Evolution Benchmark */}
            <div style={{ marginTop: '20px' }}>
                <EvolutionBenchmarkDisplay worldId={worldId} />
            </div>

            {/* Poker Dashboard - Stats, Leaderboard & Activity */}
            <div className="glass-panel" style={{ padding: '16px', marginTop: '20px' }}>
                <CollapsibleSection title="Poker Dashboard" defaultExpanded={false}>

                    {/* Key Metrics Row */}
                    <div className={styles.metricsGrid}>
                        <MetricCard label="Total Games" value={pokerStats?.total_games?.toLocaleString() ?? '0'} />
                        <MetricCard
                            label="Economy Volume"
                            value={`${Math.round(pokerStats?.total_energy_won ?? 0).toLocaleString()}⚡`}
                        />
                        <MetricCard label="Avg Win Rate" value={pokerStats?.win_rate_pct ?? '0.0%'} />
                        <MetricCard
                            label="Plant Win Rate"
                            value={pokerStats?.plant_win_rate_pct ?? '0.0%'}
                            valueColor="#4ade80"
                            icon={<PlantIcon size={12} />}
                            subValue={`${pokerStats?.plant_poker_wins ?? 0}W / ${pokerStats?.fish_poker_wins ?? 0}L`}
                        />
                        <MetricCard label="Plant Games" value={pokerStats?.total_plant_games?.toLocaleString() ?? '0'} />
                    </div>

                    {/* Leaderboard and Activity Grid */}
                    <div className={styles.dashboardGrid}>
                        <div className={styles.dashboardCard}>
                            <PokerLeaderboard leaderboard={pokerLeaderboard} />
                        </div>
                        <div className={styles.dashboardCard}>
                            <PokerEvents events={pokerEvents} currentFrame={currentFrame} />
                        </div>
                    </div>
                </CollapsibleSection>
            </div>

            {/* Poker Error Notification */}
            {pokerError && (
                <div className={styles.errorNotification}>
                    <span>⚠️</span>
                    <span>{pokerError}</span>
                    <button onClick={() => setPokerError(null)} className={styles.errorClose}>
                        ✕
                    </button>
                </div>
            )}
        </div>
    );
}

function MetricCard({
    label,
    value,
    valueColor = '#f1f5f9',
    icon,
    subValue,
}: {
    label: string;
    value: string;
    valueColor?: string;
    icon?: React.ReactNode;
    subValue?: string;
}) {
    return (
        <div className={styles.metricCard}>
            <div className={styles.metricLabel}>
                {icon}
                {label}
            </div>
            <div className={styles.metricValue} style={{ color: valueColor }}>
                {value}
            </div>
            {subValue && <div className={styles.metricSub}>{subValue}</div>}
        </div>
    );
}
