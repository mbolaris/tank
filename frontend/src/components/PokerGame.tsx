/**
 * Interactive poker game component
 */

import { Button } from './ui';
import { PokerTable, PokerPlayer, PokerActions } from './poker';
import type { PokerGameState } from '../types/simulation';
import styles from './PokerGame.module.css';

interface PokerGameProps {
    onClose: () => void;
    onAction: (action: string, amount?: number) => void;
    gameState: PokerGameState | null;
    loading: boolean;
}

export function PokerGame({ onClose, onAction, gameState, loading }: PokerGameProps) {
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
                <h2 className={styles.title}>Poker Game</h2>
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
                        energy={player.energy}
                        currentBet={player.current_bet}
                        folded={player.folded}
                        isActive={player.name === gameState.current_player}
                        isHuman={false}
                        cards={player.hole_cards}
                    />
                ))}
            </div>

            {/* Human Player Section - Cards, Chips, and Actions side by side */}
            {humanPlayer && (
                <div className={styles.humanSection}>
                    <PokerPlayer
                        name="You"
                        energy={humanPlayer.energy}
                        currentBet={humanPlayer.current_bet}
                        folded={humanPlayer.folded}
                        isActive={false}
                        isHuman={true}
                        cards={gameState.your_cards}
                    />

                    {/* Action Buttons */}
                    {!gameState.game_over && (
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
                    )}
                </div>
            )}

            {/* Game Message */}
            {gameState.message && (
                <div className={styles.message}>{gameState.message}</div>
            )}

            {/* Game Over */}
            {gameState.game_over && (
                <div className={styles.gameOver}>
                    <h3 className={styles.gameOverTitle}>Game Over!</h3>
                    <p className={styles.gameOverMessage}>
                        {gameState.winner === 'You'
                            ? `Congratulations! You won ${gameState.pot.toFixed(1)} energy!`
                            : `${gameState.winner} won the pot of ${gameState.pot.toFixed(1)} energy.`
                        }
                    </p>
                    <Button onClick={onClose} variant="success" className={styles.newGameButton}>
                        Close
                    </Button>
                </div>
            )}
        </div>
    );
}
