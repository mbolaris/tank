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
});
