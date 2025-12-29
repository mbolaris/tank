import { stratify, type HierarchyNode } from 'd3-hierarchy';

export interface FishRecord {
    id: string;
    parent_id: string;
    algorithm: string;
    generation: number;
    color: string;
    birth_time?: number;
    is_alive?: boolean;
    tank_name?: string;
}

export interface TreeNodeData {
    name: string;
    attributes: {
        Algo: string;
        ID: string;
        Gen: number;
        IsAlive: boolean;
        Tank?: string;
    };
    nodeColor: string;
    children: TreeNodeData[];
}

const ROOT_NODE_ID = 'root';

export interface LineageTransformResult {
    tree: TreeNodeData | null;
    error: string | null;
}

/**
 * Recursively remove dead fish that have no children (dead-end branches).
 * This prunes the tree to only show lineages that have living descendants or contributed to them.
 */
const pruneDeadLeaves = (node: TreeNodeData, isRoot: boolean = false): TreeNodeData | null => {
    // Recursively prune children first
    if (node.children && node.children.length > 0) {
        const prunedChildren = node.children
            .map(child => pruneDeadLeaves(child, false))
            .filter((child): child is TreeNodeData => child !== null);

        node.children = prunedChildren;
    }

    // Keep root node always
    if (isRoot) {
        return node;
    }

    // Keep alive fish
    if (node.attributes.IsAlive) {
        return node;
    }

    // Keep dead fish that have children (they contributed to the lineage)
    if (node.children && node.children.length > 0) {
        return node;
    }

    // Remove dead fish with no children (dead-end branches)
    return null;
};

export const transformLineageData = (flatData: FishRecord[]): LineageTransformResult => {
    if (!flatData || flatData.length === 0) {
        return { tree: null, error: null };
    }

    try {
        // Validate data structure before stratifying
        const sanitizedData = flatData.map((record) => ({
            ...record,
            // Normalize any null/undefined parents to the root node
            parent_id: record.parent_id ?? ROOT_NODE_ID,
        }));

        const orphans: string[] = [];
        const idSet = new Set([...sanitizedData.map((d) => d.id), ROOT_NODE_ID]);

        for (const record of sanitizedData) {
            if (record.parent_id !== ROOT_NODE_ID && !idSet.has(record.parent_id)) {
                orphans.push(`Fish ${record.id} has parent ${record.parent_id} which doesn't exist`);
            }
        }

        // Log orphans if found
        if (orphans.length > 0) {
            const orphanPreview = orphans.slice(0, 3).join('; ');
            const detailSuffix = orphans.length > 3 ? ' (additional orphaned records omitted)' : '';

            return {
                tree: null,
                error: `Lineage data contains ${orphans.length} orphaned record(s): ${orphanPreview}${detailSuffix}`,
            };
        }

        // D3 Stratify converts flat list -> nested tree
        const strategy = stratify<FishRecord>()
            .id((d) => d.id)
            .parentId((d) => (d.id === ROOT_NODE_ID ? null : d.parent_id));

        // D3-stratify requires exactly one root node. We add an explicit root so
        // that multiple initial spawns share a common ancestor instead of causing
        // a "multiple roots" error.
        const rootNode: FishRecord = {
            id: ROOT_NODE_ID,
            parent_id: '',
            generation: 0,
            algorithm: 'Primordial Soup',
            color: '#00ff00',
            birth_time: 0,
        };

        const tree = strategy([rootNode, ...sanitizedData]);

        // React-D3-Tree expects a specific format (name, attributes, children)
        // We write a recursive mapper to convert the D3 node to the React component format
        const mapper = (node: HierarchyNode<FishRecord>): TreeNodeData => {
            return {
                name: `Gen ${node.data.generation}`,
                attributes: {
                    Algo: node.data.algorithm,
                    ID: node.data.id,
                    Gen: node.data.generation,
                    IsAlive: node.data.is_alive ?? false,
                    Tank: node.data.tank_name,
                },
                // Custom property to pass color to the renderer
                nodeColor: node.data.color,
                children: node.children ? node.children.map(mapper) : [],
            };
        };

        const result = mapper(tree);

        // Prune dead fish that have no children (dead-end branches)
        const prunedResult = pruneDeadLeaves(result, true);

        return { tree: prunedResult, error: null };
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Unknown lineage transform error';
        return { tree: null, error: `Failed to process lineage data: ${message}` };
    }
};
