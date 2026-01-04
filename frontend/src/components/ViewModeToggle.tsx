
import { Button, FishIcon } from './ui';
import type { ViewMode } from '../rendering/types';

interface ViewModeToggleProps {
    viewMode: ViewMode;
    onChange: (mode: ViewMode) => void;
    petriMode: boolean;
    onPetriModeChange: (enabled: boolean) => void;
}

// Microscope icon for microbes view
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

/**
 * Simple toggle between two complete rendering styles:
 * - Tank View: Rectangular fish tank with fish (side view)
 * - Petri View: Circular dish with microbes (top-down view)
 */
export function ViewModeToggle({ onChange, petriMode, onPetriModeChange }: ViewModeToggleProps) {
    const isTankMode = !petriMode;
    const isPetriMode = petriMode;

    const handleTankClick = () => {
        onPetriModeChange(false);
        onChange('side');  // Tank uses side view
    };

    const handlePetriClick = () => {
        onPetriModeChange(true);
        onChange('topdown');  // Petri uses top-down view
    };

    return (
        <div style={{ display: 'flex', gap: '8px', backgroundColor: 'rgba(0,0,0,0.2)', padding: '4px', borderRadius: '8px' }}>
            <Button
                variant={isTankMode ? 'primary' : 'secondary'}
                onClick={handleTankClick}
                style={{ fontSize: '12px', padding: '4px 12px', height: 'auto' }}
            >
                <FishIcon size={14} /> Tank
            </Button>
            <Button
                variant={isPetriMode ? 'primary' : 'secondary'}
                onClick={handlePetriClick}
                style={{
                    fontSize: '12px',
                    padding: '4px 12px',
                    height: 'auto',
                    backgroundColor: isPetriMode ? '#4CAF50' : undefined,
                }}
            >
                <MicroscopeIcon size={14} /> Microbes
            </Button>
        </div>
    );
}

