import React, { useEffect, useState, useCallback } from 'react';
import styles from './SolutionLeaderboard.module.css';

interface SolutionEntry {
    rank: number;
    solution_id: string;
    name: string;
    author: string;
    submitted_at: string;
    elo_rating: number;
    skill_tier: string;
    bb_per_100: number;
}

interface SolutionsResponse {
    count: number;
    solutions: SolutionEntry[];
}

interface SolutionLeaderboardProps {
    tankId?: string;
    onCapture?: () => void;
}

export const SolutionLeaderboard: React.FC<SolutionLeaderboardProps> = ({ tankId, onCapture }) => {
    const [solutions, setSolutions] = useState<SolutionEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [capturing, setCapturing] = useState(false);
    const [captureMessage, setCaptureMessage] = useState<string | null>(null);

    const fetchSolutions = useCallback(async () => {
        try {
            const response = await fetch('/api/solutions');
            if (!response.ok) {
                throw new Error(`Failed to fetch solutions: ${response.statusText}`);
            }
            const data: SolutionsResponse = await response.json();
            setSolutions(data.solutions || []);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchSolutions();
        // Refresh every 60 seconds
        const interval = setInterval(fetchSolutions, 60000);
        return () => clearInterval(interval);
    }, [fetchSolutions]);

    const handleCapture = async () => {
        if (!tankId) {
            setCaptureMessage('No tank selected for capture');
            return;
        }

        setCapturing(true);
        setCaptureMessage(null);

        try {
            const response = await fetch(`/api/solutions/capture/${tankId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    evaluate: true,
                }),
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Capture failed');
            }

            const result = await response.json();
            setCaptureMessage(`Captured solution: ${result.solution_id}`);

            // Refresh the list
            await fetchSolutions();

            if (onCapture) {
                onCapture();
            }
        } catch (err) {
            setCaptureMessage(err instanceof Error ? err.message : 'Capture failed');
        } finally {
            setCapturing(false);
        }
    };

    const getSkillTierClass = (tier: string): string => {
        const tierMap: Record<string, string> = {
            master: styles.tierMaster,
            expert: styles.tierExpert,
            advanced: styles.tierAdvanced,
            intermediate: styles.tierIntermediate,
            beginner: styles.tierBeginner,
            novice: styles.tierNovice,
            failing: styles.tierFailing,
        };
        return tierMap[tier] || '';
    };

    const getSkillTierEmoji = (tier: string): string => {
        const emojiMap: Record<string, string> = {
            master: '🏆',
            expert: '⭐',
            advanced: '🎯',
            intermediate: '📊',
            beginner: '📈',
            novice: '🌱',
            failing: '⚠️',
        };
        return emojiMap[tier] || '❓';
    };

    const formatDate = (isoDate: string): string => {
        try {
            const date = new Date(isoDate);
            return date.toLocaleDateString();
        } catch {
            return isoDate;
        }
    };

    if (loading) {
        return (
            <div className={styles.solutionLeaderboard}>
                <h3>Solution Leaderboard</h3>
                <div className={styles.loading}>Loading solutions...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className={styles.solutionLeaderboard}>
                <h3>Solution Leaderboard</h3>
                <div className={styles.error}>Error: {error}</div>
            </div>
        );
    }

    return (
        <div className={styles.solutionLeaderboard}>
            <div className={styles.header}>
                <h3>Solution Leaderboard</h3>
                {tankId && (
                    <button
                        className={styles.captureButton}
                        onClick={handleCapture}
                        disabled={capturing}
                    >
                        {capturing ? 'Capturing...' : '📸 Capture Best'}
                    </button>
                )}
            </div>

            {captureMessage && (
                <div className={styles.captureMessage}>{captureMessage}</div>
            )}

            {solutions.length === 0 ? (
                <div className={styles.empty}>
                    <p>No solutions submitted yet.</p>
                    <p>Capture the best performing fish from your simulation to create a solution!</p>
                </div>
            ) : (
                <div className={styles.leaderboardTable}>
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Solution</th>
                                <th>Author</th>
                                <th>Elo</th>
                                <th>Tier</th>
                                <th>bb/100</th>
                                <th>Date</th>
                            </tr>
                        </thead>
                        <tbody>
                            {solutions.map((entry) => {
                                const rankClass =
                                    entry.rank === 1
                                        ? styles.rank1
                                        : entry.rank === 2
                                          ? styles.rank2
                                          : entry.rank === 3
                                            ? styles.rank3
                                            : '';

                                return (
                                    <tr key={entry.solution_id} className={rankClass}>
                                        <td className={styles.rankCell}>
                                            {entry.rank === 1 && '🥇'}
                                            {entry.rank === 2 && '🥈'}
                                            {entry.rank === 3 && '🥉'}
                                            {entry.rank > 3 && entry.rank}
                                        </td>
                                        <td className={styles.nameCell}>
                                            <div className={styles.solutionInfo}>
                                                <span className={styles.solutionName}>{entry.name}</span>
                                                <span className={styles.solutionId}>
                                                    {entry.solution_id.substring(0, 8)}...
                                                </span>
                                            </div>
                                        </td>
                                        <td className={styles.authorCell}>{entry.author}</td>
                                        <td className={styles.eloCell}>{entry.elo_rating.toFixed(0)}</td>
                                        <td className={`${styles.tierCell} ${getSkillTierClass(entry.skill_tier)}`}>
                                            {getSkillTierEmoji(entry.skill_tier)} {entry.skill_tier}
                                        </td>
                                        <td
                                            className={
                                                entry.bb_per_100 >= 0 ? styles.positive : styles.negative
                                            }
                                        >
                                            {entry.bb_per_100 >= 0 ? '+' : ''}
                                            {entry.bb_per_100.toFixed(2)}
                                        </td>
                                        <td className={styles.dateCell}>
                                            {formatDate(entry.submitted_at)}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            <div className={styles.footer}>
                <span className={styles.count}>{solutions.length} solutions submitted</span>
                <button className={styles.refreshButton} onClick={fetchSolutions}>
                    🔄 Refresh
                </button>
            </div>
        </div>
    );
};

export default SolutionLeaderboard;
