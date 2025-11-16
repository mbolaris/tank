import React from 'react';

interface PokerEvent {
  frame: number;
  winner_id: number;
  loser_id: number;
  winner_hand: string;
  loser_hand: string;
  energy_transferred: number;
  message: string;
}

interface PokerEventsProps {
  events: PokerEvent[];
  currentFrame: number;
}

const PokerEvents: React.FC<PokerEventsProps> = ({ events, currentFrame }) => {
  if (events.length === 0) {
    return null;
  }

  const styles = {
    container: {
      position: 'fixed' as const,
      bottom: '20px',
      right: '20px',
      width: '400px',
      maxHeight: '250px',
      overflowY: 'auto' as const,
      pointerEvents: 'none' as const,
      zIndex: 1000,
    },
    event: (age: number) => ({
      backgroundColor: 'rgba(20, 20, 40, 0.9)',
      padding: '8px 12px',
      marginBottom: '5px',
      borderRadius: '4px',
      fontSize: '13px',
      color: age > 120 ? `rgba(200, 255, 150, ${Math.max(0.3, 1 - (age - 120) / 60)})` : 'rgb(200, 255, 150)',
      transition: 'opacity 0.5s',
      border: '1px solid rgba(100, 255, 100, 0.3)',
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)',
    }),
    tieEvent: (age: number) => ({
      backgroundColor: 'rgba(20, 20, 40, 0.9)',
      padding: '8px 12px',
      marginBottom: '5px',
      borderRadius: '4px',
      fontSize: '13px',
      color: age > 120 ? `rgba(255, 255, 100, ${Math.max(0.3, 1 - (age - 120) / 60)})` : 'rgb(255, 255, 100)',
      transition: 'opacity 0.5s',
      border: '1px solid rgba(255, 255, 100, 0.3)',
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)',
    }),
  };

  return (
    <div style={styles.container}>
      {events.slice().reverse().map((event, index) => {
        const age = currentFrame - event.frame;
        const isTie = event.winner_id === -1;
        return (
          <div
            key={`${event.frame}-${index}`}
            style={isTie ? styles.tieEvent(age) : styles.event(age)}
          >
            {event.message}
          </div>
        );
      })}
    </div>
  );
};

export default PokerEvents;
