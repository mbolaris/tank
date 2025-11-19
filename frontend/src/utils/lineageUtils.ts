import { stratify } from 'd3-hierarchy';

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

export const transformLineageData = (flatData: FishRecord[]): TreeNodeData | null => {
  if (!flatData || flatData.length === 0) {
    console.log('[lineageUtils] No data provided or empty array');
    return null;
  }

  console.log('[lineageUtils] Processing lineage data:', {
    totalRecords: flatData.length,
    sampleRecords: flatData.slice(0, 3),
    uniqueIds: new Set(flatData.map(d => d.id)).size,
    uniqueParentIds: new Set(flatData.map(d => d.parent_id)).size,
  });

  try {
    // Validate data structure before stratifying
    const orphans: string[] = [];
    const idSet = new Set(flatData.map(d => d.id));

    for (const record of flatData) {
      if (record.parent_id !== 'root' && !idSet.has(record.parent_id)) {
        orphans.push(`Fish ${record.id} has parent ${record.parent_id} which doesn't exist`);
      }
    }

    if (orphans.length > 0) {
      console.error('[lineageUtils] Found orphan nodes:', orphans);
      console.error('[lineageUtils] All IDs:', Array.from(idSet).sort());
      console.error('[lineageUtils] All parent IDs:', flatData.map(d => d.parent_id).sort());
      // Still try to build tree, but it will likely fail
    }

    // D3 Stratify converts flat list -> nested tree
    const strategy = stratify<FishRecord>()
      .id((d) => d.id)
      .parentId((d) => d.parent_id === "root" ? null : d.parent_id);

    const tree = strategy(flatData);
    console.log('[lineageUtils] Successfully stratified data into tree');

    // React-D3-Tree expects a specific format (name, attributes, children)
    // We write a recursive mapper to convert the D3 node to the React component format
    const mapper = (node: any): TreeNodeData => {
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
    console.log('[lineageUtils] Successfully transformed tree');
    return result;
  } catch (error) {
    console.error("[lineageUtils] Lineage parsing error:", error);
    console.error("[lineageUtils] Error details:", {
      message: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
    });
    return null;
  }
};
