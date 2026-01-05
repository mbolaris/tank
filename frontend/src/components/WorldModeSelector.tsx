
import type { WorldType } from '../types/world';
import { WORLD_TYPE_LABELS } from '../types/world';
import styles from './WorldModeSelector.module.css';

interface WorldModeSelectorProps {
    worldType: WorldType;
    onChange: (worldType: WorldType) => void;
}

// Icon components for each world type
function FishIcon({ size = 16 }: { size?: number }) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <path d="M6.5 12c.94-3.46 4.94-6 8.5-6 3.56 0 6.06 2.54 7 6-.94 3.47-3.44 6-7 6s-7.56-2.53-8.5-6Z" />
            <path d="M18 12v.5" />
            <path d="M16 17.93a9.77 9.77 0 0 1 0-11.86" />
            <path d="M7 10.67C7 8 5.58 5.97 2.73 5.5c-1 1.5-1 5 .23 6.5-1.24 1.5-1.24 5-.23 6.5C5.58 18.03 7 16 7 13.33" />
            <path d="M10.46 7.26C10.2 5.88 9.17 4.24 8 3h5.8a2 2 0 0 1 1.98 1.67l.23 1.4" />
            <path d="m16.01 17.93-.23 1.4A2 2 0 0 1 13.8 21H9.5a5.96 5.96 0 0 0 1.49-3.98" />
        </svg>
    );
}

function MicroscopeIcon({ size = 16 }: { size?: number }) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <path d="M6 18h8" />
            <path d="M3 22h18" />
            <path d="M14 22a7 7 0 1 0 0-14h-1" />
            <path d="M9 14h2" />
            <path d="M9 12a2 2 0 0 1-2-2V6h6v4a2 2 0 0 1-2 2Z" />
            <path d="M12 6V4a2 2 0 0 0-4 0v2" />
        </svg>
    );
}

function SoccerIcon({ size = 16 }: { size?: number }) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <circle cx="12" cy="12" r="10" />
            <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
            <path d="M2 12h20" />
            <path d="m8 3 2.5 4.5" />
            <path d="m16 3-2.5 4.5" />
            <path d="m8 21 2.5-4.5" />
            <path d="m16 21-2.5-4.5" />
        </svg>
    );
}

function getIconForWorldType(worldType: WorldType, size: number = 16) {
    switch (worldType) {
        case 'tank':
            return <FishIcon size={size} />;
        case 'petri':
            return <MicroscopeIcon size={size} />;
        case 'soccer_training':
        case 'soccer':
            return <SoccerIcon size={size} />;
        default:
            return null;
    }
}

/**
 * World mode selector dropdown
 * Allows switching between Tank, Petri, Soccer Training, and Soccer (RCSS) modes
 */
export function WorldModeSelector({ worldType, onChange }: WorldModeSelectorProps) {
    const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
        onChange(event.target.value as WorldType);
    };

    return (
        <div className={styles.container}>
            <label htmlFor="world-mode-select" className={styles.label}>
                {getIconForWorldType(worldType, 14)}
                <span>World:</span>
            </label>
            <select
                id="world-mode-select"
                className={styles.select}
                value={worldType}
                onChange={handleChange}
            >
                <option value="tank">{WORLD_TYPE_LABELS.tank}</option>
                <option value="petri">{WORLD_TYPE_LABELS.petri}</option>
                <option value="soccer_training">{WORLD_TYPE_LABELS.soccer_training}</option>
                <option value="soccer">{WORLD_TYPE_LABELS.soccer}</option>
            </select>
        </div>
    );
}
