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
    is_jellyfish?: boolean;
}

interface PokerEventsProps {
    events: PokerEvent[];
    currentFrame: number;
}

const PokerEvents: React.FC<PokerEventsProps> = ({ events, currentFrame }) => {
    return (
        <section className="poker-events" aria-label="Recent poker activity">
            <div className="poker-events__header">
                <div className="poker-events__title-row">
                    <h2>Recent Activity</h2>
                </div>
            </div>

            {events.length === 0 ? (
                <div className="poker-events__empty-state">
                    <span className="poker-events__empty-icon">🃏</span>
                    <p>No poker games recorded yet.</p>
                    <span className="poker-events__empty-sub">Waiting for fish to gather...</span>
                </div>
            ) : (
                <div className="poker-events__list">
                    {events
                        .slice()
                        .reverse()
                        .map((event, index) => {
                            const age = currentFrame - event.frame;
                            const isTie = event.winner_id === -1;
                            const isJellyfish = event.is_jellyfish;

                            // Calculate opacity based on age (fade out after 180 frames)
                            const fading = Math.max(0.4, 1 - Math.max(0, age - 120) / 60);

                            // Parse the message to extract key info if possible, or use raw message
                            // Format: "Fish #X beats Fish #Y with [Hand]! (+Z energy)"
                            let content = null;

                            if (isTie) {
                                content = (
                                    <div className="event-content">
                                        <div className="event-header">
                                            <span className="event-badge tie">TIE</span>
                                            <span className="event-hand">{event.winner_hand}</span>
                                        </div>
                                        <div className="event-details">
                                            {event.message.split(' - ')[0]}
                                        </div>
                                    </div>
                                );
                            } else {
                                const winnerName = isJellyfish && event.winner_id === -2 ? "Jellyfish" : `Fish #${event.winner_id}`;
                                const loserName = isJellyfish && event.loser_id === -2 ? "Jellyfish" : `Fish #${event.loser_id}`;

                                content = (
                                    <div className="event-content">
                                        <div className="event-header">
                                            <span className={`event-badge ${isJellyfish ? 'jellyfish' : 'win'}`}>
                                                {isJellyfish && event.winner_id === -2 ? 'JELLY' : 'WIN'}
                                            </span>
                                            <span className="event-hand">{event.winner_hand}</span>
                                            <span className="event-energy">+{event.energy_transferred.toFixed(1)}⚡</span>
                                        </div>
                                        <div className="event-details">
                                            <span className="winner-name">{winnerName}</span>
                                            <span className="vs-text">def.</span>
                                            <span className="loser-name">{loserName}</span>
                                        </div>
                                    </div>
                                );
                            }

                            return (
                                <div
                                    key={`${event.frame}-${index}`}
                                    className={`poker-events__item ${isTie ? 'tie' : ''} ${isJellyfish ? 'jellyfish' : ''}`}
                                    style={{ opacity: fading }}
                                >
                                    {content}
                                </div>
                            );
                        })}
                </div>
            )}
        </section>
    );
};

export default PokerEvents;
