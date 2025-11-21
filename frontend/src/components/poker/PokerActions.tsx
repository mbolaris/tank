/**
 * Poker action buttons component
 */

import { useState } from 'react';
import styles from './PokerActions.module.css';

interface PokerActionsProps {
  isYourTurn: boolean;
  callAmount: number;
  minRaise: number;
  maxRaise: number;
  loading: boolean;
  currentPlayer: string;
  onFold: () => void;
  onCheck: () => void;
  onCall: () => void;
  onRaise: (amount: number) => void;
}

export function PokerActions({
  isYourTurn,
  callAmount,
  minRaise,
  maxRaise,
  loading,
  currentPlayer,
  onFold,
  onCheck,
  onCall,
  onRaise,
}: PokerActionsProps) {
  const [raiseAmount, setRaiseAmount] = useState<number>(minRaise);
  const [showRaiseInput, setShowRaiseInput] = useState(false);

  const handleRaise = () => {
    if (raiseAmount >= minRaise) {
      onRaise(raiseAmount);
      setShowRaiseInput(false);
      setRaiseAmount(minRaise);
    }
  };

  const handleShowRaise = () => {
    setShowRaiseInput(true);
    setRaiseAmount(minRaise);
  };

  const actionsClass = `${styles.actions} ${isYourTurn ? styles.actionsActive : ''}`;

  if (!isYourTurn) {
    return (
      <div className={styles.actions}>
        <div className={styles.waitingMessage}>
          Waiting for <strong>{currentPlayer}</strong><span className={styles.waitingDots}>...</span>
        </div>
      </div>
    );
  }

  if (showRaiseInput) {
    return (
      <div className={actionsClass}>
        <div className={styles.raiseInputContainer}>
          <input
            type="number"
            value={raiseAmount}
            onChange={(e) => setRaiseAmount(Number(e.target.value))}
            min={minRaise}
            max={maxRaise}
            step={1}
            className={styles.raiseInput}
          />
          <button
            onClick={handleRaise}
            disabled={loading || raiseAmount < minRaise}
            className={styles.confirmButton}
          >
            Bet {raiseAmount.toFixed(0)}
          </button>
          <button
            onClick={() => setShowRaiseInput(false)}
            className={styles.cancelButton}
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={actionsClass}>
      <button
        onClick={onFold}
        disabled={loading}
        className={`${styles.actionButton} ${styles.foldButton}`}
      >
        Fold
      </button>

      {callAmount === 0 ? (
        <button
          onClick={onCheck}
          disabled={loading}
          className={`${styles.actionButton} ${styles.checkButton}`}
        >
          Check
        </button>
      ) : (
        <button
          onClick={onCall}
          disabled={loading}
          className={`${styles.actionButton} ${styles.callButton}`}
        >
          Call {callAmount.toFixed(0)}
        </button>
      )}

      <button
        onClick={handleShowRaise}
        disabled={loading}
        className={`${styles.actionButton} ${styles.raiseButton}`}
      >
        {callAmount > 0 ? 'Raise' : 'Bet'}
      </button>
    </div>
  );
}
