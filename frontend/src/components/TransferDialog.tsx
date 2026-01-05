/**
 * TransferDialog - Modal for transferring entities between tanks
 */

import { useState, useEffect, useCallback } from 'react';
import { config } from '../config';

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
    const [tanks, setTanks] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [transferring, setTransferring] = useState(false);
    const [selectedTankId, setSelectedTankId] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const fetchTanks = useCallback(async () => {
        setError(null);
        try {
            const response = await fetch(`${config.apiBaseUrl}/api/worlds?include_private=true`);
            if (!response.ok) {
                throw new Error('Failed to fetch worlds');
            }
            const data = await response.json();
            // Filter out source tank and tanks that don't allow transfers
            const eligibleTanks = data.worlds.filter(
                (world: any) =>
                    world.id !== sourceTankId && world.allow_transfers
            );
            setTanks(eligibleTanks);
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to load worlds';
            setError(message);
        } finally {
            setLoading(false);
        }
    }, [sourceTankId]);

    useEffect(() => {
        fetchTanks();
    }, [fetchTanks]);

    const handleTransfer = async () => {
        if (!selectedTankId) return;

        setTransferring(true);
        try {
            const response = await fetch(
                `${config.apiBaseUrl}/api/worlds/${sourceTankId}/transfer?entity_id=${entityId}&destination_world_id=${selectedTankId}`,
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

    const entityTypeDisplay = entityType === 'fish' ? 'Fish' : entityType === 'plant' ? 'Plant' : entityType;

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
                            {tanks.map((world) => (
                                <div
                                    key={world.id}
                                    onClick={() => setSelectedTankId(world.id)}
                                    style={{
                                        padding: '12px 16px',
                                        cursor: 'pointer',
                                        backgroundColor:
                                            selectedTankId === world.id
                                                ? '#3b82f6'
                                                : '#0f172a',
                                        borderBottom: '1px solid #334155',
                                        transition: 'background-color 0.2s',
                                    }}
                                >
                                    <div style={{ fontWeight: 600, marginBottom: '4px' }}>
                                        {world.name}
                                    </div>
                                    {world.description && (
                                        <div style={{ fontSize: '13px', color: '#94a3b8' }}>
                                            {world.description}
                                        </div>
                                    )}
                                    <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
                                        {world.stats?.entity_count || 0} entities
                                        {' • '}
                                        {world.world_type}
                                        {' • '}
                                        {world.running ? (world.paused ? 'Paused' : 'Running') : 'Stopped'}
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
