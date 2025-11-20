import { stratify, type HierarchyNode } from 'd3-hierarchy';

export interface FishRecord {
  id: string;
  parent_id: string;
  algorithm: string;
  generation: number;
  color: string;
  birth_time?: number;
}

export interface TreeNodeData {
  name: string;
  attributes: {
    Algo: string;
    ID: string;
    Gen: number;
  };
  nodeColor: string;
  children: TreeNodeData[];
}

const ROOT_NODE_ID = 'root';

export const transformLineageData = (flatData: FishRecord[]): TreeNodeData | null => {
  if (!flatData || flatData.length === 0) {
    return null;
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
      console.error('Phylogenetic tree error: Found orphaned records:', orphans);
      console.error('Available IDs:', Array.from(idSet));
      console.error('Full data:', flatData);
      return null;
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
        },
        // Custom property to pass color to the renderer
        nodeColor: node.data.color,
        children: node.children ? node.children.map(mapper) : [],
      };
    };

    const result = mapper(tree);
    return result;
  } catch (error) {
    console.error('Phylogenetic tree error:', error);
    console.error('Data that caused error:', flatData);
    return null;
  }
};
