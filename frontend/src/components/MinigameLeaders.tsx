import React from 'react';
import type { PokerLeaderboardEntry, SoccerFishLeaderEntry } from '../types/simulation';

/**
 * Compact standings panels shown under the poker table and the soccer field.
 *
 * These are glanceable top-5 lists of the tank's best competitors — no event
 * history, no per-hand ledger. Winning shows up here as wins, goals, and net
 * energy earned.
 */

const TOP_N = 5;

const rowStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'baseline',
    gap: '8px',
    padding: '6px 10px',
    borderRadius: '8px',
    backgroundColor: '#0f172a',
    border: '1px solid #1e293b',
    fontSize: '13px',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
};

const emptyStyle: React.CSSProperties = {
    marginTop: '8px',
    padding: '12px',
    borderRadius: '8px',
    backgroundColor: '#0f172a',
    border: '1px dashed #334155',
    color: '#94a3b8',
    fontSize: '13px',
    textAlign: 'center',
};

function rankColor(rank: number): string {
    if (rank === 1) return '#facc15';
    if (rank === 2) return '#cbd5e1';
    if (rank === 3) return '#d97706';
    return '#64748b';
}

function energyText(value: number): { text: string; color: string } {
    return {
        text: `${value >= 0 ? '+' : ''}${Math.round(value)}⚡`,
        color: value >= 0 ? '#4ade80' : '#f87171',
    };
}

function LeadersPanel({
    title,
    rows,
    emptyMessage,
}: {
    title: string;
    rows: React.ReactNode[];
    emptyMessage: string;
}) {
    return (
        <section aria-label={title} style={{ marginTop: '14px' }}>
            <h3 style={{ margin: 0, fontSize: '14px', color: '#93c5fd' }}>{title}</h3>
            {rows.length === 0 ? (
                <div style={emptyStyle}>{emptyMessage}</div>
            ) : (
                <div style={{ marginTop: '8px', display: 'grid', gap: '4px' }}>{rows}</div>
            )}
        </section>
    );
}

function LeaderRow({
    rank,
    fishId,
    stats,
    energy,
}: {
    rank: number;
    fishId: number;
    stats: string;
    energy: number;
}) {
    const e = energyText(energy);
    return (
        <div style={rowStyle}>
            <span style={{ color: rankColor(rank), fontWeight: 700, minWidth: '18px' }}>{rank}.</span>
            <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{`Fish #${fishId}`}</span>
            <span style={{ color: '#94a3b8' }}>{stats}</span>
            <span style={{ color: e.color, marginLeft: 'auto' }}>{e.text}</span>
        </div>
    );
}

/** Top poker players in the tank, shown under the poker table. */
export function PokerLeaders({ leaders }: { leaders: PokerLeaderboardEntry[] }) {
    const rows = leaders
        .slice(0, TOP_N)
        .map((entry, index) => {
            const tankName = entry.tank_name && entry.tank_name !== 'Unknown Tank'
                ? entry.tank_name
                : entry.tank_id && entry.tank_id !== 'unknown'
                    ? `Tank ${entry.tank_id}`
                    : 'Origin not recorded';
            const offspring = entry.offspring_count !== undefined ? ` — ${entry.offspring_count} offspring` : '';
            return (
                <LeaderRow
                    key={entry.fish_id}
                    rank={index + 1}
                    fishId={entry.fish_id}
                    stats={` · ${tankName} — ${entry.wins} wins · ${entry.total_games} hands · best: ${entry.best_hand || '—'}${offspring}`}
                    energy={entry.net_energy}
                />
            );
        });

    return (
        <LeadersPanel
            title="Poker Leaders"
            rows={rows}
            emptyMessage="No poker games yet. The tank's best players will appear here."
        />
    );
}

/** Top soccer players in the tank, shown under the field. */
export function SoccerLeaders({ leaders }: { leaders: SoccerFishLeaderEntry[] }) {
    const rows = leaders
        .slice(0, TOP_N)
        .map((entry, index) => {
            const roundedEnergy = Math.round(entry.net_energy);
            const energyText = `${roundedEnergy >= 0 ? '+' : ''}${roundedEnergy} net energy`;
            const tankName = entry.tank_name && entry.tank_name !== 'Unknown Tank'
                ? entry.tank_name
                : entry.tank_id && entry.tank_id !== 'unknown'
                    ? `Tank ${entry.tank_id}`
                    : 'Origin not recorded';
            const offspring = entry.offspring_count !== undefined ? ` — ${entry.offspring_count} offspring` : '';
            const stats = ` — ${entry.goals} goals — ${entry.assists} assists — ${energyText} — ${entry.wins} wins${offspring}`;
            return (
                <div key={entry.fish_id} style={rowStyle}>
                    <span style={{ color: rankColor(index + 1), fontWeight: 700, minWidth: '18px' }}>{index + 1}.</span>
                    <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{`Fish #${entry.fish_id}`}</span>
                    <span style={{ color: '#94a3b8' }}>{` · ${tankName}${stats}`}</span>
                </div>
            );
        });

    return (
        <LeadersPanel
            title="Soccer Leaders"
            rows={rows}
            emptyMessage="No soccer matches yet. The tank's best players will appear here."
        />
    );
}
