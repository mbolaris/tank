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
        /** Present on collapsed-chain summary nodes */
        IsCollapsedChain?: boolean;
        /** Number of hidden generations in this collapsed chain */
        ChainLength?: number;
        /** Human-readable generation range, e.g. "Gen 3→12" */
        GenRange?: string;
    };
    nodeColor: string;
    children: TreeNodeData[];
    /**
     * Chain continuation hidden behind a collapsed-chain summary node.
     *
     * react-d3-tree only walks `children`, so parking the chain here is what
     * actually hides it. Do NOT try to hide nodes with `__rd3t.collapsed`:
     * the library hard-assigns `__rd3t = {id, depth, collapsed: false}` to every
     * node in `assignInternalProperties` (both on mount and whenever the `data`
     * prop identity changes), so any preset value is discarded. `initialDepth`
     * is its only supported way to start collapsed, and that is depth-based.
     */
    hiddenChain?: TreeNodeData[];
}

const ROOT_NODE_ID = 'root';

export interface LineageTransformResult {
    tree: TreeNodeData | null;
    error: string | null;
}

export interface LineageTransformOptions {
    /**
     * Summary-node IDs the user has expanded. Chains listed here are left
     * intact instead of being collapsed, so expansions survive the periodic
     * lineage refetch.
     */
    expandedChainIds?: ReadonlySet<string>;
}

/**
 * Remove dead fish that have no children (dead-end branches).
 * This prunes the tree to only show lineages that have living descendants or contributed to them.
 * Uses iterative post-order traversal to avoid stack overflow on deep trees.
 */
const pruneDeadLeaves = (root: TreeNodeData, isRoot: boolean = false): TreeNodeData | null => {
    // Build post-order traversal list using a stack
    const stack: { node: TreeNodeData; isRoot: boolean }[] = [{ node: root, isRoot }];
    const postOrder: { node: TreeNodeData; isRoot: boolean }[] = [];

    while (stack.length > 0) {
        const entry = stack.pop()!;
        postOrder.push(entry);
        if (entry.node.children) {
            for (const child of entry.node.children) {
                stack.push({ node: child, isRoot: false });
            }
        }
    }

    // Track which nodes should be pruned (removed)
    const pruned = new Set<TreeNodeData>();

    // Process bottom-up
    for (let i = postOrder.length - 1; i >= 0; i--) {
        const { node, isRoot: nodeIsRoot } = postOrder[i];

        // Filter children: remove any that were pruned
        if (node.children && node.children.length > 0) {
            node.children = node.children.filter(child => !pruned.has(child));
        }

        // Keep root node always
        if (nodeIsRoot) continue;

        // Keep alive fish
        if (node.attributes.IsAlive) continue;

        // Keep dead fish that have children (they contributed to the lineage)
        if (node.children && node.children.length > 0) continue;

        // Mark dead fish with no children for removal (dead-end branches)
        pruned.add(node);
    }

    // If root itself was pruned (shouldn't happen since we always keep root)
    return pruned.has(root) ? null : root;
};

