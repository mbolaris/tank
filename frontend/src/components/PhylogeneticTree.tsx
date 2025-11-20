import React, { useEffect, useState } from 'react';
import Tree, { type CustomNodeElementProps } from 'react-d3-tree';
import { transformLineageData } from '../utils/lineageUtils';
import type { FishRecord, TreeNodeData } from '../utils/lineageUtils';

const containerStyles: React.CSSProperties = {
  width: '100%',
  height: '600px',
  background: '#1a1a1a', // Dark background for "Lab" feel
  borderRadius: '8px',
  border: '1px solid #333',
  position: 'relative',
};

const loadingStyles: React.CSSProperties = {
  color: '#00ff00',
  textAlign: 'center',
  padding: '20px',
  fontSize: '18px',
};

export const PhylogeneticTree: React.FC = () => {
  const [treeData, setTreeData] = useState<TreeNodeData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLineage = async () => {
    try {
      setLoading(true);
      setError(null);

      // Replace with your actual API URL
      const response = await fetch('http://localhost:8000/api/lineage');

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: FishRecord[] = await response.json();

      if (data && data.length > 0) {
        const nestedData = transformLineageData(data);
        if (nestedData) {
          setTreeData(nestedData);
          setError(null);  // Clear any previous errors
        } else {
          setError(`Failed to build phylogenetic tree from ${data.length} lineage records.`);
        }
      } else {
        setError('No lineage data available yet. Fish need to reproduce to build the tree.');
      }

      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load lineage data');
      setLoading(false);
    }
  };

  // Refresh data every 10 seconds (or trigger manually)
  useEffect(() => {
    fetchLineage();
    const interval = setInterval(fetchLineage, 10000);
    return () => clearInterval(interval);
  }, []);

  // Custom node renderer to color-code by fish color
  const renderCustomNode = ({ nodeDatum, toggleNode }: CustomNodeElementProps) => {
    const treeNode = nodeDatum as unknown as TreeNodeData;
    return (
      <g>
        <circle
          r={10}
          fill={treeNode.nodeColor || "#00ff00"}
          stroke="#fff"
          strokeWidth="1"
          onClick={toggleNode}
          style={{ cursor: 'pointer' }}
        />
        <text
          fill="white"
          x="15"
          dy=".31em"
          fontSize="12px"
          style={{ pointerEvents: 'none' }}
        >
          {treeNode.attributes?.Algo}
        </text>
        <text
          fill="#888"
          x="15"
          dy="1.5em"
          fontSize="10px"
          style={{ pointerEvents: 'none' }}
        >
          ID: {treeNode.attributes?.ID}
        </text>
      </g>
    );
  };

  if (loading && !treeData) {
    return (
      <div style={containerStyles}>
        <div style={loadingStyles}>Loading evolution data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={containerStyles}>
        <div style={{ ...loadingStyles, color: '#ff6b6b' }}>{error}</div>
      </div>
    );
  }

  if (!treeData) {
    return (
      <div style={containerStyles}>
        <div style={loadingStyles}>Waiting for evolution data...</div>
      </div>
    );
  }

  return (
    <div style={containerStyles}>
      <Tree
        data={treeData}
        orientation="vertical"
        pathFunc="step" // Looks more like a circuit board/tech tree
        renderCustomNodeElement={renderCustomNode}
        translate={{ x: 400, y: 50 }} // Start in top center
        zoomable={true}
        collapsible={true}
        nodeSize={{ x: 200, y: 100 }}
        separation={{ siblings: 1, nonSiblings: 1.5 }}
      />
    </div>
  );
};
