
import { Button } from './ui';
import type { ViewMode } from '../rendering/types';

interface ViewModeToggleProps {
    viewMode: ViewMode;
    onChange: (mode: ViewMode) => void;
    petriMode: boolean;
    onPetriModeChange: (enabled: boolean) => void;
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
                🐟 Fish Tank
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
                🔬 Microbes
            </Button>
        </div>
    );
}
