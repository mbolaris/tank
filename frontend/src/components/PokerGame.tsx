/**
 * Interactive poker game component
 */

import { useState } from 'react';
import { colors, commonStyles } from '../styles/theme';

interface PokerGamePlayer {
  player_id: string;
  name: string;
  energy: number;
  current_bet: number;
  total_bet: number;
  folded: boolean;
  is_human: boolean;
  algorithm?: string;
  hole_cards: string[];
}

interface PokerGameState {
  game_id: string;
  pot: number;
  current_round: string;
  community_cards: string[];
  current_player: string;
  is_your_turn: boolean;
  game_over: boolean;
  message: string;
  winner: string | null;
  players: PokerGamePlayer[];
  your_cards: string[];
  call_amount: number;
  min_raise: number;
}

interface PokerGameProps {
  onClose: () => void;
  onAction: (action: string, amount?: number) => void;
  gameState: PokerGameState | null;
  loading: boolean;
}

export function PokerGame({ onClose, onAction, gameState, loading }: PokerGameProps) {
  const [raiseAmount, setRaiseAmount] = useState<number>(0);
  const [showRaiseInput, setShowRaiseInput] = useState(false);

  if (!gameState) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <h2 style={styles.title}>Loading Poker Game...</h2>
          <button onClick={onClose} style={styles.closeButton}>×</button>
        </div>
        <div style={styles.loading}>
          <p>Setting up your poker game with the top 3 fish...</p>
        </div>
      </div>
    );
  }

  const handleFold = () => {
    onAction('fold');
    setShowRaiseInput(false);
  };

  const handleCheck = () => {
    onAction('check');
    setShowRaiseInput(false);
  };

  const handleCall = () => {
    onAction('call');
    setShowRaiseInput(false);
  };

  const handleRaise = () => {
    if (raiseAmount > 0) {
      onAction('raise', raiseAmount);
      setShowRaiseInput(false);
      setRaiseAmount(0);
    }
  };

  const handleShowRaise = () => {
    setShowRaiseInput(true);
    setRaiseAmount(gameState.min_raise);
  };

  const humanPlayer = gameState.players.find(p => p.is_human);
  const aiPlayers = gameState.players.filter(p => !p.is_human);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Poker Game - {gameState.current_round}</h2>
        <button onClick={onClose} style={styles.closeButton}>×</button>
      </div>

        {/* Pot and Community Cards */}
        <div style={styles.tableSection}>
          <div style={styles.pot}>
            <div style={styles.potLabel}>Pot</div>
            <div style={styles.potAmount}>{gameState.pot.toFixed(1)} ⚡</div>
          </div>

          <div style={styles.communityCards}>
            {gameState.community_cards.length > 0 ? (
              gameState.community_cards.map((card, idx) => (
                <div key={idx} style={styles.card}>{card}</div>
              ))
            ) : (
              <div style={styles.noCards}>No community cards yet</div>
            )}
          </div>
        </div>

        {/* AI Players */}
        <div style={styles.opponentsSection}>
          {aiPlayers.map((player, idx) => (
            <div
              key={player.player_id}
              style={{
                ...styles.opponent,
                ...(player.folded && styles.foldedPlayer),
                ...(player.name === gameState.current_player && styles.activePlayer),
              }}
            >
              <div style={styles.opponentName}>{player.name}</div>
              <div style={styles.opponentInfo}>
                <div style={styles.opponentCards}>
                  {player.hole_cards.map((card, i) => (
                    <div key={i} style={styles.cardSmall}>{card}</div>
                  ))}
                </div>
                <div style={styles.opponentStats}>
                  <div>Energy: {player.energy.toFixed(1)} ⚡</div>
                  {player.current_bet > 0 && (
                    <div style={styles.bet}>Bet: {player.current_bet.toFixed(1)}</div>
                  )}
                  {player.folded && <div style={styles.foldedLabel}>FOLDED</div>}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Human Player */}
        {humanPlayer && (
          <div style={styles.playerSection}>
            <div style={styles.playerInfo}>
              <div style={styles.playerName}>You</div>
              <div style={styles.playerStats}>
                <div>Energy: {humanPlayer.energy.toFixed(1)} ⚡</div>
                {humanPlayer.current_bet > 0 && (
                  <div>Current Bet: {humanPlayer.current_bet.toFixed(1)}</div>
                )}
              </div>
            </div>

            <div style={styles.yourCards}>
              <div style={styles.cardsLabel}>Your Cards:</div>
              <div style={styles.cardsContainer}>
                {gameState.your_cards.map((card, idx) => (
                  <div key={idx} style={styles.cardLarge}>{card}</div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Game Message */}
        {gameState.message && (
          <div style={styles.message}>{gameState.message}</div>
        )}

        {/* Action Buttons */}
        {!gameState.game_over && (
          <div style={styles.actions}>
            {gameState.is_your_turn ? (
              <>
                {!showRaiseInput ? (
                  <>
                    <button
                      onClick={handleFold}
                      style={{ ...styles.actionButton, ...styles.foldButton }}
                      disabled={loading}
                    >
                      Fold
                    </button>

                    {gameState.call_amount === 0 ? (
                      <button
                        onClick={handleCheck}
                        style={{ ...styles.actionButton, ...styles.checkButton }}
                        disabled={loading}
                      >
                        Check
                      </button>
                    ) : (
                      <button
                        onClick={handleCall}
                        style={{ ...styles.actionButton, ...styles.callButton }}
                        disabled={loading}
                      >
                        Call {gameState.call_amount.toFixed(1)}
                      </button>
                    )}

                    <button
                      onClick={handleShowRaise}
                      style={{ ...styles.actionButton, ...styles.raiseButton }}
                      disabled={loading}
                    >
                      {gameState.call_amount > 0 ? 'Raise' : 'Bet'}
                    </button>
                  </>
                ) : (
                  <div style={styles.raiseInputContainer}>
                    <input
                      type="number"
                      value={raiseAmount}
                      onChange={(e) => setRaiseAmount(Number(e.target.value))}
                      min={gameState.min_raise}
                      max={humanPlayer?.energy || 0}
                      step={gameState.min_raise}
                      style={styles.raiseInput}
                    />
                    <button
                      onClick={handleRaise}
                      style={{ ...styles.actionButton, ...styles.raiseButton }}
                      disabled={loading || raiseAmount < gameState.min_raise}
                    >
                      Confirm {raiseAmount.toFixed(1)}
                    </button>
                    <button
                      onClick={() => setShowRaiseInput(false)}
                      style={{ ...styles.actionButton, ...styles.cancelButton }}
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div style={styles.waitingMessage}>
                Waiting for {gameState.current_player}...
              </div>
            )}
          </div>
        )}

        {/* Game Over */}
        {gameState.game_over && (
          <div style={styles.gameOver}>
            <h3 style={styles.gameOverTitle}>Game Over!</h3>
            <p style={styles.gameOverMessage}>
              {gameState.winner === 'You'
                ? `Congratulations! You won ${gameState.pot.toFixed(1)} energy!`
                : `${gameState.winner} won the pot of ${gameState.pot.toFixed(1)} energy.`
              }
            </p>
            <button onClick={onClose} style={styles.newGameButton}>
              Close
            </button>
          </div>
        )}
    </div>
  );
}

const styles = {
  container: {
    backgroundColor: colors.bgDark,
    borderRadius: '12px',
    padding: '20px',
    border: `2px solid ${colors.primary}`,
    boxShadow: '0 0 20px rgba(0, 255, 0, 0.2)',
    width: '100%',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
    borderBottom: `1px solid ${colors.border}`,
    paddingBottom: '12px',
  },
  title: {
    margin: 0,
    fontSize: '24px',
    color: colors.primary,
  },
  closeButton: {
    background: 'none',
    border: 'none',
    color: colors.text,
    fontSize: '32px',
    cursor: 'pointer',
    padding: '0 8px',
  },
  loading: {
    padding: '40px',
    textAlign: 'center' as const,
    fontSize: '16px',
  },
  tableSection: {
    marginBottom: '24px',
    padding: '20px',
    backgroundColor: colors.bgDarker,
    borderRadius: '8px',
  },
  pot: {
    textAlign: 'center' as const,
    marginBottom: '16px',
  },
  potLabel: {
    fontSize: '14px',
    color: colors.textSecondary,
    marginBottom: '4px',
  },
  potAmount: {
    fontSize: '28px',
    fontWeight: 'bold',
    color: colors.accent,
  },
  communityCards: {
    display: 'flex',
    gap: '8px',
    justifyContent: 'center',
    flexWrap: 'wrap' as const,
  },
  card: {
    backgroundColor: colors.bgLight,
    border: `2px solid ${colors.border}`,
    borderRadius: '6px',
    padding: '12px 16px',
    fontSize: '24px',
    fontWeight: 'bold',
    minWidth: '60px',
    textAlign: 'center' as const,
  },
  cardSmall: {
    backgroundColor: colors.bgLight,
    border: `1px solid ${colors.border}`,
    borderRadius: '4px',
    padding: '4px 8px',
    fontSize: '16px',
    fontWeight: 'bold',
    minWidth: '40px',
    textAlign: 'center' as const,
  },
  cardLarge: {
    backgroundColor: colors.bgLight,
    border: `3px solid ${colors.primary}`,
    borderRadius: '8px',
    padding: '16px 20px',
    fontSize: '32px',
    fontWeight: 'bold',
    minWidth: '80px',
    textAlign: 'center' as const,
    boxShadow: '0 0 10px rgba(0, 255, 0, 0.3)',
  },
  noCards: {
    color: colors.textSecondary,
    fontSize: '14px',
    fontStyle: 'italic',
  },
  opponentsSection: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '12px',
    marginBottom: '24px',
  },
  opponent: {
    padding: '12px',
    backgroundColor: colors.bgLight,
    borderRadius: '8px',
    border: `1px solid ${colors.border}`,
  },
  activePlayer: {
    border: `2px solid ${colors.accent}`,
    boxShadow: '0 0 10px rgba(251, 191, 36, 0.3)',
  },
  foldedPlayer: {
    opacity: 0.5,
  },
  opponentName: {
    fontSize: '14px',
    fontWeight: 'bold',
    marginBottom: '8px',
    color: colors.primary,
  },
  opponentInfo: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
  },
  opponentCards: {
    display: 'flex',
    gap: '4px',
  },
  opponentStats: {
    fontSize: '12px',
    color: colors.textSecondary,
  },
  bet: {
    color: colors.accent,
    fontWeight: 'bold',
  },
  foldedLabel: {
    color: colors.danger,
    fontWeight: 'bold',
  },
  playerSection: {
    padding: '16px',
    backgroundColor: colors.bgDarker,
    borderRadius: '8px',
    marginBottom: '20px',
    border: `2px solid ${colors.primary}`,
  },
  playerInfo: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
  },
  playerName: {
    fontSize: '18px',
    fontWeight: 'bold',
    color: colors.primary,
  },
  playerStats: {
    fontSize: '14px',
    color: colors.textSecondary,
    textAlign: 'right' as const,
  },
  yourCards: {
    marginTop: '12px',
  },
  cardsLabel: {
    fontSize: '14px',
    color: colors.textSecondary,
    marginBottom: '8px',
  },
  cardsContainer: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'center',
  },
  message: {
    padding: '12px',
    backgroundColor: colors.bgLight,
    borderRadius: '6px',
    marginBottom: '16px',
    textAlign: 'center' as const,
    border: `1px solid ${colors.border}`,
    fontSize: '14px',
    color: colors.primary,
  },
  actions: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'center',
    flexWrap: 'wrap' as const,
  },
  actionButton: {
    ...commonStyles.button,
    padding: '12px 24px',
    fontSize: '16px',
    fontWeight: 'bold',
    minWidth: '120px',
  },
  foldButton: {
    backgroundColor: colors.buttonDanger,
  },
  checkButton: {
    backgroundColor: colors.buttonSecondary,
  },
  callButton: {
    backgroundColor: colors.buttonPrimary,
  },
  raiseButton: {
    backgroundColor: colors.buttonSuccess,
  },
  cancelButton: {
    backgroundColor: colors.buttonSecondary,
  },
  raiseInputContainer: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
    flexWrap: 'wrap' as const,
  },
  raiseInput: {
    padding: '12px',
    fontSize: '16px',
    borderRadius: '6px',
    border: `2px solid ${colors.border}`,
    backgroundColor: colors.bgDark,
    color: colors.text,
    width: '120px',
  },
  waitingMessage: {
    padding: '12px',
    fontSize: '16px',
    color: colors.accent,
    textAlign: 'center' as const,
  },
  gameOver: {
    padding: '24px',
    backgroundColor: colors.bgLight,
    borderRadius: '8px',
    textAlign: 'center' as const,
    border: `2px solid ${colors.primary}`,
  },
  gameOverTitle: {
    margin: '0 0 12px 0',
    fontSize: '24px',
    color: colors.primary,
  },
  gameOverMessage: {
    margin: '0 0 20px 0',
    fontSize: '16px',
  },
  newGameButton: {
    ...commonStyles.button,
    backgroundColor: colors.buttonSuccess,
    padding: '12px 32px',
    fontSize: '16px',
  },
};
