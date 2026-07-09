import { useCallback, useEffect, useState } from 'react';
import { colors } from '../styles/theme';
import type { ForagingGymResult } from '../types/skill';

const SEEDS = [42, 7, 123] as const;

function percent(value: number): string {
    return `${(value * 100).toFixed(1)}%`;
}

function energy(value: number): string {
    return Math.round(value).toLocaleString();
}

export function ForagingGymResultCard({ result }: { result: ForagingGymResult }) {
    const { composable_energy_ratio, random_walk_energy_ratio } = result.score_breakdown;
    const { composable, random_walk, oracle, oracle_energy } = result.metadata;
    const beatFloor = composable_energy_ratio > random_walk_energy_ratio;

    return (
        <div style={styles.result}>
            <div style={styles.scoreRow}>
                <div>
                    <div style={styles.label}>COMPOSABLE FORAGING</div>
                    <div style={styles.score}>{percent(composable_energy_ratio)}</div>
                    <div style={styles.caption}>
                        {energy(composable.energy_collected)} / {energy(oracle_energy)} energy · {composable.food_collected}/
                        {oracle.food_collected} food
                    </div>
                </div>
                <div style={{ ...styles.floorBadge, color: beatFloor ? colors.success : colors.danger }}>
                    {beatFloor ? 'ABOVE RANDOM FLOOR' : 'BELOW RANDOM FLOOR'}
                </div>
            </div>

            <div style={styles.track} aria-label="Composable energy captured relative to oracle ceiling">
                <div
                    style={{
                        ...styles.fill,
                        width: `${Math.max(0, Math.min(100, composable_energy_ratio * 100))}%`,
                    }}
                />
            </div>

            <div style={styles.referenceGrid}>
                <div style={styles.reference}>
                    <span style={styles.referenceName}>Random walk</span>
                    <strong>{percent(random_walk_energy_ratio)}</strong>
                    <span style={styles.referenceDetail}>{random_walk.food_collected} food</span>
                </div>
                <div style={styles.reference}>
                    <span style={styles.referenceName}>Oracle ceiling</span>
                    <strong>{percent(result.score_breakdown.oracle_energy_ratio)}</strong>
                    <span style={styles.referenceDetail}>{oracle.food_collected} food</span>
                </div>
            </div>
        </div>
    );
}

export function ForagingGymPanel() {
    const [seed, setSeed] = useState<number>(42);
    const [result, setResult] = useState<ForagingGymResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const evaluate = useCallback(async (selectedSeed: number) => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch(`/api/skill/foraging-gym?seed=${selectedSeed}`);
            if (!response.ok) throw new Error(`Evaluation failed (${response.status})`);
            const data: ForagingGymResult = await response.json();
            setResult(data);
        } catch (cause) {
            setError(cause instanceof Error ? cause.message : 'Evaluation unavailable');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        evaluate(seed);
    }, [evaluate, seed]);

    return (
        <section style={styles.panel} aria-label="Foraging gym evaluator">
            <div style={styles.header}>
                <div>
                    <div style={styles.title}>Foraging Gym</div>
                    <div style={styles.description}>
                        One fish, scripted food, no ecosystem confounders. 100% means every available calorie.
                    </div>
                </div>
                <div style={styles.controls}>
                    <label style={styles.seedLabel}>
                        Seed
                        <select value={seed} onChange={event => setSeed(Number(event.target.value))} style={styles.select}>
                            {SEEDS.map(option => <option key={option} value={option}>{option}</option>)}
                        </select>
                    </label>
                    <button type="button" onClick={() => evaluate(seed)} disabled={loading} style={styles.button}>
                        {loading ? 'Evaluating…' : 'Run gym'}
                    </button>
                </div>
            </div>

            {error ? <div style={styles.error}>{error}</div> : result ? <ForagingGymResultCard result={result} /> : <div style={styles.loading}>Evaluating current behavior…</div>}
        </section>
    );
}

const styles = {
    panel: {
        backgroundColor: 'rgba(15, 23, 42, 0.52)',
        border: `1px solid ${colors.border}`,
        borderRadius: '10px',
        padding: '14px',
        display: 'flex',
        flexDirection: 'column' as const,
        gap: '12px',
    },
    header: { display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' as const },
    title: { color: colors.primary, fontWeight: 700, fontSize: '15px' },
    description: { color: colors.textSecondary, fontSize: '11px', marginTop: '3px', maxWidth: '460px' },
    controls: { display: 'flex', alignItems: 'end', gap: '8px' },
    seedLabel: { color: colors.textSecondary, display: 'flex', flexDirection: 'column' as const, fontSize: '10px', gap: '3px' },
    select: { backgroundColor: colors.bgLight, border: `1px solid ${colors.border}`, borderRadius: '5px', color: colors.text, padding: '4px 6px' },
    button: { backgroundColor: colors.primary, border: 'none', borderRadius: '5px', color: '#fff', cursor: 'pointer', fontSize: '12px', fontWeight: 700, padding: '6px 10px' },
    result: { display: 'flex', flexDirection: 'column' as const, gap: '10px' },
    scoreRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' },
    label: { color: colors.textSecondary, fontSize: '10px', fontWeight: 700, letterSpacing: '0.05em' },
    score: { color: colors.success, fontFamily: 'var(--font-mono)', fontSize: '28px', fontWeight: 800, lineHeight: 1.1 },
    caption: { color: colors.textSecondary, fontSize: '11px', marginTop: '2px' },
    floorBadge: { fontSize: '10px', fontWeight: 800, letterSpacing: '0.04em', textAlign: 'right' as const },
    track: { backgroundColor: 'rgba(2, 6, 23, 0.7)', borderRadius: '999px', height: '12px', overflow: 'hidden' },
    fill: { background: 'linear-gradient(90deg, #22c55e, #84cc16)', borderRadius: '999px', height: '100%', transition: 'width 180ms ease-out' },
    referenceGrid: { display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '8px' },
    reference: { backgroundColor: colors.bgLight, borderRadius: '6px', color: colors.text, display: 'flex', flexDirection: 'column' as const, gap: '2px', padding: '8px' },
    referenceName: { color: colors.textSecondary, fontSize: '10px' },
    referenceDetail: { color: colors.textSecondary, fontSize: '10px' },
    loading: { color: colors.textSecondary, fontSize: '12px', padding: '8px 0' },
    error: { color: colors.danger, fontSize: '12px', padding: '8px 0' },
} as const;
