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
    is_plant?: boolean;
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
                            const isPlant = event.is_plant;

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
                                let winnerName = `Fish #${event.winner_id}`;
                                let loserName = `Fish #${event.loser_id}`;

                                if (isJellyfish) {
                                    if (event.winner_id === -2) winnerName = "Jellyfish";
                                    if (event.loser_id === -2) loserName = "Jellyfish";
                                } else if (isPlant) {
                                    if (event.winner_id === -3) winnerName = `Plant #${Math.abs(event.winner_id)}`; // Plant IDs are positive in simulation but -3 here is just a flag check really
                                    if (event.loser_id === -3) loserName = `Plant #${Math.abs(event.loser_id)}`;

                                    // Actually, for plants we passed -3 as ID in backend? 
                                    // No, we passed -3 as ID. But we also have plant_id in message.
                                    // Let's just use the ID passed.
                                    if (event.winner_id === -3) winnerName = "Plant";
                                    if (event.loser_id === -3) loserName = "Plant";
                                }

                                content = (
                                    <div className="event-content">
                                        <div className="event-header">
                                            <span className={`event-badge ${isJellyfish ? 'jellyfish' : isPlant ? 'plant' : 'win'}`}>
                                                {isJellyfish ? 'JELLY' : isPlant ? 'PLANT' : 'WIN'}
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
                                    className={`poker-events__item ${isTie ? 'tie' : ''} ${isJellyfish ? 'jellyfish' : ''} ${isPlant ? 'plant' : ''}`}
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
