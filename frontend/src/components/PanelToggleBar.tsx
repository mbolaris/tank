import type { PanelId } from '../hooks/useVisiblePanels';
import styles from './TankView.module.css';

const PANEL_CONFIG: { id: PanelId; label: string; icon: string }[] = [
    { id: 'insights', label: 'Insights', icon: '💬' },
    { id: 'skills', label: 'Skills', icon: '🎯' },
    { id: 'trends', label: 'Trends', icon: '📈' },
    { id: 'ecosystem', label: 'Ecosystem', icon: '🌿' },
    { id: 'genetics', label: 'Genetics', icon: '🧬' },
    { id: 'soccer', label: 'Soccer', icon: '⚽' },
    { id: 'poker', label: 'Poker', icon: '♠' },
];

interface PanelToggleBarProps {
    visible: PanelId[];
    onToggle: (id: PanelId) => void;
}

export function PanelToggleBar({ visible, onToggle }: PanelToggleBarProps) {
    return (
        <div className={styles.panelToggleBar}>
            <span className={styles.panelToggleLabel}>Show panels:</span>
            {PANEL_CONFIG.map(({ id, label, icon }) => {
                const isVisible = visible.includes(id);
                return (
                    <button
                        key={id}
                        className={`${styles.panelToggle} ${isVisible ? styles.active : ''}`}
                        onClick={() => onToggle(id)}
                        aria-pressed={isVisible}
                    >
                        <span className={styles.panelToggleIcon}>{icon}</span>
                        <span>{label}</span>
                    </button>
                );
            })}
        </div>
    );
}