export const transformLineageData = (
    flatData: FishRecord[],
    options: LineageTransformOptions = {},
): LineageTransformResult => {
    if (!flatData || flatData.length === 0) {
        return { tree: null, error: null };
    }

    try {
        // Validate data structure before stratifying
        const uniqueDataMap = new Map<string, FishRecord>();
        const sanitizedData = flatData.map((record) => ({
            ...record,
            // Normalize any null/undefined parents to the root node
            parent_id: record.parent_id ?? ROOT_NODE_ID,
        }));

        // Deduplicate by ID, preferring records with higher generation or later birth time
        for (const record of sanitizedData) {
            const existing = uniqueDataMap.get(record.id);
            if (!existing) {
                uniqueDataMap.set(record.id, record);
            } else {
                // Collision detected: determine which one to keep
                // Logic: Keep the one with higher generation (likely newer)
                // If generations equal, keep the one appearing later in the list (newest)
                if ((record.generation || 0) > (existing.generation || 0)) {
                    uniqueDataMap.set(record.id, record);
                }
                // Else keep existing
                console.warn(`Lineage: Duplicate ID ${record.id} detected. Keeping Gen ${uniqueDataMap.get(record.id)?.generation}.`);
            }
        }

        const uniqueData = Array.from(uniqueDataMap.values());

        const orphans: string[] = [];
        const idSet = new Set([...uniqueData.map((d) => d.id), ROOT_NODE_ID]);

        for (const record of uniqueData) {
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

        const tree = strategy([rootNode, ...uniqueData]);

        // React-D3-Tree expects a specific format (name, attributes, children)
        // Iterative mapper to convert D3 hierarchy nodes to TreeNodeData format
        // (avoids stack overflow on deep lineage trees)
        const mapIterative = (root: HierarchyNode<FishRecord>): TreeNodeData => {
            type StackEntry = {
                d3Node: HierarchyNode<FishRecord>;
                treeNode: TreeNodeData;
            };

            const rootTreeNode: TreeNodeData = {
                name: `Gen ${root.data.generation}`,
                attributes: {
                    Algo: root.data.algorithm,
                    ID: root.data.id,
                    Gen: root.data.generation,
                    IsAlive: root.data.is_alive ?? false,
                    Tank: root.data.tank_name,
                },
                nodeColor: root.data.color,
                children: [],
            };

            const stack: StackEntry[] = [{ d3Node: root, treeNode: rootTreeNode }];

            while (stack.length > 0) {
                const { d3Node, treeNode } = stack.pop()!;
                if (d3Node.children) {
                    for (const child of d3Node.children) {
                        const childTreeNode: TreeNodeData = {
                            name: `Gen ${child.data.generation}`,
                            attributes: {
                                Algo: child.data.algorithm,
                                ID: child.data.id,
                                Gen: child.data.generation,
                                IsAlive: child.data.is_alive ?? false,
                                Tank: child.data.tank_name,
                            },
                            nodeColor: child.data.color,
                            children: [],
                        };
                        treeNode.children.push(childTreeNode);
                        stack.push({ d3Node: child, treeNode: childTreeNode });
                    }
                }
            }

            return rootTreeNode;
        };

        const result = mapIterative(tree);

        // Prune dead fish that have no children (dead-end branches)
        const prunedResult = pruneDeadLeaves(result, true);

        // Compress straight dead lineages with same behavior
        const compressedResult = compressLineageTree(prunedResult);

        // Auto-collapse long chains so the tree starts compact
        const collapsedResult = collapseLongChains(
            compressedResult,
            DEFAULT_MAX_CHAIN_LENGTH,
            options.expandedChainIds,
        );

        return { tree: collapsedResult, error: null };
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Unknown lineage transform error';
        return { tree: null, error: `Failed to process lineage data: ${message}` };
    }
};

/**
 * Recursively compress straight path segments with the same algorithm and dead intermediate nodes.
 * Uses a stack-based iterative approach to avoid call-stack overflow on deep lineage chains.
 */
export const compressLineageTree = (root: TreeNodeData | null): TreeNodeData | null => {
    if (!root) return null;

    // Process tree bottom-up using an iterative post-order traversal.
    // This avoids the recursive call that caused "Maximum call stack size exceeded"
    // on long chains of dead single-child nodes with the same algorithm.
    const stack: TreeNodeData[] = [root];
    const postOrder: TreeNodeData[] = [];

    // Build post-order list (children processed before parents)
    while (stack.length > 0) {
        const node = stack.pop()!;
        postOrder.push(node);
        if (node.children) {
            for (const child of node.children) {
                stack.push(child);
            }
        }
    }

    // Process in reverse (bottom-up) so children are compressed before their parents
    for (let i = postOrder.length - 1; i >= 0; i--) {
        const node = postOrder[i];

        // Filter out null children (from pruning)
        if (node.children && node.children.length > 0) {
            node.children = node.children.filter(
                (child): child is TreeNodeData => child !== null
            );
        }

        // Iteratively bypass single dead children with the same algorithm
        while (
            node.children &&
            node.children.length === 1 &&
            node.children[0].attributes.Algo === node.attributes.Algo &&
            !node.children[0].attributes.IsAlive
        ) {
            // Bypass child by inheriting its children
            node.children = node.children[0].children;
        }
    }

    return root;
};

export const DEFAULT_MAX_CHAIN_LENGTH = 5;

/** Stable id for the summary node standing in for a hidden chain. */
export const chainSummaryId = (firstHiddenId: string, lastHiddenId: string): string =>
    `chain_${firstHiddenId}_to_${lastHiddenId}`;

/**
 * Auto-collapse long single-child chains into summary nodes.
 *
 * Any unbroken single-child chain longer than `maxChainLength` gets a summary
 * node spliced in after the first node. The chain itself moves off `children`
 * and onto the summary's `hiddenChain`, which is what actually hides it —
 * react-d3-tree only renders `children`. The user sees a compact
 * "N generations" pill and clicking it restores the chain (see
 * `expandedChainIds`).
 *
 * Chains whose summary id appears in `expandedChainIds` are left intact, so a
 * user's expansions survive the periodic lineage refetch.
 *
 * Uses iterative DFS to avoid stack overflow on deep trees.
 */
export const collapseLongChains = (
    root: TreeNodeData | null,
    maxChainLength: number = DEFAULT_MAX_CHAIN_LENGTH,
    expandedChainIds?: ReadonlySet<string>,
): TreeNodeData | null => {
    if (!root) return null;

    // Iterative DFS — process each node and look for chain starts
    const stack: TreeNodeData[] = [root];

    while (stack.length > 0) {
        const node = stack.pop()!;

        // Only interested in nodes that start a single-child chain
        if (!node.children || node.children.length !== 1) {
            // Not a chain — push multi-child branches for further processing
            if (node.children) {
                for (const child of node.children) {
                    stack.push(child);
                }
            }
            continue;
        }

        // Walk the single-child chain to measure its length
        const chain: TreeNodeData[] = [node];
        let cursor: TreeNodeData = node;
        while (cursor.children?.length === 1) {
            chain.push(cursor.children[0]);
            cursor = cursor.children[0];
        }

        const firstNode = chain[0];
        const secondNode = chain[1];
        const tailNode = chain[chain.length - 1]; // has 0 or 2+ children

        // Only chains longer than the threshold get a summary node. `chain` is
        // then at least 6 long, so chain[length - 2] is a genuine hidden node.
        const summaryId =
            chain.length > maxChainLength
                ? chainSummaryId(
                      secondNode.attributes.ID,
                      chain[chain.length - 2].attributes.ID,
                  )
                : null;

        // Leave the chain intact when it is short enough, or when the user has
        // already expanded this exact chain.
        if (summaryId === null || expandedChainIds?.has(summaryId)) {
            // Still need to process any branching at the tail
            if (tailNode.children) {
                for (const child of tailNode.children) {
                    stack.push(child);
                }
            }
            continue;
        }

        // --- Chain is too long: splice in a summary node that hides it ---
        const collapsedCount = chain.length - 1; // nodes hidden behind summary

        const summaryNode: TreeNodeData = {
            name: `${collapsedCount} gen`,
            attributes: {
                Algo: '⋯ chain',
                ID: summaryId,
                Gen: secondNode.attributes.Gen,
                IsAlive: false,
                IsCollapsedChain: true,
                ChainLength: collapsedCount,
                GenRange: `Gen ${secondNode.attributes.Gen} → ${tailNode.attributes.Gen}`,
            },
            nodeColor: '#475569',
            // Empty `children` is what hides the chain; the continuation is
            // parked on `hiddenChain` for the expand handler to restore.
            children: [],
            hiddenChain: [secondNode],
        };

        // Splice the summary in: firstNode → summaryNode ⇢ (hidden chain)
        firstNode.children = [summaryNode];

        // Continue processing the tail's branches (they're hidden but should
        // still be processed in case they themselves contain long chains)
        if (tailNode.children) {
            for (const child of tailNode.children) {
                stack.push(child);
            }
        }
    }

    return root;
};
