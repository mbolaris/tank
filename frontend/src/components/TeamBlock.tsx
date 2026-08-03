import type { SoccerMatchState, SoccerParticipant } from '../types/simulation';
import styles from './SoccerScoreboard.module.css';

interface TeamBlockProps {
    match: SoccerMatchState | null;
    side: 'left' | 'right';
    name: string;
    score: number;
}

function teamGeneration(match: SoccerMatchState | null, side: 'left' | 'right'): number | undefined {
    const generations = (match?.participants ?? [])
        .filter((participant: SoccerParticipant) => participant.side === side && participant.generation !== undefined)
        .map((participant) => participant.generation as number);
    return generations.length ? Math.max(...generations) : undefined;
}

export function TeamBlock({ match, side, name, score }: TeamBlockProps) {
    const generation = teamGeneration(match, side);
    return (
        <div className={`${styles.teamBlock} ${side === 'right' ? styles.teamAway : ''}`} data-testid={`team-block-${side}`}>
            <span className={`${styles.teamBar} ${side === 'left' ? styles.teamBarLeft : styles.teamBarRight}`} aria-hidden="true" />
            <span className={styles.teamEmblem} aria-hidden="true">◉</span>
            <span className={styles.teamCopy}>
                <span className={styles.teamName}>{name}</span>
                <span className={styles.teamMeta}>{generation === undefined ? 'Team' : `Gen ${generation}`}</span>
            </span>
            <strong className={styles.teamScore}>{score}</strong>
        </div>
    );
}
