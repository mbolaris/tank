import React, { useEffect, useRef, useState, useCallback } from 'react';
import Tree, { type CustomNodeElementProps } from 'react-d3-tree';
import { transformLineageData } from '../utils/lineageUtils';
import type { FishRecord, TreeNodeData, LineageTransformResult } from '../utils/lineageUtils';
import { config } from '../config';
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

interface PhylogeneticTreeProps {
    worldId?: string;
}

/**
 * Read the actual rendered SVG node positions from the DOM.
 * Each node is in a <g> with a transform like "translate(x,y)".
 * Returns the bounding box in the tree's coordinate system.
 */
function readSvgNodeBounds(containerEl: HTMLDivElement): {
    minX: number; maxX: number; minY: number; maxY: number;
    width: number; height: number; centerX: number; centerY: number;
    nodeCount: number;
} | null {
    // react-d3-tree renders nodes as <g class="rd3t-node"> or <g class="rd3t-leaf-node">
    const nodeGroups = containerEl.querySelectorAll<SVGGElement>('g.rd3t-node, g.rd3t-leaf-node');
    if (nodeGroups.length === 0) return null;

    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;

    const CARD_HALF_W = 120; // account for node card width (foreignObject extends ~200px right of center)
    const CARD_HALF_H = 50;  // account for node card height

    for (const g of nodeGroups) {
        const transform = g.getAttribute('transform');
        if (!transform) continue;
        const match = transform.match(/translate\(\s*([-\d.e+]+)\s*,\s*([-\d.e+]+)\s*\)/);
        if (!match) continue;
        const nx = parseFloat(match[1]);
        const ny = parseFloat(match[2]);

        if (nx - CARD_HALF_W < minX) minX = nx - CARD_HALF_W;
        if (nx + CARD_HALF_W + 180 > maxX) maxX = nx + CARD_HALF_W + 180; // foreignObject extends 180px right
        if (ny - CARD_HALF_H < minY) minY = ny - CARD_HALF_H;
        if (ny + CARD_HALF_H > maxY) maxY = ny + CARD_HALF_H;
    }

    if (!isFinite(minX)) return null;

    const width = Math.max(100, maxX - minX);
    const height = Math.max(100, maxY - minY);
    return {
        minX, maxX, minY, maxY, width, height,
        centerX: (minX + maxX) / 2,
        centerY: (minY + maxY) / 2,
        nodeCount: nodeGroups.length,
    };
}


