import type { ParameterEvolutionData } from '../types/entityDetails';
import { StatRow } from './ui';
import styles from './EntityInspectorDrawer.module.css';

interface ParameterEvolutionRowProps {
    label: string;
    currentValue: number;
    evolutionData?: ParameterEvolutionData | null;
    isInteger?: boolean;
}

export function ParameterEvolutionRow({
    label,
    currentValue,
    evolutionData,
    isInteger = false,
}: ParameterEvolutionRowProps) {
    const formattedVal = isInteger ? currentValue.toFixed(0) : currentValue.toFixed(2);

    if (!evolutionData) {
        return <StatRow label={label} value={formattedVal} />;
    }

    const { parent, species_median, carriers_pct, trend } = evolutionData;

    const trendText = trend === 'increasing' ? 'rising' : trend === 'declining' ? 'falling' : 'stable';
    const parentText = parent !== null ? (isInteger ? parent.toFixed(0) : parent.toFixed(2)) : 'N/A';
    const medianText = isInteger ? species_median.toFixed(0) : species_median.toFixed(2);

    return (
        <div className={styles.paramEvolutionContainer}>
            <div className={styles.paramHeader}>
                <span className={styles.paramLabel}>{label}</span>
                <span className={styles.paramValue}>{formattedVal}</span>
            </div>
            <div className={styles.paramSubDetails}>
                <div>Parent: {parentText} | Species median: {medianText}</div>
                <div>Present in {carriers_pct.toFixed(0)}% of the population and {trendText}</div>
            </div>
        </div>
    );
}
