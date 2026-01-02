
import { Button } from './ui';
import type { ViewMode, WorldType } from '../rendering/types';
import { rendererRegistry } from '../rendering/registry';

interface ViewModeToggleProps {
    worldType?: WorldType;
    viewMode: ViewMode;
    onChange: (mode: ViewMode) => void;
}

export function ViewModeToggle({ worldType, viewMode, onChange }: ViewModeToggleProps) {
    const type = worldType || 'tank';

    // Only show if both side and topdown renderers exist for this worldType
    const hasSide = rendererRegistry.hasRenderer(type, 'side');
    const hasTopDown = rendererRegistry.hasRenderer(type, 'topdown');

    if (!hasSide || !hasTopDown) return null;

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
