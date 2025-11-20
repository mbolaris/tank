import React, { useEffect, useRef, useState } from 'react';
import Tree, { type CustomNodeElementProps } from 'react-d3-tree';
import { transformLineageData } from '../utils/lineageUtils';
import type { FishRecord, TreeNodeData } from '../utils/lineageUtils';
import './PhylogeneticTree.css';

const containerStyles: React.CSSProperties = {
    width: '100%',
    height: '600px',
    background: 'linear-gradient(180deg, #0b1221 0%, #0f172a 100%)',
    borderRadius: '12px',
    border: '1px solid #1f2a44',
    position: 'relative',
    overflow: 'hidden',
    boxShadow: '0 20px 50px rgba(0, 0, 0, 0.4)',
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
    const containerRef = useRef<HTMLDivElement | null>(null);
    const [translate, setTranslate] = useState<{ x: number; y: number }>({ x: 400, y: 60 });

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

    useEffect(() => {
        const updateTranslate = () => {
            const rect = containerRef.current?.getBoundingClientRect();
            if (rect) {
                setTranslate({ x: rect.width / 2, y: 70 });
            }
        };

        updateTranslate();
        window.addEventListener('resize', updateTranslate);
        return () => window.removeEventListener('resize', updateTranslate);
    }, []);

    // Custom node renderer to color-code by fish color
    const renderCustomNode = ({ nodeDatum, toggleNode }: CustomNodeElementProps) => {
        const treeNode = nodeDatum as unknown as TreeNodeData;
        const labelWidth = 200;
        const labelHeight = 68;
        return (
            <g>
                <circle
                    r={14}
                    fill={treeNode.nodeColor || '#34d399'}
                    stroke="#fff"
                    strokeWidth="2"
                    onClick={toggleNode}
                    style={{ cursor: 'pointer' }}
                />
                <foreignObject x={22} y={-labelHeight / 2} width={labelWidth} height={labelHeight}>
                    <div
                        style={{
                            width: '100%',
                            height: '100%',
                            backgroundColor: 'rgba(15, 23, 42, 0.95)',
                            border: '1.5px solid #22d3ee',
                            borderRadius: '8px',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'center',
                            paddingLeft: '12px',
                            boxSizing: 'border-box',
                            fontFamily: 'Inter, system-ui, sans-serif',
                        }}
                    >
                        <div
                            style={{
                                color: '#f1f5f9',
                                fontSize: '16px',
                                fontWeight: 600,
                                lineHeight: '1.2',
                                marginBottom: '4px',
                            }}
                        >
                            {treeNode.attributes?.Algo || 'Unknown algo'}
                        </div>
                        <div
                            style={{
                                color: '#cbd5e1',
                                fontSize: '13px',
                                lineHeight: '1.2',
                            }}
                        >
                            ID: {treeNode.attributes?.ID}
                        </div>
                    </div>
                </foreignObject>
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
        <div style={containerStyles} ref={containerRef}>
            <Tree
                data={treeData}
                orientation="vertical"
                pathFunc="step" // Looks more like a circuit board/tech tree
                renderCustomNodeElement={renderCustomNode}
                translate={translate} // Start in top center
                zoomable={true}
                collapsible={true}
                nodeSize={{ x: 250, y: 160 }}
                separation={{ siblings: 1.2, nonSiblings: 1.3 }}
                scaleExtent={{ min: 0.25, max: 2.5 }}
            />
        </div>
    );
};
