import React from 'react';
import type { SimulationUpdate } from '../types/simulation';
import { PokerLeaderboard } from './PokerLeaderboard';
import PokerEvents from './PokerEvents';
import { AutoEvaluateDisplay } from './AutoEvaluateDisplay';
import { EvolutionBenchmarkDisplay } from './EvolutionBenchmarkDisplay';
import './PokerDashboard.css';

interface PokerDashboardProps {
    state: SimulationUpdate | null;
}

export const PokerDashboard: React.FC<PokerDashboardProps> = ({ state }) => {
    if (!state) return null;

    const { stats, poker_events, poker_leaderboard, auto_evaluation } = state;
    const pokerStats = stats?.poker_stats;

    // Calculate Games Per Minute (Activity Metric)
    // Assuming 30 FPS for frame count calculation if time isn't available directly
    // But we have total games. We can try to estimate rate if we had previous state, 
    // but for now let's use total games / (frames / 30 / 60)
    const minutesElapsed = state.frame / 30 / 60;
    const gamesPerMinute = minutesElapsed > 0 && pokerStats
        ? (pokerStats.total_games / minutesElapsed).toFixed(1)
        : "0.0";

    return (
        <div className="poker-dashboard">
            {/* Header */}
            <div className="dashboard-header">
                <div className="header-title">
                    <h2>Poker Ecosystem</h2>
                    <div className="header-subtitle">Real-time economy & evolution tracking</div>
                </div>
                <div className="live-indicator">
                    <div className="pulse-dot"></div>
                    LIVE ACTIVITY
                </div>
            </div>

            {/* Key Metrics Row - "Are they playing?" */}
            <div className="metrics-grid">
                <div className="metric-card">
                    <span className="metric-label">Activity Rate</span>
                    <span className="metric-value highlight">{gamesPerMinute}</span>
                    <span className="metric-subtext">Games / Minute</span>
                </div>
                <div className="metric-card">
                    <span className="metric-label">Total Games</span>
                    <span className="metric-value">{pokerStats?.total_games.toLocaleString() ?? 0}</span>
                    <span className="metric-subtext">Lifetime Hands Dealt</span>
                </div>
                <div className="metric-card">
                    <span className="metric-label">Economy Volume</span>
                    <span className="metric-value">{Math.round(pokerStats?.total_energy_won ?? 0).toLocaleString()}⚡</span>
                    <span className="metric-subtext">Total Energy Exchanged</span>
                </div>
                <div className="metric-card">
                    <span className="metric-label">Avg Win Rate</span>
                    <span className="metric-value">{pokerStats?.win_rate_pct ?? "0%"}</span>
                    <span className="metric-subtext">Population Skill Level</span>
                </div>
            </div>

            {/* Improvement Section - "Are they improving?" */}
            {auto_evaluation && (
                <div className="section-container">
                    <div className="section-title">
                        <span>📈</span> Evolution Progress
                    </div>
                    <AutoEvaluateDisplay stats={auto_evaluation} loading={false} />
                </div>
            )}

            {/* Scientific Benchmark Section - bb/100 tracking over generations */}
            <div className="section-container">
                <div className="section-title">
                    <span>🎯</span> Poker Skill Benchmark (bb/100)
                </div>
                <EvolutionBenchmarkDisplay />
            </div>

            {/* Detailed Split View */}
            <div className="dashboard-content">
                {/* Left: Leaderboard */}
                <div className="section-container">
                    <PokerLeaderboard leaderboard={poker_leaderboard ?? []} />
                </div>

                {/* Right: Activity Feed */}
                <div className="section-container">
                    <PokerEvents
                        events={poker_events ?? []}
                        currentFrame={state.frame}
                    />
                </div>
            </div>
        </div>
    );
};
