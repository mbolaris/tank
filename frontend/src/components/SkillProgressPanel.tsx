import { useSkillProgress } from '../hooks/useSkillProgress';
import type { SkillProgressDomain, SkillVerdict } from '../types/skillProgress';
import styles from './SkillProgressPanel.module.css';

/**
 * How each verdict is shown. The glyph carries the state as well as the colour,
 * so the panel still reads in greyscale and without relying on red/green.
 */
const PRESENTATION: Record<SkillVerdict, { label: string; glyph: string; tone: string }> = {
    progressing: { label: 'Progressing', glyph: '▲', tone: styles.progressing },
    possibly_progressing: { label: 'Possibly', glyph: '◆', tone: styles.possibly },
    stalled: { label: 'Stalled', glyph: '■', tone: styles.stalled },
    at_ceiling: { label: 'At ceiling', glyph: '★', tone: styles.ceiling },
    no_data: { label: 'No data', glyph: '·', tone: styles.nodata },
};

const DOMAIN_LABELS: Record<string, string> = {
    foraging: 'Foraging',
    poker: 'Poker',
    soccer: 'Soccer',
};

function Row({ entry }: { entry: SkillProgressDomain }) {
    const presentation = PRESENTATION[entry.verdict] ?? PRESENTATION.no_data;
    const span = entry.generation_span;
    return (
        <div className={`${styles.row} ${presentation.tone}`}>
            <span className={styles.mark} aria-hidden="true">{presentation.glyph}</span>
            <div>
                <span className={styles.domain}>{DOMAIN_LABELS[entry.domain] ?? entry.domain}</span>
                <span className={styles.state}>{presentation.label}</span>
            </div>
            <div className={styles.reason}>{entry.reason}</div>
            <div className={styles.numbers}>
                {entry.samples} sample{entry.samples === 1 ? '' : 's'}
                {span > 0 ? ` · ${span} generations` : ''}
            </div>
        </div>
    );
}

interface SkillProgressPanelProps {
    worldId?: string;
}

/**
 * Whether evolution is getting anywhere in each skill domain.
 *
 * The verdict itself is decided in `core/research/skill_progress.py`; this
 * renders it and the sentence explaining what it was judged against, because a
 * bare "stalled" invites someone to go hunting for a bug when the real answer
 * may be "three samples is not enough to tell yet".
 */
export function SkillProgressPanel({ worldId }: SkillProgressPanelProps) {
    const { domains, loading, error } = useSkillProgress(worldId);

    return (
        <section className={styles.panel} aria-label="Evolution progress by skill domain">
            <div className={styles.head}>
                <span className={styles.title}>Evolution progress</span>
                <span className={styles.note} title="A verdict compares a recent window of live skill measurements against an earlier one, and only calls it progress when the change is larger than the sampling noise.">
                    vs sampling noise
                </span>
            </div>

            {error && <div className={styles.message}>Progress unavailable: {error}</div>}
            {!error && loading && !domains && <div className={styles.message}>Measuring…</div>}
            {!error && !loading && domains && domains.length === 0 && (
                <div className={styles.message}>No evolving domains reported for this world.</div>
            )}

            {domains && domains.length > 0 && (
                <div className={styles.rows}>
                    {domains.map((entry) => <Row key={entry.domain} entry={entry} />)}
                </div>
            )}
        </section>
    );
}
