/**
 * Interactive poker game component
 */

import { PokerTable, PokerPlayer, PokerActions } from './poker';
import type { PokerGameState } from '../types/simulation';
import styles from './PokerGame.module.css';

interface PokerGameProps {
    onClose: () => void;
    onAction: (action: string, amount?: number) => void;
    onNewRound: () => void;
    gameState: PokerGameState | null;
    loading: boolean;
}

export function PokerGame({ onClose, onAction, onNewRound, gameState, loading }: PokerGameProps) {
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

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <div className={styles.headerLeft}>
                    <h2 className={styles.title}>
                        Poker Game
                        <span className={styles.handCounter}>Hand #{gameState.hands_played}</span>
                    </h2>
                    {gameState.message && (
                        <div className={styles.headerMessage}>{gameState.message}</div>
                    )}
                </div>
                <button onClick={onClose} className={styles.closeButton}>×</button>
            </div>

            {/* Pot and Community Cards */}
            <PokerTable
                pot={gameState.pot}
                communityCards={gameState.community_cards}
                currentRound={gameState.current_round}
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
                            /* Play Again / Cash Out buttons - Same position as action buttons */
                            <div className={styles.inlineGameOverButtons}>
                                {!gameState.session_over && (
                                    <button onClick={onNewRound} className={styles.inlinePlayAgainButton} disabled={loading}>
                                        {loading ? 'Dealing...' : 'Play Again'}
                                    </button>
                                )}
                                <button onClick={onClose} className={styles.inlineCashOutButton}>
                                    {gameState.session_over ? 'Exit' : 'Cash Out'}
                                </button>
                            </div>
                        )}
                    </div>

                    {/* Quit Button - Far right */}
                    {!gameState.game_over && (
                        <button onClick={onClose} className={styles.quitGameButton}>
                            Quit
                        </button>
                    )}
                </div>
            )}


            {/* Game Over - Compact result banner */}
            {gameState.game_over && !gameState.session_over && (
                <div className={`${styles.gameOverBanner} ${gameState.winner === 'You' ? styles.winBanner : styles.loseBanner}`}>
                    <div className={styles.resultInfo}>
                        <span className={styles.resultIcon}>{gameState.winner === 'You' ? '🏆' : '💀'}</span>
                        <span className={styles.resultText}>
                            {gameState.winner === 'You' ? 'You win' : `${gameState.winner} wins`}
                        </span>
                        <span className={styles.resultPot}>+{gameState.pot.toFixed(0)} ⚡</span>
                    </div>
                    <div className={styles.chipStandings}>
                        {gameState.players
                            .sort((a, b) => b.energy - a.energy)
                            .map((player) => (
                                <div key={player.player_id} className={`${styles.chipStanding} ${player.is_human ? styles.youChip : ''} ${player.energy <= 0 ? styles.eliminatedChip : ''}`}>
                                    <span className={styles.chipName}>{player.is_human ? 'You' : player.name.split('_')[0]}</span>
                                    <span className={styles.chipEnergy}>{player.energy <= 0 ? 'OUT' : player.energy.toFixed(0)}</span>
                                </div>
                            ))
                        }
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
                                    <span className={styles.finalEnergy}>{player.energy <= 0 ? 'Eliminated' : `${player.energy.toFixed(0)} ⚡`}</span>
                                </div>
                            ))
                        }
                    </div>
                </div>
            )}
        </div>
    );
}
