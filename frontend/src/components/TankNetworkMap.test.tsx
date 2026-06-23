import { describe, expect, it } from 'vitest';

import { buildConnectionPayload, type TankNode } from './tankNetworkConnections';

const tank = (overrides: Partial<TankNode>): TankNode => ({
    id: 'tank-a',
    name: 'Tank A',
    serverId: 'server-a',
    serverName: 'Server A',
    allowTransfers: true,
    x: 100,
    y: 200,
    ...overrides,
});

describe('buildConnectionPayload', () => {
    it('includes server ids when creating a cross-server tank connection', () => {
        const nodes = new Map<string, TankNode>([
            ['tank-a', tank({ id: 'tank-a', serverId: 'local-server', x: 100 })],
            ['tank-b', tank({ id: 'tank-b', serverId: 'remote-server', x: 300 })],
        ]);

        const payload = buildConnectionPayload('tank-a', 'tank-b', 25, nodes);

        expect(payload).toEqual({
            id: 'tank-a->tank-b',
            sourceId: 'tank-a',
            destinationId: 'tank-b',
            probability: 25,
            direction: 'right',
            sourceServerId: 'local-server',
            destinationServerId: 'remote-server',
        });
    });

    it('sets direction from node positions', () => {
        const nodes = new Map<string, TankNode>([
            ['tank-a', tank({ id: 'tank-a', x: 300 })],
            ['tank-b', tank({ id: 'tank-b', x: 100 })],
        ]);

        expect(buildConnectionPayload('tank-a', 'tank-b', 50, nodes).direction).toBe('left');
    });
});
