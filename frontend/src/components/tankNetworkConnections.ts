export interface TankNode {
    id: string;
    name: string;
    serverId: string;
    serverName: string;
    allowTransfers: boolean;
    x: number;
    y: number;
}

export interface TankConnection {
    id: string;
    sourceId: string;
    destinationId: string;
    probability: number;
    direction: 'left' | 'right';
    sourceServerId?: string;
    destinationServerId?: string;
}

export function buildConnectionPayload(
    sourceId: string,
    destinationId: string,
    probability: number,
    nodeLookup: Map<string, TankNode>,
): TankConnection {
    const sourceNode = nodeLookup.get(sourceId);
    const destNode = nodeLookup.get(destinationId);
    const direction = sourceNode && destNode && destNode.x > sourceNode.x ? 'right' : 'left';

    return {
        id: `${sourceId}->${destinationId}`,
        sourceId,
        destinationId,
        probability,
        direction,
        ...(sourceNode?.serverId ? { sourceServerId: sourceNode.serverId } : {}),
        ...(destNode?.serverId ? { destinationServerId: destNode.serverId } : {}),
    };
}
