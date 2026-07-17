import styles from './ModeSwitch.module.css';

export type UiMode = 'watch' | 'build' | 'analyze';

interface ModeSwitchProps {
    /** Currently active mode, or null when Analyze has no panel open. */
    mode: UiMode | null;
    onSelect: (mode: UiMode) => void;
}

const MODES: Array<{ id: UiMode; icon: string; label: string; title: string }> = [
    { id: 'watch', icon: '🎬', label: 'Watch', title: 'Watch: hide the dashboard and just watch the tank' },
    { id: 'build', icon: '🔨', label: 'Build', title: 'Build: place and arrange objects in the tank' },
    { id: 'analyze', icon: '📊', label: 'Analyze', title: 'Analyze: open research panels' },
];

export function ModeSwitch({ mode, onSelect }: ModeSwitchProps) {
    return (
        <div className={styles.switch} role="toolbar" aria-label="View mode">
            {MODES.map(({ id, icon, label, title }) => (
                <button
                    key={id}
                    className={mode === id ? styles.optionActive : styles.option}
                    onClick={() => onSelect(id)}
                    aria-pressed={mode === id}
                    title={title}
                >
                    <span aria-hidden="true">{icon}</span> {label}
                </button>
            ))}
        </div>
    );
}
