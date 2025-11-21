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
                <h2 className={styles.title}>
                    Poker Game
                    <span className={styles.handCounter}>Hand #{gameState.hands_played}</span>
                </h2>
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

            {/* Game Message */}
            {gameState.message && (
                <div className={styles.message}>{gameState.message}</div>
            )}

            {/* Game Over - Show after hand ends */}
            {gameState.game_over && (
                <div className={`${styles.gameOver} ${gameState.winner === 'You' ? styles.winnerGlow : ''}`}>
                    <div className={styles.resultBanner}>
                        {gameState.winner === 'You' ? (
                            <>
                                <span className={styles.winEmoji}>&#127881;</span>
                                <h3 className={styles.winTitle}>YOU WIN!</h3>
                                <span className={styles.winEmoji}>&#127881;</span>
                            </>
                        ) : (
                            <h3 className={styles.loseTitle}>{gameState.winner} wins</h3>
                        )}
                    </div>
                    <div className={styles.potWon}>
                        <span className={styles.potAmount}>+{gameState.pot.toFixed(0)}</span>
                        <span className={styles.potLabel}>energy</span>
                    </div>
                    {/* Show player standings */}
                    <div className={styles.standings}>
                        {gameState.players
                            .sort((a, b) => b.energy - a.energy)
                            .map((player, i) => (
                                <div key={player.player_id} className={`${styles.standingRow} ${player.is_human ? styles.humanStanding : ''}`}>
                                    <span className={styles.standingRank}>
                                        {i === 0 ? '&#128081;' : `#${i + 1}`}
                                    </span>
                                    <span className={styles.standingName}>{player.is_human ? 'You' : player.name}</span>
                                    <span className={styles.standingEnergy}>{player.energy.toFixed(0)}</span>
                                </div>
                            ))
                        }
                    </div>
                    {gameState.session_over && (
                        <div className={styles.sessionOverMessage}>
                            {humanPlayer && humanPlayer.energy > 100 ? 'Great session! You made profit!' : 'Better luck next time!'}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