export const PhylogeneticTree: React.FC<PhylogeneticTreeProps> = ({ worldId }) => {
    const [treeData, setTreeData] = useState<TreeNodeData | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const containerRef = useRef<HTMLDivElement | null>(null);
    const [translate, setTranslate] = useState<{ x: number; y: number }>({ x: 400, y: 60 });
    const [zoom, setZoom] = useState<number>(0.75);
    const hasInitializedView = useRef<boolean>(false);
    // Incrementing key forces <Tree> to re-mount with fresh translate/zoom
    const [treeKey, setTreeKey] = useState<number>(0);

    /**
     * Fit the tree into the viewport by reading actual rendered SVG positions.
     * Because react-d3-tree only reads translate/zoom as initial values,
     * we bump treeKey to force a full re-mount with the computed values.
     */
    const fitTreeToView = useCallback((_dataToFit?: TreeNodeData | null, mode: 'leaves' | 'fit' | 'root' = 'fit') => {
        if (!containerRef.current) return;

        const rect = containerRef.current.getBoundingClientRect();
        const containerW = rect.width || 800;
        const containerH = rect.height || 600;

        const bbox = readSvgNodeBounds(containerRef.current);
        if (!bbox) {
            // Fallback: just center root
            setTranslate({ x: containerW / 2, y: 60 });
            setZoom(0.5);
            setTreeKey(k => k + 1);
            return;
        }

        const PADDING = 60;
        const availableW = Math.max(200, containerW - PADDING * 2);
        const availableH = Math.max(200, containerH - PADDING * 2);

        const scaleX = availableW / bbox.width;
        const scaleY = availableH / bbox.height;
        let targetZoom = Math.min(scaleX, scaleY);
        targetZoom = Math.min(1.5, Math.max(0.01, targetZoom));

        // Center the bounding box in the container
        let tx = containerW / 2 - bbox.centerX * targetZoom;
        let ty = containerH / 2 - bbox.centerY * targetZoom;

        if (mode === 'leaves') {
            // Push leaves toward the bottom of the viewport
            const leafScreenY = bbox.maxY * targetZoom;
            const desiredTy = containerH - 80 - leafScreenY;
            ty = Math.min(60, desiredTy);
        } else if (mode === 'root') {
            // Push root toward the top of the viewport
            const rootScreenY = bbox.minY * targetZoom;
            ty = 60 - rootScreenY;
        }

        setTranslate({ x: tx, y: ty });
        setZoom(targetZoom);
        // Force re-mount so <Tree> picks up the new translate/zoom as initial values
        setTreeKey(k => k + 1);
    }, []);

    const fetchLineage = async () => {
        if (!worldId) {
            setError('Waiting for world connection...');
            setLoading(false);
            return;
        }

        try {
            setLoading(true);
            setError(null);

            const lineageUrl = `${config.apiBaseUrl}/api/worlds/${worldId}/lineage`;
            const response = await fetch(lineageUrl);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data: FishRecord[] = await response.json();

            if (data && data.length > 0) {
                const { tree, error: lineageError }: LineageTransformResult = transformLineageData(data);
                if (lineageError) {
                    setTreeData(null);
                    setError(lineageError);
                } else if (tree) {
                    setTreeData(tree);
                    setError(null);

                    if (!hasInitializedView.current) {
                        hasInitializedView.current = true;
                        // Wait for react-d3-tree to render nodes into the DOM, then fit
                        setTimeout(() => {
                            if (containerRef.current) {
                                fitTreeToView(tree, 'fit');
                            }
                        }, 300);
                    }
                } else {
                    setTreeData(null);
                    setError(`Failed to build phylogenetic tree from ${data.length} lineage records.`);
                }
            } else {
                setTreeData(null);
                setError('No lineage data available yet. Fish need to reproduce to build the tree.');
            }

            setLoading(false);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load lineage data');
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLineage();
        const interval = setInterval(fetchLineage, 10000);
        return () => clearInterval(interval);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [worldId]);

    // Custom node renderer to color-code by fish color
    const renderCustomNode = ({ nodeDatum, toggleNode }: CustomNodeElementProps) => {
        const treeNode = nodeDatum as unknown as TreeNodeData;

        // --- Collapsed-chain summary node ---
        if (treeNode.attributes?.IsCollapsedChain) {
            const pillWidth = 190;
            const pillHeight = 52;
            const chainLength = treeNode.attributes.ChainLength ?? 0;
            const genRange = treeNode.attributes.GenRange ?? '';
            return (
                <g onClick={toggleNode} style={{ cursor: 'pointer' }} className="chain-summary-node">
                    <rect
                        x={-pillWidth / 2}
                        y={-pillHeight / 2}
                        width={pillWidth}
                        height={pillHeight}
                        rx={pillHeight / 2}
                        ry={pillHeight / 2}
                        fill="rgba(30, 41, 59, 0.95)"
                        stroke="#8b5cf6"
                        strokeWidth="1.5"
                        strokeDasharray="6 3"
                        className="chain-summary-pill"
                    />
                    <text
                        textAnchor="middle"
                        y={-6}
                        style={{
                            fontSize: '13px',
                            fontWeight: 600,
                            fill: '#c4b5fd',
                            fontFamily: 'Inter, system-ui, sans-serif',
                            pointerEvents: 'none',
                        }}
                    >
                        🔗 {chainLength} generations
                    </text>
                    <text
                        textAnchor="middle"
                        y={14}
                        style={{
                            fontSize: '11px',
                            fill: '#94a3b8',
                            fontFamily: 'Inter, system-ui, sans-serif',
                            pointerEvents: 'none',
                        }}
                    >
                        {genRange} · click to expand
                    </text>
                </g>
            );
        }

        // --- Regular fish node ---
        const labelWidth = 180;
        const labelHeight = 72;
        const tankName = treeNode.attributes?.Tank;
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
                            paddingLeft: '10px',
                            paddingRight: '8px',
                            boxSizing: 'border-box',
                            fontFamily: 'Inter, system-ui, sans-serif',
                        }}
                    >
                        <div
                            style={{
                                color: '#f1f5f9',
                                fontSize: '14px',
                                fontWeight: 600,
                                lineHeight: '1.2',
                                marginBottom: '3px',
                            }}
                        >
                            {treeNode.attributes?.Algo || 'Unknown'}
                        </div>
                        <div
                            style={{
                                color: '#cbd5e1',
                                fontSize: '12px',
                                lineHeight: '1.2',
                            }}
                        >
                            ID: {treeNode.attributes?.ID}
                        </div>
                        {tankName && (
                            <div
                                style={{
                                    color: '#22d3ee',
                                    fontSize: '11px',
                                    lineHeight: '1.2',
                                    marginTop: '2px',
                                }}
                            >
                                📍 {tankName}
                            </div>
                        )}
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
            {/* Tree Controls Overlay */}
            <div className="tree-controls-overlay">
                <button
                    type="button"
                    className="tree-control-btn"
                    onClick={() => fitTreeToView(treeData, 'leaves')}
                    title="Position view to focus living leaf nodes at the bottom"
                >
                    🍃 Focus Leaves
                </button>
                <button
                    type="button"
                    className="tree-control-btn"
                    onClick={() => fitTreeToView(treeData, 'fit')}
                    title="Fit entire tree into viewport"
                >
                    📐 Fit Tree
                </button>
                <button
                    type="button"
                    className="tree-control-btn"
                    onClick={() => fitTreeToView(treeData, 'root')}
                    title="Position view at ancestor root node"
                >
                    🌱 Focus Root
                </button>
            </div>

            <Tree
                key={treeKey}
                data={treeData}
                orientation="vertical"
                pathFunc="step"
                renderCustomNodeElement={renderCustomNode}
                translate={translate}
                zoom={zoom}
                zoomable={true}
                collapsible={true}
                nodeSize={{ x: 250, y: 160 }}
                separation={{ siblings: 1.2, nonSiblings: 1.3 }}
                scaleExtent={{ min: 0.01, max: 3.0 }}
            />
        </div>
    );
};
