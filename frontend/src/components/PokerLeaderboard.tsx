import React from 'react';
import type { PokerLeaderboardEntry } from '../types/simulation';
import styles from './PokerLeaderboard.module.css';

interface PokerLeaderboardProps {
  leaderboard: PokerLeaderboardEntry[];
}

export const PokerLeaderboard: React.FC<PokerLeaderboardProps> = ({ leaderboard }) => {
  // Don't render anything if there's no data - prevents layout shift
  if (!leaderboard || leaderboard.length === 0) {
    return null;
  }

  return (
    <div className={styles.pokerLeaderboard}>
      <h3>🏆 Poker Leaderboard - Top Players</h3>
      <div className={styles.leaderboardTable}>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Fish</th>
              <th>Games</th>
              <th>Win%</th>
              <th>Trend</th>
              <th>Net Energy</th>
              <th>Streak</th>
              <th>Best Hand</th>
            </tr>
          </thead>
          <tbody>
            {leaderboard.map((entry) => {
              const rankClass = entry.rank === 1 ? styles.rank1 : entry.rank === 2 ? styles.rank2 : entry.rank === 3 ? styles.rank3 : '';
              return (
                <tr key={entry.fish_id} className={rankClass}>
                  <td className={styles.rankCell}>
                    {entry.rank === 1 && '🥇'}
                    {entry.rank === 2 && '🥈'}
                    {entry.rank === 3 && '🥉'}
                    {entry.rank > 3 && entry.rank}
                  </td>
                  <td className={styles.fishCell}>
                    <div className={styles.fishInfo}>
                      <span className={styles.fishId}>#{entry.fish_id}</span>
                      <span className={styles.fishGen}>Gen {entry.generation}</span>
                    </div>
                  </td>
                  <td>
                    <div className={styles.gamesInfo}>
                      <span className={styles.totalGames}>{entry.total_games}</span>
                      <span className={styles.winLoss}>
                        ({entry.wins}W-{entry.losses}L)
                      </span>
                    </div>
                  </td>
                  <td className={entry.win_rate >= 50 ? styles.positive : styles.neutral}>
                    {entry.win_rate.toFixed(1)}%
                  </td>
                  <td className={styles.trendCell}>
                    {getTrendIndicator(entry.skill_trend, entry.recent_win_rate)}
                  </td>
                  <td className={entry.net_energy >= 0 ? styles.positive : styles.negative}>
                    {entry.net_energy >= 0 ? '+' : ''}
                    {entry.net_energy.toFixed(1)}
                  </td>
                  <td>
                    <span className={entry.current_streak > 0 ? styles.positive : entry.current_streak < 0 ? styles.negative : ''}>
                      {entry.current_streak > 0 ? '🔥' : entry.current_streak < 0 ? '❄️' : '➖'}
                      {Math.abs(entry.current_streak)}
                    </span>
                  </td>
                  <td className={styles.bestHand}>
                    {getHandEmoji(entry.best_hand_rank)} {entry.best_hand}
                  </td>
                </tr>
              );
            })}
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

// Helper function to get trend indicator
function getTrendIndicator(trend: string, recentWinRate: number): React.ReactNode {
  if (trend === 'improving') {
    return (
      <span className={styles.improving} title={`Recent: ${recentWinRate.toFixed(1)}%`}>
        📈 ↗
      </span>
    );
  } else if (trend === 'declining') {
    return (
      <span className={styles.declining} title={`Recent: ${recentWinRate.toFixed(1)}%`}>
        📉 ↘
      </span>
    );
  } else {
    return (
      <span className={styles.stable} title={`Recent: ${recentWinRate.toFixed(1)}%`}>
        ➡ ─
      </span>
    );
  }
}
