import styles from './WatchModeToggle.module.css';

interface WatchModeToggleProps {
    active: boolean;
    onToggle: () => void;
}

export function WatchModeToggle({ active, onToggle }: WatchModeToggleProps) {
    return (
        <button
            className={styles.toggle}
            onClick={onToggle}
            title={active ? 'Exit Watch Mode' : 'Enter Watch Mode: hide the dashboard and just watch the tank'}
        >
            {active ? '✕ Exit Watch' : '🎬 Watch Mode'}
        </button>
    );
}
