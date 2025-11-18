import React from 'react';
import { PokerLeaderboardEntry } from '../types/simulation';

interface PokerLeaderboardProps {
  leaderboard: PokerLeaderboardEntry[];
}

export const PokerLeaderboard: React.FC<PokerLeaderboardProps> = ({ leaderboard }) => {
  if (!leaderboard || leaderboard.length === 0) {
    return (
      <div className="poker-leaderboard">
        <h3>🏆 Poker Leaderboard</h3>
        <p style={{ fontSize: '12px', color: '#888', padding: '10px' }}>
          No poker games yet. Fish will appear here after playing poker!
        </p>
      </div>
    );
  }

  return (
    <div className="poker-leaderboard">
      <h3>🏆 Poker Leaderboard - Top Players</h3>
      <div className="leaderboard-table">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Fish</th>
              <th>Games</th>
              <th>Win%</th>
              <th>Net Energy</th>
              <th>Streak</th>
              <th>Best Hand</th>
            </tr>
          </thead>
          <tbody>
            {leaderboard.map((entry) => (
              <tr key={entry.fish_id} className={entry.rank <= 3 ? `rank-${entry.rank}` : ''}>
                <td className="rank-cell">
                  {entry.rank === 1 && '🥇'}
                  {entry.rank === 2 && '🥈'}
                  {entry.rank === 3 && '🥉'}
                  {entry.rank > 3 && entry.rank}
                </td>
                <td className="fish-cell">
                  <div className="fish-info">
                    <span className="fish-id">#{entry.fish_id}</span>
                    <span className="fish-gen">Gen {entry.generation}</span>
                  </div>
                </td>
                <td>
                  <div className="games-info">
                    <span className="total-games">{entry.total_games}</span>
                    <span className="win-loss">
                      ({entry.wins}W-{entry.losses}L)
                    </span>
                  </div>
                </td>
                <td className={entry.win_rate >= 50 ? 'positive' : 'neutral'}>
                  {entry.win_rate.toFixed(1)}%
                </td>
                <td className={entry.net_energy >= 0 ? 'positive' : 'negative'}>
                  {entry.net_energy >= 0 ? '+' : ''}
                  {entry.net_energy.toFixed(1)}
                </td>
                <td>
                  <span className={entry.current_streak > 0 ? 'positive' : entry.current_streak < 0 ? 'negative' : ''}>
                    {entry.current_streak > 0 ? '🔥' : entry.current_streak < 0 ? '❄️' : '➖'}
                    {Math.abs(entry.current_streak)}
                  </span>
                </td>
                <td className="best-hand">
                  {getHandEmoji(entry.best_hand_rank)} {entry.best_hand}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <style jsx>{`
        .poker-leaderboard {
          background: rgba(0, 0, 0, 0.8);
          border: 2px solid #4a9eff;
          border-radius: 8px;
          padding: 15px;
          color: white;
          font-family: 'Courier New', monospace;
          max-width: 800px;
          margin: 10px;
        }

        h3 {
          margin: 0 0 15px 0;
          font-size: 18px;
          color: #ffd700;
          text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
        }

        .leaderboard-table {
          overflow-x: auto;
        }

        table {
          width: 100%;
          border-collapse: collapse;
          font-size: 13px;
        }

        th {
          background: rgba(74, 158, 255, 0.3);
          padding: 8px 6px;
          text-align: left;
          font-weight: bold;
          border-bottom: 2px solid #4a9eff;
          font-size: 12px;
          text-transform: uppercase;
        }

        td {
          padding: 8px 6px;
          border-bottom: 1px solid rgba(74, 158, 255, 0.2);
        }

        tr:hover {
          background: rgba(74, 158, 255, 0.1);
        }

        .rank-1 {
          background: rgba(255, 215, 0, 0.15);
        }

        .rank-2 {
          background: rgba(192, 192, 192, 0.15);
        }

        .rank-3 {
          background: rgba(205, 127, 50, 0.15);
        }

        .rank-cell {
          font-size: 18px;
          text-align: center;
          width: 40px;
        }

        .fish-cell {
          min-width: 100px;
        }

        .fish-info {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .fish-id {
          font-weight: bold;
          color: #4a9eff;
        }

        .fish-gen {
          font-size: 10px;
          color: #888;
        }

        .games-info {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .total-games {
          font-weight: bold;
        }

        .win-loss {
          font-size: 10px;
          color: #aaa;
        }

        .positive {
          color: #4ade80;
          font-weight: bold;
        }

        .negative {
          color: #f87171;
          font-weight: bold;
        }

        .neutral {
          color: #fbbf24;
        }

        .best-hand {
          font-size: 11px;
          color: #a78bfa;
        }

        @media (max-width: 768px) {
          table {
            font-size: 11px;
          }

          th, td {
            padding: 6px 4px;
          }

          .fish-gen, .win-loss {
            display: none;
          }
        }
      `}</style>
    </div>
  );
};

// Helper function to get emoji for hand rank
function getHandEmoji(rank: number): string {
  const emojis = [
    '🃏', // High Card
    '👥', // Pair
    '👥👥', // Two Pair
    '🎰', // Three of a Kind
    '📏', // Straight
    '💎', // Flush
    '🏠', // Full House
    '🎲', // Four of a Kind
    '⚡', // Straight Flush
    '👑', // Royal Flush
  ];
  return emojis[rank] || '🃏';
}
