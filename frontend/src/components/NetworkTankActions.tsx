import { Link } from 'react-router-dom';

interface NetworkTankActionsProps {
    worldId: string;
    name: string;
    paused: boolean;
    fastForward: boolean;
    disabled: boolean;
    onPause: () => void;
    onFastForward: () => void;
    onDelete: () => void;
}

export function NetworkTankActions({
    worldId, name, paused, fastForward, disabled, onPause, onFastForward, onDelete,
}: NetworkTankActionsProps) {
    const buttonStyle = {
        padding: '6px 10px', color: 'white', border: 'none', borderRadius: '4px',
        cursor: disabled ? 'not-allowed' : 'pointer', fontWeight: 600, fontSize: '11px',
    } as const;

    return (
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            <button onClick={onPause} disabled={disabled} aria-label={paused ? `Resume ${name}` : `Pause ${name}`} title={paused ? `Resume ${name}` : `Pause ${name}`} style={{ ...buttonStyle, backgroundColor: paused ? '#3b82f6' : '#f59e0b' }}>
                {paused ? 'Resume' : 'Pause'}
            </button>
            <button onClick={onFastForward} disabled={disabled} aria-label={fastForward ? `Set ${name} to normal speed` : `Fast forward ${name}`} title={fastForward ? 'Normal Speed' : 'Fast Forward'} style={{ ...buttonStyle, backgroundColor: fastForward ? '#a855f7' : '#475569' }}>
                {fastForward ? 'Normal speed' : 'Fast forward'}
            </button>
            <Link to={`/tank/${worldId}`} style={{ flex: 1, padding: '6px', backgroundColor: '#3b82f6', color: 'white', textDecoration: 'none', borderRadius: '4px', textAlign: 'center', fontWeight: 600, fontSize: '11px' }}>
                View
            </Link>
            <button onClick={onDelete} aria-label={`Delete ${name}`} title={`Delete ${name}`} style={{ padding: '6px 10px', backgroundColor: 'transparent', color: '#ef4444', border: '1px solid #ef4444', borderRadius: '4px', cursor: 'pointer', fontSize: '11px' }}>
                Delete
            </button>
        </div>
    );
}
