/**
 * TransferHistory - Display recent entity transfers between tanks
 */

import { useState, useEffect } from 'react';
import { config } from '../config';

interface Transfer {
    transfer_id: string;
    timestamp: string;
    entity_type: string;
    entity_old_id: number;
    entity_new_id: number | null;
    source_tank_id: string;
    source_tank_name: string;
    destination_tank_id: string;
    destination_tank_name: string;
    success: boolean;
    error: string | null;
}

interface TransferHistoryProps {
    onClose: () => void;
    tankId?: string; // Optional filter by tank ID
}

export function TransferHistory({ onClose, tankId }: TransferHistoryProps) {
    const [transfers, setTransfers] = useState<Transfer[]>([]);
    const [loading, setLoading] = useState(true);
    const [successOnly, setSuccessOnly] = useState(false);

    useEffect(() => {
        fetchTransfers();
        // Auto-refresh every 5 seconds
        const interval = setInterval(fetchTransfers, 5000);
        return () => clearInterval(interval);
    }, [tankId, successOnly]);

    const fetchTransfers = async () => {
        try {
            const params = new URLSearchParams({
                limit: '50',
                ...(tankId && { tank_id: tankId }),
                ...(successOnly && { success_only: 'true' }),
            });

            const response = await fetch(`${config.apiBaseUrl}/api/transfers?${params}`);
            if (!response.ok) {
                throw new Error('Failed to fetch transfers');
            }

            const data = await response.json();
            setTransfers(data.transfers);
        } catch (err) {
            console.error('Failed to load transfer history:', err);
        } finally {
            setLoading(false);
        }
    };

    const formatRelativeTime = (timestamp: string): string => {
        const now = new Date();
        const then = new Date(timestamp);
        const diffMs = now.getTime() - then.getTime();
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} min ago`;

        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;

        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    };

    const getEntityIcon = (entityType: string): string => {
        return entityType === 'fish' ? '🐟' : '🌿';
    };

    const getEntityLabel = (entityType: string): string => {
        return entityType === 'fish' ? 'Fish' : 'Plant';
    };

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
                    maxWidth: '600px',
                    width: '90%',
                    maxHeight: '80vh',
                    border: '1px solid #334155',
                    color: '#e2e8f0',
                    display: 'flex',
                    flexDirection: 'column',
                }}
                onClick={(e) => e.stopPropagation()}
            >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 600 }}>
                        Transfer History
                        {tankId && ' (Filtered)'}
                    </h2>
                    <button
                        onClick={onClose}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#94a3b8',
                            cursor: 'pointer',
                            fontSize: '24px',
                            padding: '0',
                            width: '32px',
                            height: '32px',
                        }}
                    >
                        ×
                    </button>
                </div>

                <div style={{ marginBottom: '16px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                        <input
                            type="checkbox"
                            checked={successOnly}
                            onChange={(e) => setSuccessOnly(e.target.checked)}
                            style={{ cursor: 'pointer' }}
                        />
                        <span style={{ fontSize: '14px', color: '#94a3b8' }}>Show successful only</span>
                    </label>
                </div>

                {loading ? (
                    <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>
                        Loading transfers...
                    </div>
                ) : transfers.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '40px' }}>
                        <p style={{ color: '#94a3b8', margin: 0 }}>No transfers found</p>
                        <p style={{ color: '#64748b', fontSize: '13px', marginTop: '8px' }}>
                            Entity transfers will appear here
                        </p>
                    </div>
                ) : (
                    <div
                        style={{
                            flex: 1,
                            overflowY: 'auto',
                            border: '1px solid #334155',
                            borderRadius: '8px',
                        }}
                    >
                        {transfers.map((transfer) => (
                            <div
                                key={transfer.transfer_id}
                                style={{
                                    padding: '16px',
                                    borderBottom: '1px solid #334155',
                                    backgroundColor: transfer.success ? '#0f172a' : '#1e1b1b',
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                                    <span style={{ fontSize: '20px' }}>
                                        {getEntityIcon(transfer.entity_type)}
                                    </span>
                                    <div style={{ flex: 1 }}>
                                        <div style={{ fontWeight: 600, fontSize: '14px' }}>
                                            {getEntityLabel(transfer.entity_type)} #{transfer.entity_old_id}
                                            {transfer.success && transfer.entity_new_id && (
                                                <span style={{ color: '#22c55e' }}> → #{transfer.entity_new_id}</span>
                                            )}
                                        </div>
                                        <div style={{ fontSize: '13px', color: '#94a3b8', marginTop: '2px' }}>
                                            {transfer.source_tank_name}
                                            <span style={{ margin: '0 6px', color: '#475569' }}>→</span>
                                            {transfer.destination_tank_name}
                                        </div>
                                    </div>
                                    <div style={{ textAlign: 'right' }}>
                                        <div
                                            style={{
                                                fontSize: '12px',
                                                fontWeight: 600,
                                                color: transfer.success ? '#22c55e' : '#ef4444',
                                                marginBottom: '2px',
                                            }}
                                        >
                                            {transfer.success ? '✓ Success' : '✗ Failed'}
                                        </div>
                                        <div style={{ fontSize: '11px', color: '#64748b' }}>
                                            {formatRelativeTime(transfer.timestamp)}
                                        </div>
                                    </div>
                                </div>

                                {!transfer.success && transfer.error && (
                                    <div
                                        style={{
                                            marginTop: '8px',
                                            padding: '8px 12px',
                                            backgroundColor: '#2d1a1a',
                                            borderRadius: '6px',
                                            fontSize: '12px',
                                            color: '#fca5a5',
                                        }}
                                    >
                                        Error: {transfer.error}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}

                <div style={{ marginTop: '16px', textAlign: 'center' }}>
                    <button
                        onClick={onClose}
                        style={{
                            padding: '10px 24px',
                            backgroundColor: '#475569',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '14px',
                            fontWeight: 600,
                        }}
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}
