import type { ServerWithWorlds } from '../../config';
import { TankCard } from './TankCard';
import styles from '../NetworkDashboard.module.css';

interface ServerCardProps {
    serverWithWorlds: ServerWithWorlds;
    onDeleteTank: (tankId: string, tankName: string) => void;
    onRefresh: () => void;
}

export function ServerCard({ serverWithWorlds, onDeleteTank, onRefresh }: ServerCardProps) {
    const { server, worlds } = serverWithWorlds;

    const statusColor = server.status === 'online' ? '#22c55e' :
        server.status === 'degraded' ? '#f59e0b' : '#ef4444';

    const formatUptime = (seconds: number): string => {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        }
        return `${minutes}m`;
    };

    const platformMeta = [
        server.platform,
        server.architecture,
        server.hardware_model,
        server.logical_cpus ? `${server.logical_cpus} logical CPUs` : null,
    ].filter(Boolean) as string[];

    return (
        <div className={styles.serverCard} style={{
            backgroundColor: '#1e293b',
            borderRadius: '12px',
            border: '2px solid #334155',
            overflow: 'hidden',
        }}>
            {/* Server Header */}
            <div className={styles.serverHeader} style={{
                padding: '20px 24px',
                borderBottom: '1px solid #334155',
                backgroundColor: '#0f172a',
            }}>
                <div className={styles.serverHeaderRow} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div className={styles.serverDetails}>
                        <div className={styles.serverTitleRow} style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                            <h2 style={{
                                margin: 0,
                                fontSize: '20px',
                                fontWeight: 600,
                                color: '#f1f5f9',
                            }}>
                                🖥️ {server.hostname}
                            </h2>
                            <span style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                fontSize: '12px',
                                color: statusColor,
                                fontWeight: 500,
                            }}>
                                <span style={{
                                    width: '8px',
                                    height: '8px',
                                    borderRadius: '50%',
                                    backgroundColor: statusColor,
                                }} />
                                {server.status.toUpperCase()}
                            </span>
                            <span style={{
                                fontSize: '11px',
                                backgroundColor: '#334155',
                                color: '#94a3b8',
                                padding: '2px 8px',
                                borderRadius: '4px',
                                fontWeight: 500,
                            }}>
                                v{server.version}
                            </span>
                        </div>
                        <div className={styles.serverMeta} style={{ fontSize: '13px', color: '#94a3b8', display: 'flex', gap: '16px' }}>
                            <span>{server.host}:{server.port}</span>
                            <span>&bull;</span>
                            <span>Uptime: {formatUptime(server.uptime_seconds)}</span>
                            {server.cpu_percent != null && (
                                <>
                                    <span>&bull;</span>
                                    <span>CPU: {server.cpu_percent.toFixed(1)}%</span>
                                </>
                            )}
                            {server.memory_mb != null && (
                                <>
                                    <span>&bull;</span>
                                    <span>Memory: {server.memory_mb.toFixed(0)} MB</span>
                                </>
                            )}
                        </div>
                        {platformMeta.length > 0 && (
                            <div className={styles.serverPlatformMeta} style={{
                                marginTop: '8px',
                                display: 'flex',
                                flexWrap: 'wrap',
                                gap: '8px',
                                fontSize: '12px',
                                color: '#cbd5e1',
                            }}>
                                {platformMeta.map((detail) => (
                                    <span key={detail} style={{
                                        backgroundColor: '#0b1728',
                                        border: '1px solid #334155',
                                        padding: '4px 8px',
                                        borderRadius: '6px',
                                    }}>
                                        {detail}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>
                    <div className={styles.serverWorldCount} style={{
                        textAlign: 'right',
                    }}>
                        <div style={{ fontSize: '28px', fontWeight: 700, color: '#3b82f6' }}>
                            {worlds.length}
                        </div>
                        <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                            world{worlds.length !== 1 ? 's' : ''}
                        </div>
                    </div>
                </div>
            </div>

            {/* Tanks Grid */}
            <div style={{ padding: '20px' }}>
                {worlds.length === 0 ? (
                    <div style={{
                        textAlign: 'center',
                        padding: '32px',
                        color: '#64748b',
                        fontSize: '14px',
                    }}>
                        No worlds running on this server
                    </div>
                ) : (
                    <div className={styles.tankGrid} style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 350px), 1fr))',
                        gap: '16px',
                    }}>
                        {[...worlds].sort((a, b) => (b.frame_count ?? 0) - (a.frame_count ?? 0)).map((tankStatus) => (
                            <TankCard
                                key={tankStatus.world_id}
                                tankStatus={tankStatus}
                                onDelete={() => onDeleteTank(tankStatus.world_id, tankStatus.name)}
                                onRefresh={onRefresh}
                            />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
