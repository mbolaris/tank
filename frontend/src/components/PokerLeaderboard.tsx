import React from 'react';
import type { PokerLeaderboardEntry } from '../types/simulation';
import './PokerLeaderboard.css';

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
