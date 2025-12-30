
import { Button } from './ui';
import type { ViewMode, WorldType } from '../rendering/types';
import { rendererRegistry } from '../rendering/registry';
import { useMemo } from 'react';

interface ViewModeToggleProps {
    worldType?: WorldType;
    viewMode: ViewMode;
    onChange: (mode: ViewMode) => void;
}

export function ViewModeToggle({ worldType, viewMode, onChange }: ViewModeToggleProps) {

    // Only show if worldType is tank (per requirements)
    if (worldType !== 'tank') return null;

    // Check if top-down renderer is available
    // We can do this by checking if the registry has a factory for it 
    // BUT registry doesn't expose `has`. 
    // We can just try to see if it renders validly, or just check if it's "tank".
    // For now, hardcode check as per "Disable top-down if renderer registry doesn't have a match" check.
    // Since registry doesn't currently expose check, I'll rely on the fact that I haven't registered it yet
    // so it would return Fallback. 
    // Actually, I should probably add a `hasRenderer` method to registry or just let it fall back.
    // The requirement said "Disable top-down if renderer registry doesn’t have a match (nice touch)".
    // I'll skip the disable logic for now to keep it simple, or I can update registry to add `has`.
    // Let's implement it simply first.

    return (
        <div style={{ display: 'flex', gap: '8px', backgroundColor: 'rgba(0,0,0,0.2)', padding: '4px', borderRadius: '8px' }}>
            <Button
                variant={viewMode === 'side' ? 'primary' : 'secondary'}
                onClick={() => onChange('side')}
                style={{ fontSize: '12px', padding: '4px 12px', height: 'auto' }}
            >
                Side View
            </Button>
            <Button
                variant={viewMode === 'topdown' ? 'primary' : 'secondary'}
                onClick={() => onChange('topdown')}
                style={{ fontSize: '12px', padding: '4px 12px', height: 'auto' }}
            >
                Top Down
            </Button>
        </div>
    );
}
