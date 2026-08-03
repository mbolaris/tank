import type { BroadcastEvent } from './soccerEvents';
import styles from './SoccerEvents.module.css';

interface SoccerEffectsLayerProps {
    event: BroadcastEvent | null;
    reducedMotion?: boolean;
}

export function SoccerEffectsLayer({ event, reducedMotion = false }: SoccerEffectsLayerProps) {
    if (!event || event.kind === 'half_time' || event.kind === 'full_time' || event.kind === 'kickoff') return null;
    const effectClass = event.kind === 'goal' ? styles.goalEffect : event.kind === 'shot' ? styles.shotEffect : styles.possessionEffect;
    return <div className={`${styles.effectsLayer} ${effectClass} ${reducedMotion ? styles.reducedMotion : ''}`} aria-hidden="true" data-testid="soccer-effects-layer" />;
}
