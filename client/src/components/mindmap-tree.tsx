import React, { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ZoomIn, ZoomOut, Maximize2, Download } from "lucide-react";
import { Button } from "@/components/ui/button";

interface MindmapNode {
  label: string;
  children: MindmapNode[];
}

interface Position {
  x: number;
  y: number;
}

interface RenderedNode {
  node: MindmapNode;
  x: number;
  y: number;
  depth: number;
  expanded: boolean;
  children: RenderedNode[];
}

// Color palette for different depth levels
const DEPTH_COLORS = [
  "bg-violet-500 text-white",
  "bg-blue-500 text-white",
  "bg-cyan-500 text-white",
  "bg-teal-500 text-white",
  "bg-emerald-500 text-white",
  "bg-amber-500 text-white",
  "bg-rose-500 text-white",
];

const STROKE_COLORS = [
  "#8b5cf6",
  "#3b82f6",
  "#06b6d4",
  "#14b8a6",
  "#10b981",
  "#f59e0b",
  "#f43f5e",
];

interface MindmapTreeProps {
  data: MindmapNode;
}

export function MindmapTree({ data }: MindmapTreeProps) {
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState<Position>({ x: 50, y: 300 });
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set(["root"]));
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState<Position>({ x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Calculate tree layout
  const NODE_WIDTH = 180;
  const NODE_HEIGHT = 50;
  const HORIZONTAL_SPACING = 220;
  const VERTICAL_SPACING = 70;

  const getNodeId = (path: string[]) => path.join("-") || "root";

  const calculateTreeLayout = useCallback(
    (node: MindmapNode, depth: number, path: string[]): RenderedNode => {
      const nodeId = getNodeId(path);
      const isExpanded = expandedNodes.has(nodeId);

      const renderedNode: RenderedNode = {
        node,
        x: depth * HORIZONTAL_SPACING,
        y: 0, // Will be calculated after counting children
        depth,
        expanded: isExpanded,
        children: [],
      };

      if (isExpanded && node.children.length > 0) {
        renderedNode.children = node.children.map((child, index) =>
          calculateTreeLayout(child, depth + 1, [...path, String(index)])
        );
      }

      return renderedNode;
    },
    [expandedNodes]
  );

  // Calculate Y positions based on leaf count
  const assignYPositions = useCallback(
    (renderedNode: RenderedNode, startY: number): number => {
      if (renderedNode.children.length === 0) {
        renderedNode.y = startY;
        return startY + VERTICAL_SPACING;
      }

      let currentY = startY;
      for (const child of renderedNode.children) {
        currentY = assignYPositions(child, currentY);
      }

      // Center parent vertically among children
      const firstChild = renderedNode.children[0];
      const lastChild = renderedNode.children[renderedNode.children.length - 1];
      renderedNode.y = (firstChild.y + lastChild.y) / 2;

      return currentY;
    },
    []
  );

  const treeLayout = calculateTreeLayout(data, 0, []);
  assignYPositions(treeLayout, 100);

  // Calculate SVG bounds
  const getMaxX = (node: RenderedNode): number => {
    const childMaxX = node.children.length > 0 ? Math.max(...node.children.map(getMaxX)) : node.x;
    return Math.max(node.x, childMaxX);
  };

  const getMaxY = (node: RenderedNode): number => {
    const childMaxY = node.children.length > 0 ? Math.max(...node.children.map(getMaxY)) : node.y;
    return Math.max(node.y, childMaxY);
  };

  const svgWidth = getMaxX(treeLayout) + NODE_WIDTH + 100;
  const svgHeight = Math.max(getMaxY(treeLayout) + NODE_HEIGHT + 100, 600);

  // Toggle expand/collapse
  const toggleNode = useCallback((path: string[]) => {
    const nodeId = getNodeId(path);
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  }, []);

  // Zoom controls
  const zoomIn = () => setScale((s) => Math.min(s + 0.2, 2.5));
  const zoomOut = () => setScale((s) => Math.max(s - 0.2, 0.3));
  const resetView = () => {
    setScale(1);
    setOffset({ x: 50, y: 300 });
  };

  // Expand/collapse all
  const expandAll = useCallback(() => {
    const allIds = new Set<string>();
    const collect = (node: MindmapNode, path: string[]) => {
      allIds.add(getNodeId(path));
      node.children.forEach((child, i) => collect(child, [...path, String(i)]));
    };
    collect(data, []);
    setExpandedNodes(allIds);
  }, [data]);

  const collapseAll = useCallback(() => {
    setExpandedNodes(new Set(["root"]));
  }, []);

  // Drag to pan
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) {
      setIsDragging(true);
      setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setOffset({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => setIsDragging(false);

  // Export as PNG
  const exportPNG = async () => {
    if (!svgRef.current) return;
    const svgData = new XMLSerializer().serializeToString(svgRef.current);
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    const img = new Image();

    img.onload = () => {
      canvas.width = img.width * 2;
      canvas.height = img.height * 2;
      ctx?.scale(2, 2);
      ctx?.drawImage(img, 0, 0);
      const link = document.createElement("a");
      link.download = "mindmap.png";
      link.href = canvas.toDataURL("image/png");
      link.click();
    };

    img.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(svgData)));
  };

  // Export as JSON
  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.download = "mindmap.json";
    link.href = URL.createObjectURL(blob);
    link.click();
  };

  // Render node and edges recursively
  const renderNode = (renderedNode: RenderedNode, path: string[]) => {
    const { node, x, y, depth, expanded } = renderedNode;
    const nodeId = getNodeId(path);
    const colorIndex = depth % DEPTH_COLORS.length;

    return (
      <g key={nodeId}>
        {/* Edges to children */}
        {renderedNode.children.map((child, index) => {
          const childPath = [...path, String(index)];
          return (
            <g key={getNodeId(childPath)}>
              <motion.path
                d={`M ${x + NODE_WIDTH} ${y + NODE_HEIGHT / 2} 
                    C ${x + NODE_WIDTH + 60} ${y + NODE_HEIGHT / 2},
                      ${child.x - 60} ${child.y + NODE_HEIGHT / 2},
                      ${child.x} ${child.y + NODE_HEIGHT / 2}`}
                fill="none"
                stroke={STROKE_COLORS[child.depth % STROKE_COLORS.length]}
                strokeWidth="3"
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 1 }}
                transition={{ duration: 0.4, ease: "easeOut" }}
              />
              {renderNode(child, childPath)}
            </g>
          );
        })}

        {/* Node rectangle */}
        <motion.g
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, delay: depth * 0.1 }}
        >
          <foreignObject x={x} y={y} width={NODE_WIDTH} height={NODE_HEIGHT}>
            <div
              className={`w-full h-full rounded-lg shadow-md cursor-pointer select-none flex items-center justify-center px-3 py-2 ${DEPTH_COLORS[colorIndex]} ${
                node.children.length > 0 ? "hover:brightness-110" : ""
              }`}
              onClick={() => node.children.length > 0 && toggleNode(path)}
              style={{ minHeight: NODE_HEIGHT }}
            >
              <p className="text-sm font-medium text-center leading-tight line-clamp-2">{node.label}</p>
            </div>
          </foreignObject>

          {/* Expand/collapse indicator */}
          {node.children.length > 0 && (
            <circle
              cx={x + NODE_WIDTH}
              cy={y + NODE_HEIGHT / 2}
              r="8"
              fill={expanded ? "#10b981" : "#f59e0b"}
              stroke="white"
              strokeWidth="2"
            />
          )}
        </motion.g>
      </g>
    );
  };

  return (
    <div ref={containerRef} className="relative w-full h-full bg-gradient-to-br from-slate-50 to-slate-100 rounded-lg overflow-hidden">
      {/* Controls */}
      <div className="absolute top-4 right-4 z-10 flex flex-col gap-2">
        <div className="flex gap-2 bg-white/90 backdrop-blur-sm p-2 rounded-lg shadow-lg">
          <Button variant="outline" size="icon" onClick={zoomIn} title="Zoom In">
            <ZoomIn className="w-4 h-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={zoomOut} title="Zoom Out">
            <ZoomOut className="w-4 h-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={resetView} title="Reset View">
            <Maximize2 className="w-4 h-4" />
          </Button>
        </div>
        <div className="flex gap-2 bg-white/90 backdrop-blur-sm p-2 rounded-lg shadow-lg">
          <Button variant="outline" size="sm" onClick={expandAll}>
            Expand All
          </Button>
          <Button variant="outline" size="sm" onClick={collapseAll}>
            Collapse All
          </Button>
        </div>
        <div className="flex gap-2 bg-white/90 backdrop-blur-sm p-2 rounded-lg shadow-lg">
          <Button variant="outline" size="icon" onClick={exportPNG} title="Export as PNG">
            <Download className="w-4 h-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={exportJSON}>
            Export JSON
          </Button>
        </div>
        <div className="bg-white/90 backdrop-blur-sm px-3 py-2 rounded-lg shadow-lg text-xs text-slate-600">
          Zoom: {(scale * 100).toFixed(0)}%
        </div>
      </div>

      {/* SVG Canvas */}
      <svg
        ref={svgRef}
        className="w-full h-full cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <g transform={`translate(${offset.x}, ${offset.y}) scale(${scale})`}>
          {renderNode(treeLayout, [])}
        </g>
      </svg>
    </div>
  );
}
