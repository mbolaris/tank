import { EcosystemStats } from '../EcosystemStats';
import { AutoEvaluateDisplay } from '../AutoEvaluateDisplay';
import type { StatsData, AutoEvaluateStats } from '../../types/simulation';
import styles from './TankEcosystemTab.module.css';

interface TankEcosystemTabProps {
    stats: StatsData | null;
    autoEvaluation: AutoEvaluateStats | undefined;
}

export function TankEcosystemTab({ stats, autoEvaluation }: TankEcosystemTabProps) {
    return (
        <div className={styles.ecosystemTab}>
            {/* Ecosystem Stats */}
            <EcosystemStats stats={stats} />

            {/* Auto Evaluation (if running) */}
            {autoEvaluation && (
                <div style={{ marginTop: '20px' }}>
                    <AutoEvaluateDisplay stats={autoEvaluation} loading={false} />
                </div>
            )}
        </div>
    );
}
