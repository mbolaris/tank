import { describe, it, expect } from 'vitest';
import { transformLineageData, type FishRecord } from './lineageUtils';

describe('lineageUtils', () => {
    it('should handle empty lineage data', () => {
        const result = transformLineageData([]);
        expect(result.tree).toBeNull();
        expect(result.error).toBeNull();
    });

    it('should build a basic tree and prune dead-end branches', () => {
        const flatData: FishRecord[] = [
            { id: '1', parent_id: 'root', generation: 1, algorithm: 'AlgoA', color: '#ff0000', is_alive: false },
            { id: '2', parent_id: '1', generation: 2, algorithm: 'AlgoA', color: '#ff0000', is_alive: true },
            { id: '3', parent_id: '1', generation: 2, algorithm: 'AlgoA', color: '#ff0000', is_alive: false }, // Should be pruned (dead, no children)
        ];

        const { tree, error } = transformLineageData(flatData);
        expect(error).toBeNull();
        expect(tree).toBeDefined();
        expect(tree?.name).toBe('Gen 0'); // Root node
        expect(tree?.children.length).toBe(1); // '1' is kept because it has alive child '2'

        const child1 = tree?.children[0];
        expect(child1?.attributes.ID).toBe('1');
        expect(child1?.children.length).toBe(1); // '2' is kept, '3' is pruned

        const child2 = child1?.children[0];
        expect(child2?.attributes.ID).toBe('2');
        expect(child2?.children.length).toBe(0);
    });

    it('should compress straight lineage segments with the same algorithm', () => {
        const flatData: FishRecord[] = [
            { id: '1', parent_id: 'root', generation: 1, algorithm: 'AlgoA', color: '#ff0000', is_alive: false },
            { id: '2', parent_id: '1', generation: 2, algorithm: 'AlgoA', color: '#ff0000', is_alive: false }, // dead, same algo
            { id: '3', parent_id: '2', generation: 3, algorithm: 'AlgoA', color: '#ff0000', is_alive: false }, // dead, same algo
            { id: '4', parent_id: '3', generation: 4, algorithm: 'AlgoA', color: '#ff0000', is_alive: true },  // alive, same algo
        ];

        const { tree, error } = transformLineageData(flatData);
        expect(error).toBeNull();
        expect(tree?.children.length).toBe(1);

        // Child '1' should connect directly to '4' because '2' and '3' are dead and share the same algorithm
        const child1 = tree?.children[0];
        expect(child1?.attributes.ID).toBe('1');
        expect(child1?.children.length).toBe(1);

        const child4 = child1?.children[0];
        expect(child4?.attributes.ID).toBe('4');
        expect(child4?.attributes.IsAlive).toBe(true);
        expect(child4?.children.length).toBe(0);
    });

    it('should NOT compress segments if the algorithm changes', () => {
        const flatData: FishRecord[] = [
            { id: '1', parent_id: 'root', generation: 1, algorithm: 'AlgoA', color: '#ff0000', is_alive: false },
            { id: '2', parent_id: '1', generation: 2, algorithm: 'AlgoB', color: '#00ff00', is_alive: false }, // dead, DIFFERENT algo!
            { id: '3', parent_id: '2', generation: 3, algorithm: 'AlgoB', color: '#00ff00', is_alive: true },  // alive, same algo as 2
        ];

        const { tree, error } = transformLineageData(flatData);
        expect(error).toBeNull();

        const child1 = tree?.children[0];
        expect(child1?.attributes.ID).toBe('1');
        expect(child1?.children.length).toBe(1);

        const child2 = child1?.children[0];
        expect(child2?.attributes.ID).toBe('2'); // NOT compressed/bypassed!
        expect(child2?.children.length).toBe(1);

        const child3 = child2?.children[0];
        expect(child3?.attributes.ID).toBe('3');
    });

    it('should handle deep lineage chains without stack overflow', () => {
        // This is a regression test for the "Maximum call stack size exceeded" bug.
        // The old recursive compressLineageTree would overflow on chains this deep.
        const depth = 5000;
        const flatData: FishRecord[] = [];

        // Build a single deep chain: root -> 1 -> 2 -> ... -> depth
        for (let i = 1; i <= depth; i++) {
            flatData.push({
                id: String(i),
                parent_id: i === 1 ? 'root' : String(i - 1),
                generation: i,
                algorithm: 'AlgoA', // Same algo throughout — triggers compression
                color: '#ff0000',
                is_alive: i === depth, // Only the last node is alive
            });
        }

        // This should NOT throw "Maximum call stack size exceeded"
        const { tree, error } = transformLineageData(flatData);
        expect(error).toBeNull();
        expect(tree).toBeDefined();

        // The chain should be compressed: root -> 1 -> depth (all intermediates bypassed)
        const child1 = tree?.children[0];
        expect(child1?.attributes.ID).toBe('1');
        expect(child1?.children.length).toBe(1);

        const lastChild = child1?.children[0];
        expect(lastChild?.attributes.ID).toBe(String(depth));
        expect(lastChild?.attributes.IsAlive).toBe(true);
    });

    it('should auto-collapse long chains with a summary node', () => {
        // Build a chain of 8 nodes with different algorithms (so compression doesn't remove them)
        const flatData: FishRecord[] = [];
        for (let i = 1; i <= 8; i++) {
            flatData.push({
                id: String(i),
                parent_id: i === 1 ? 'root' : String(i - 1),
                generation: i,
                algorithm: `Algo${i}`, // Different algos → no compression
                color: '#ff0000',
                is_alive: true, // All alive → no pruning
            });
        }

        const { tree, error } = transformLineageData(flatData);
        expect(error).toBeNull();
        expect(tree).toBeDefined();

        // root → summaryNode(collapsed) → (hidden: 1→2→...→8)
        // The chain starts at root (which has 1 child), so root's first child is the summary
        const summary = tree?.children[0];
        expect(summary?.attributes.IsCollapsedChain).toBe(true);
        expect(summary?.attributes.ChainLength).toBeGreaterThan(0);
        expect(summary?.attributes.GenRange).toBeDefined();
        expect(summary?.__rd3t?.collapsed).toBe(true);

        // The summary's children should contain the hidden chain starting at node '1'
        expect(summary?.children.length).toBe(1);
        expect(summary?.children[0].attributes.ID).toBe('1');
    });

    it('should NOT collapse short chains (at or below threshold)', () => {
        // Build a chain of exactly 4 nodes (below default threshold of 5)
        const flatData: FishRecord[] = [];
        for (let i = 1; i <= 4; i++) {
            flatData.push({
                id: String(i),
                parent_id: i === 1 ? 'root' : String(i - 1),
                generation: i,
                algorithm: `Algo${i}`, // Different algos → no compression
                color: '#ff0000',
                is_alive: true,
            });
        }

        const { tree, error } = transformLineageData(flatData);
        expect(error).toBeNull();

        // No summary nodes should be present anywhere in this short chain
        const child1 = tree?.children[0];
        expect(child1?.attributes.IsCollapsedChain).toBeUndefined();
        expect(child1?.attributes.ID).toBe('1');

        const child2 = child1?.children[0];
        expect(child2?.attributes.IsCollapsedChain).toBeUndefined();
        expect(child2?.attributes.ID).toBe('2');
    });
});
