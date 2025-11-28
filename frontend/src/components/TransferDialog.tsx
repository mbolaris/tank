/**
 * TransferDialog - Modal for transferring entities between tanks
 */

import { useState, useEffect } from 'react';
import { config, type TankStatus } from '../config';

interface TransferDialogProps {
    entityId: number;
    entityType: string;
    sourceTankId: string;
    sourceTankName: string;
    onClose: () => void;
    onTransferComplete: (success: boolean, message: string) => void;
}

export function TransferDialog({
    entityId,
    entityType,
    sourceTankId,
    sourceTankName,
    onClose,
    onTransferComplete,
}: TransferDialogProps) {
    const [tanks, setTanks] = useState<TankStatus[]>([]);
    const [loading, setLoading] = useState(true);
    const [transferring, setTransferring] = useState(false);
    const [selectedTankId, setSelectedTankId] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchTanks();
    }, []);

    const fetchTanks = async () => {
        setError(null);
        try {
            const response = await fetch(`${config.tanksApiUrl}?include_private=true`);
            if (!response.ok) {
                throw new Error('Failed to fetch tanks');
            }
            const data = await response.json();
            // Filter out source tank and tanks that don't allow transfers
            const eligibleTanks = data.tanks.filter(
                (tank: TankStatus) =>
                    tank.tank.tank_id !== sourceTankId && tank.tank.allow_transfers
            );
            setTanks(eligibleTanks);
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to load tanks';
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    const handleTransfer = async () => {
        if (!selectedTankId) return;

        setTransferring(true);
        try {
            const response = await fetch(
                `${config.apiBaseUrl}/api/tanks/${sourceTankId}/transfer?entity_id=${entityId}&destination_tank_id=${selectedTankId}`,
                { method: 'POST' }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Transfer failed');
            }

            onTransferComplete(true, data.message || 'Entity transferred successfully');
            onClose();
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Transfer failed';
            onTransferComplete(false, message);
        } finally {
            setTransferring(false);
        }
    };

    const entityTypeDisplay = entityType === 'fish' ? 'Fish' : entityType === 'fractal_plant' ? 'Plant' : entityType;

    return (
        <div
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(0, 0, 0, 0.7)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 1000,
            }}
            onClick={onClose}
        >
            <div
                style={{
                    backgroundColor: '#1e293b',
                    borderRadius: '12px',
                    padding: '24px',
                    maxWidth: '500px',
                    width: '90%',
                    border: '1px solid #334155',
                    color: '#e2e8f0',
                }}
                onClick={(e) => e.stopPropagation()}
            >
                <h2 style={{ margin: '0 0 8px 0', fontSize: '20px', fontWeight: 600 }}>
                    Transfer Entity
                </h2>
                <p style={{ margin: '0 0 20px 0', color: '#94a3b8', fontSize: '14px' }}>
                    Transfer {entityTypeDisplay} #{entityId} from {sourceTankName}
                </p>

                {loading ? (
                    <div style={{ textAlign: 'center', padding: '20px', color: '#94a3b8' }}>
                        Loading available tanks...
                    </div>
                ) : error ? (
                    <div style={{ textAlign: 'center', padding: '20px' }}>
                        <p style={{ color: '#ef4444', margin: 0 }}>
                            {error}
                        </p>
                        <button
                            onClick={fetchTanks}
                            style={{
                                marginTop: '12px',
                                padding: '8px 16px',
                                backgroundColor: '#3b82f6',
                                color: 'white',
                                border: 'none',
                                borderRadius: '6px',
                                cursor: 'pointer',
                                fontSize: '13px',
                            }}
                        >
                            Retry
                        </button>
                    </div>
                ) : tanks.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '20px' }}>
                        <p style={{ color: '#94a3b8', margin: 0 }}>
                            No eligible destination tanks found
                        </p>
                        <p style={{ color: '#64748b', fontSize: '13px', marginTop: '8px' }}>
                            Tanks must have transfers enabled to receive entities
                        </p>
                    </div>
                ) : (
                    <div>
                        <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: 500 }}>
                            Select Destination Tank:
                        </label>
                        <div
                            style={{
                                maxHeight: '250px',
                                overflowY: 'auto',
                                marginBottom: '20px',
                                border: '1px solid #334155',
                                borderRadius: '8px',
                            }}
                        >
                            {tanks.map((tankStatus) => (
                                <div
                                    key={tankStatus.tank.tank_id}
                                    onClick={() => setSelectedTankId(tankStatus.tank.tank_id)}
                                    style={{
                                        padding: '12px 16px',
                                        cursor: 'pointer',
                                        backgroundColor:
                                            selectedTankId === tankStatus.tank.tank_id
                                                ? '#3b82f6'
                                                : '#0f172a',
                                        borderBottom: '1px solid #334155',
                                        transition: 'background-color 0.2s',
                                    }}
                                >
                                    <div style={{ fontWeight: 600, marginBottom: '4px' }}>
                                        {tankStatus.tank.name}
                                    </div>
                                    {tankStatus.tank.description && (
                                        <div style={{ fontSize: '13px', color: '#94a3b8' }}>
                                            {tankStatus.tank.description}
                                        </div>
                                    )}
                                    <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
                                        {tankStatus.stats?.fish_count || 0} fish
                                        {' • '}
                                        Gen {tankStatus.stats?.generation || 0}
                                        {' • '}
                                        {tankStatus.running ? (tankStatus.paused ? 'Paused' : 'Running') : 'Stopped'}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                    <button
                        onClick={onClose}
                        disabled={transferring}
                        style={{
                            padding: '10px 20px',
                            backgroundColor: 'transparent',
                            color: '#94a3b8',
                            border: '1px solid #475569',
                            borderRadius: '6px',
                            cursor: transferring ? 'not-allowed' : 'pointer',
                            fontSize: '14px',
                            fontWeight: 600,
                        }}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleTransfer}
                        disabled={!selectedTankId || transferring || tanks.length === 0}
                        style={{
                            padding: '10px 20px',
                            backgroundColor:
                                !selectedTankId || transferring || tanks.length === 0
                                    ? '#475569'
                                    : '#22c55e',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor:
                                !selectedTankId || transferring || tanks.length === 0
                                    ? 'not-allowed'
                                    : 'pointer',
                            fontSize: '14px',
                            fontWeight: 600,
                            opacity: transferring ? 0.7 : 1,
                        }}
                    >
                        {transferring ? 'Transferring...' : 'Transfer'}
                    </button>
                </div>
            </div>
        </div>
    );
}
