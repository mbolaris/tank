/**
 * Poker action buttons component
 */

import { useState } from 'react';
import { Button } from '../ui';
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

  if (!isYourTurn) {
    return (
      <div className={styles.actions}>
        <div className={styles.waitingMessage}>
          Waiting for {currentPlayer}...
        </div>
      </div>
    );
  }

  if (showRaiseInput) {
    return (
      <div className={styles.actions}>
        <div className={styles.raiseInputContainer}>
          <input
            type="number"
            value={raiseAmount}
            onChange={(e) => setRaiseAmount(Number(e.target.value))}
            min={minRaise}
            max={maxRaise}
            step={minRaise}
            className={styles.raiseInput}
          />
          <Button
            onClick={handleRaise}
            disabled={loading || raiseAmount < minRaise}
            variant="success"
            className={styles.actionButton}
          >
            Confirm {raiseAmount.toFixed(1)}
          </Button>
          <Button
            onClick={() => setShowRaiseInput(false)}
            variant="secondary"
            className={styles.actionButton}
          >
            Cancel
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.actions}>
      <Button
        onClick={onFold}
        disabled={loading}
        variant="danger"
        className={styles.actionButton}
      >
        Fold
      </Button>

      {callAmount === 0 ? (
        <Button
          onClick={onCheck}
          disabled={loading}
          variant="secondary"
          className={styles.actionButton}
        >
          Check
        </Button>
      ) : (
        <Button
          onClick={onCall}
          disabled={loading}
          variant="primary"
          className={styles.actionButton}
        >
          Call {callAmount.toFixed(1)}
        </Button>
      )}

      <Button
        onClick={handleShowRaise}
        disabled={loading}
        variant="success"
        className={styles.actionButton}
      >
        {callAmount > 0 ? 'Raise' : 'Bet'}
      </Button>
    </div>
  );
}
