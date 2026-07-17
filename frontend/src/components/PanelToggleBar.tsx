import type { PanelId } from '../hooks/useVisiblePanels';
import styles from './TankView.module.css';

const PANEL_CONFIG: { id: PanelId; label: string; icon: string }[] = [
    { id: 'insights', label: 'Board', icon: '📋' },
    { id: 'skills', label: 'Skills', icon: '🎯' },
    { id: 'trends', label: 'Trends', icon: '📈' },
    { id: 'ecosystem', label: 'Ecosystem', icon: '🌿' },
    { id: 'genetics', label: 'Genetics', icon: '🧬' },
    { id: 'soccer', label: 'Soccer', icon: '⚽' },
    { id: 'poker', label: 'Poker', icon: '♠' },
];

interface PanelToggleBarProps {
    visible: PanelId[];
    onSelect: (id: PanelId) => void;
}

export function PanelToggleBar({ visible, onSelect }: PanelToggleBarProps) {
    return (
        <div className={styles.panelToggleBar} role="toolbar" aria-label="Analysis workspace">
            <span className={styles.panelToggleLabel}>Analysis</span>
            {PANEL_CONFIG.map(({ id, label, icon }) => {
                const isVisible = visible.includes(id);
                return (
                    <button
                        key={id}
                        className={`${styles.panelToggle} ${isVisible ? styles.active : ''}`}
                        onClick={() => onSelect(id)}
                        aria-pressed={isVisible}
                        title={`Open ${label}`}
                    >
                        <span className={styles.panelToggleIcon}>{icon}</span>
                        <span>{label}</span>
                    </button>
                );
            })}
        </div>
    );
}
