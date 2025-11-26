/**
 * Interactive poker game component
 */

import { useState, useEffect, useRef } from 'react';
import { PokerTable, PokerPlayer, PokerActions, FishAvatar } from './poker';
import type { PokerGameState } from '../types/simulation';
import { useErrorNotification } from '../hooks/useErrorNotification';
import { ErrorNotification } from './ErrorNotification';
import styles from './PokerGame.module.css';

interface PokerGameProps {
    onClose: () => void;
    onAction: (action: string, amount?: number) => void;
    onNewRound: () => void;
    onGetAutopilotAction: () => Promise<{ success: boolean; action: string; amount: number }>;
    gameState: PokerGameState | null;
    loading: boolean;
}

const AUTOPILOT_POLL_INTERVAL = 1000; // ms between autopilot checks
const AUTOPILOT_NEW_ROUND_DELAY = 1500; // ms before starting new hand

export function PokerGame({ onClose, onAction, onNewRound, onGetAutopilotAction, gameState, loading }: PokerGameProps) {
    const [autopilot, setAutopilot] = useState(false);
    const isProcessingRef = useRef(false);
    const lastActionTimeRef = useRef(0);
    const { errors, addError, clearError } = useErrorNotification();

    // Autopilot polling effect
    useEffect(() => {
        if (!autopilot || !gameState) return;

        const pollAutopilot = async () => {
            // Skip if already processing or loading
            if (isProcessingRef.current || loading) return;

            // Enforce minimum delay between actions
            const now = Date.now();
            if (now - lastActionTimeRef.current < AUTOPILOT_POLL_INTERVAL) return;

            isProcessingRef.current = true;

            try {
                const result = await onGetAutopilotAction();

                if (!result.success) {
                    isProcessingRef.current = false;
                    return;
                }

                const { action, amount } = result;

                if (action === 'exit') {
                    setAutopilot(false);
                } else if (action === 'new_round') {
                    // Delay before new round for readability
                    await new Promise(resolve => setTimeout(resolve, AUTOPILOT_NEW_ROUND_DELAY));
                    lastActionTimeRef.current = Date.now();
                    onNewRound();
                } else if (action === 'wait') {
                    // Not our turn, just wait for next poll
                } else {
                    // Execute the action (fold, check, call, raise)
                    lastActionTimeRef.current = Date.now();
                    onAction(action, amount);
                }
            } catch (error) {
                addError(error, 'Autopilot error');
                setAutopilot(false); // Disable autopilot on error
            }

            isProcessingRef.current = false;
        };

        // Poll immediately and then on interval
        pollAutopilot();
        const intervalId = setInterval(pollAutopilot, 500);

        return () => clearInterval(intervalId);
    }, [autopilot, gameState, loading, onGetAutopilotAction, onAction, onNewRound]);

    // Turn off autopilot when session ends
    useEffect(() => {
        if (gameState?.session_over) {
            setAutopilot(false);
        }
    }, [gameState?.session_over]);
    if (!gameState) {
        return (
            <div className={styles.container}>
                <div className={styles.header}>
                    <h2 className={styles.title}>Loading Poker Game...</h2>
                    <button onClick={onClose} className={styles.closeButton}>×</button>
                </div>
                <div className={styles.loading}>
                    <p>Setting up your poker game with the top 3 fish...</p>
                </div>
            </div>
        );
    }

    const handleFold = () => {
        // audioManager.playFold();
        onAction('fold');
    };

    const handleCheck = () => {
        // audioManager.playCheck();
        onAction('check');
    };

    const handleCall = () => {
        // audioManager.playCall();
        onAction('call');
    };

    const handleRaise = (amount: number) => {
        // audioManager.playRaise();
        onAction('raise', amount);
    };

    const humanPlayer = gameState.players.find(p => p.is_human);
    const aiPlayers = gameState.players.filter(p => !p.is_human);

    // Find winner player data for the result banner
    const winnerPlayer = gameState.winner === 'You'
        ? humanPlayer
        : aiPlayers.find(p => p.name === gameState.winner);

    return (
        <div className={styles.container}>
            <ErrorNotification errors={errors} onDismiss={clearError} />
            <div className={styles.header}>
                <div className={styles.headerLeft}>
                    <h2 className={styles.title}>
                        Poker Game
                        <span className={styles.handCounter}>Hand #{gameState.hands_played}</span>
                        <span className={styles.phaseIndicator}>{gameState.current_round?.replace('_', '-') || 'Starting'}</span>
                    </h2>
                    {gameState.message && (
                        <div className={styles.headerMessage}>{gameState.message}</div>
                    )}
                </div>
                <div className={styles.headerRight}>
                    <button onClick={onClose} className={styles.closeButton}>×</button>
                </div>
            </div>

            {/* Pot and Community Cards */}
            <PokerTable
                pot={gameState.pot}
                communityCards={gameState.community_cards}
                players={gameState.players}
                resultBanner={gameState.game_over && !gameState.session_over ? (
                    <div className={`${styles.resultBanner} ${gameState.winner === 'You' ? styles.winBanner : styles.loseBanner}`}>
                        {gameState.winner === 'You' ? (
                            <span className={styles.resultIcon}>🏆</span>
                        ) : (
                            <FishAvatar
                                fishId={winnerPlayer?.fish_id}
                                genomeData={winnerPlayer?.genome_data}
                                size="small"
                            />
                        )}
                        <span className={styles.resultText}>
                            {gameState.winner === 'You' ? 'You win' : `${gameState.winner} wins`}
                        </span>
                        <span className={styles.resultPot}>+{Math.round(gameState.pot)} ⚡</span>
                    </div>
                ) : undefined}
            />

            {/* AI Players */}
            <div className={styles.opponentsSection}>
                {aiPlayers.map((player) => (
                    <PokerPlayer
                        key={player.player_id}
                        name={player.name}
                        fishId={player.fish_id}
                        generation={player.generation}
                        genomeData={player.genome_data}
                        energy={player.energy}
                        currentBet={player.current_bet}
                        folded={player.folded}
                        isActive={player.name === gameState.current_player}
                        isHuman={false}
                        cards={player.hole_cards}
                    />
                ))}
            </div>

            {/* Human Player Section - Cards | Controls | Quit Button */}
            {humanPlayer && (
                <div className={styles.humanSection}>
                    <div className={styles.playerAndControls}>
                        <PokerPlayer
                            name="You"
                            energy={humanPlayer.energy}
                            currentBet={humanPlayer.current_bet}
                            folded={humanPlayer.folded}
                            isActive={gameState.is_your_turn}
                            isHuman={true}
                            cards={gameState.your_cards}
                        />

                        {/* Action Buttons - Right next to cards */}
                        {!gameState.game_over ? (
                            <PokerActions
                                isYourTurn={gameState.is_your_turn}
                                callAmount={gameState.call_amount}
                                minRaise={gameState.min_raise}
                                maxRaise={humanPlayer?.energy || 0}
                                loading={loading}
                                currentPlayer={gameState.current_player}
                                onFold={handleFold}
                                onCheck={handleCheck}
                                onCall={handleCall}
                                onRaise={handleRaise}
                            />
                        ) : (
                            /* Play Again button - Same position as action buttons */
                            !gameState.session_over && (
                                <button onClick={onNewRound} className={styles.inlinePlayAgainButton} disabled={loading}>
                                    {loading ? 'Dealing...' : 'Play Again'}
                                </button>
                            )
                        )}
                    </div>

                    {/* Autopilot + Cash Out - Far right */}
                    <div className={styles.controlsRight}>
                        <button
                            onClick={() => setAutopilot(!autopilot)}
                            className={`${styles.autopilotButton} ${autopilot ? styles.autopilotActive : ''}`}
                            disabled={gameState.session_over}
                        >
                            <span className={styles.autopilotIcon}>🤖</span>
                            <span className={styles.autopilotText}>{autopilot ? 'AUTO ON' : 'AUTO'}</span>
                        </button>
                        <button onClick={onClose} className={styles.cashOutButton}>
                            💰 Cash Out
                        </button>
                    </div>
                </div>
            )}


            {/* Session Over - Final results */}
            {gameState.session_over && (
                <div className={styles.sessionOverBanner}>
                    <div className={styles.sessionOverHeader}>
                        <span className={styles.sessionOverIcon}>🎰</span>
                        <span className={styles.sessionOverTitle}>Session Complete</span>
                        <span className={styles.sessionOverHands}>{gameState.hands_played} hands played</span>
                    </div>
                    <div className={styles.finalStandings}>
                        {gameState.players
                            .sort((a, b) => b.energy - a.energy)
                            .map((player, index) => (
                                <div key={player.player_id} className={`${styles.finalStanding} ${index === 0 ? styles.sessionWinner : ''} ${player.energy <= 0 ? styles.eliminated : ''}`}>
                                    <span className={styles.finalRank}>{index === 0 ? '👑' : `#${index + 1}`}</span>
                                    <span className={styles.finalName}>{player.is_human ? 'You' : player.name}</span>
                                    <span className={styles.finalEnergy}>{player.energy <= 0 ? 'Eliminated' : `${Math.round(player.energy)} ⚡`}</span>
                                </div>
                            ))
                        }
                    </div>
                </div>
            )}
        </div>
    );
}
