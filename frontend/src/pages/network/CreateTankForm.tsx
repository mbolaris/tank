import type { ServerWithWorlds } from '../../config';

interface CreateTankFormProps {
    servers: ServerWithWorlds[];
    name: string;
    onNameChange: (name: string) => void;
    description: string;
    onDescriptionChange: (description: string) => void;
    selectedServerId: string;
    onServerChange: (serverId: string) => void;
    creating: boolean;
    onSubmit: (e: React.FormEvent) => void;
    onCancel: () => void;
}

/**
 * Create-tank form.
 *
 * Field state deliberately lives in the parent page rather than here: the form
 * is conditionally rendered, so owning the state locally would discard a
 * half-typed name when the user cancels and reopens.
 */
export function CreateTankForm({
    servers,
    name,
    onNameChange,
    description,
    onDescriptionChange,
    selectedServerId,
    onServerChange,
    creating,
    onSubmit,
    onCancel,
}: CreateTankFormProps) {
    return (
        <div style={{
            backgroundColor: '#1e293b',
            borderRadius: '12px',
            padding: '24px',
            marginBottom: '24px',
            border: '1px solid #334155',
        }}>
            <h3 style={{ margin: '0 0 16px 0', color: '#f1f5f9' }}>Create New Tank</h3>
            <form onSubmit={onSubmit}>
                <div style={{ marginBottom: '16px' }}>
                    <label htmlFor="tank-name" style={{ display: 'block', marginBottom: '6px', color: '#94a3b8', fontSize: '14px' }}>
                        Tank Name
                    </label>
                    <input
                        id="tank-name"
                        type="text"
                        value={name}
                        onChange={(e) => onNameChange(e.target.value)}
                        placeholder="My Tank"
                        style={{
                            width: '100%',
                            padding: '10px 12px',
                            backgroundColor: '#0f172a',
                            border: '1px solid #475569',
                            borderRadius: '6px',
                            color: '#e2e8f0',
                            fontSize: '14px',
                            boxSizing: 'border-box',
                        }}
                        autoFocus
                    />
                </div>
                <div style={{ marginBottom: '16px' }}>
                    <label htmlFor="tank-description" style={{ display: 'block', marginBottom: '6px', color: '#94a3b8', fontSize: '14px' }}>
                        Description (optional)
                    </label>
                    <input
                        id="tank-description"
                        type="text"
                        value={description}
                        onChange={(e) => onDescriptionChange(e.target.value)}
                        placeholder="A brief description"
                        style={{
                            width: '100%',
                            padding: '10px 12px',
                            backgroundColor: '#0f172a',
                            border: '1px solid #475569',
                            borderRadius: '6px',
                            color: '#e2e8f0',
                            fontSize: '14px',
                            boxSizing: 'border-box',
                        }}
                    />
                </div>
                <div style={{ marginBottom: '16px' }}>
                    <label htmlFor="tank-server" style={{ display: 'block', marginBottom: '6px', color: '#94a3b8', fontSize: '14px' }}>
                        Server
                    </label>
                    <select
                        id="tank-server"
                        value={selectedServerId}
                        onChange={(e) => onServerChange(e.target.value)}
                        style={{
                            width: '100%',
                            padding: '10px 12px',
                            backgroundColor: '#0f172a',
                            border: '1px solid #475569',
                            borderRadius: '6px',
                            color: '#e2e8f0',
                            fontSize: '14px',
                            boxSizing: 'border-box',
                        }}
                    >
                        {servers.map((serverWithWorlds) => (
                            <option key={serverWithWorlds.server.server_id} value={serverWithWorlds.server.server_id}>
                                {serverWithWorlds.server.hostname} ({serverWithWorlds.server.status})
                            </option>
                        ))}
                    </select>
                </div>
                <div style={{ display: 'flex', gap: '12px' }}>
                    <button
                        type="submit"
                        disabled={creating || !selectedServerId}
                        style={{
                            padding: '10px 20px',
                            backgroundColor: creating ? '#475569' : '#22c55e',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: creating ? 'not-allowed' : 'pointer',
                            fontWeight: 600,
                            fontSize: '14px',
                        }}
                    >
                        {creating ? 'Creating...' : 'Create Tank'}
                    </button>
                    <button
                        type="button"
                        onClick={onCancel}
                        style={{
                            padding: '10px 20px',
                            backgroundColor: 'transparent',
                            color: '#94a3b8',
                            border: '1px solid #475569',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '14px',
                        }}
                    >
                        Cancel
                    </button>
                </div>
            </form>
        </div>
    );
}
