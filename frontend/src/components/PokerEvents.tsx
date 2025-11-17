import React from 'react';
import './PokerEvents.css';

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
  return (
    <section className="poker-events" aria-label="Recent poker activity">
      <div className="poker-events__header">
        <h2>Poker Activity</h2>
        <span>Latest clashes between fish</span>
      </div>
      {events.length === 0 ? (
        <p className="poker-events__empty">No poker activity yet.</p>
      ) : (
        <div className="poker-events__list">
          {events
            .slice()
            .reverse()
            .map((event, index) => {
              const age = currentFrame - event.frame;
              const isTie = event.winner_id === -1;
              const fading = Math.max(0.35, 1 - Math.max(0, age - 90) / 90);

              return (
                <div
                  key={`${event.frame}-${index}`}
                  className={`poker-events__item ${isTie ? 'tie' : ''}`}
                  style={{ opacity: fading }}
                >
                  {event.message}
                </div>
              );
            })}
        </div>
      )}
    </section>
  );
};

export default PokerEvents;
