import { ARENA_VIEW_MODES, arenaViewModeLabel, type ArenaViewMode } from './soccerViewMode';
import styles from './SoccerArenaView.module.css';

/**
 * §4 view-mode segmented control.
 *
 * A radiogroup rather than a row of buttons: the modes are mutually exclusive
 * and a screen reader should say "Tactical, 2 of 2 selected", not read two
 * unrelated toggles.
 */
export function ArenaViewModeControl({
    mode,
    onChange,
}: {
    mode: ArenaViewMode;
    onChange: (mode: ArenaViewMode) => void;
}) {
    return (
        <div className={styles.viewModes} role="radiogroup" aria-label="Arena view mode" data-testid="arena-view-mode">
            {ARENA_VIEW_MODES.map((candidate) => {
                const label = arenaViewModeLabel(candidate);
                const selected = candidate === mode;
                return (
                    <button
                        key={candidate}
                        type="button"
                        role="radio"
                        aria-checked={selected}
                        className={`${styles.viewModeButton} ${selected ? styles.viewModeSelected : ''}`}
                        onClick={() => onChange(candidate)}
                        title={`${label} view (${candidate[0].toUpperCase()})`}
                        data-testid={`arena-view-mode-${candidate}`}
                    >
                        {label}
                    </button>
                );
            })}
        </div>
    );
}
