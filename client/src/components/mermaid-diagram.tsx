import { useEffect, useRef, useState, useCallback } from "react";
import mermaid from "mermaid";

// Initialize mermaid once
mermaid.initialize({
    startOnLoad: false,
    theme: "default",
    securityLevel: "loose",
    fontFamily: "inherit",
});

let renderCounter = 0;

interface MermaidDiagramProps {
    chart: string;
}

export default function MermaidDiagram({ chart }: MermaidDiagramProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [svg, setSvg] = useState<string>("");
    const [error, setError] = useState<string | null>(null);

    const renderChart = useCallback(async () => {
        if (!chart.trim()) return;

        try {
            const id = `mermaid-${Date.now()}-${renderCounter++}`;
            const { svg: renderedSvg } = await mermaid.render(id, chart.trim());
            setSvg(renderedSvg);
            setError(null);
        } catch (err: any) {
            console.warn("Mermaid render error:", err);
            setError(err?.message || "Failed to render diagram");
            setSvg("");
        }
    }, [chart]);

    useEffect(() => {
        renderChart();
    }, [renderChart]);

    if (error) {
        return (
            <div className="my-4 rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-950/20 p-4 overflow-x-auto">
                <p className="text-xs text-amber-600 dark:text-amber-400 mb-2 font-medium">
                    ⚠ Diagram could not be rendered
                </p>
                <pre className="text-xs text-muted-foreground font-mono whitespace-pre-wrap">{chart}</pre>
            </div>
        );
    }

    if (!svg) {
        return (
            <div className="my-4 flex items-center justify-center p-8 rounded-lg border border-border/50 bg-muted/20">
                <div className="animate-pulse text-sm text-muted-foreground">Rendering diagram...</div>
            </div>
        );
    }

    return (
        <div
            ref={containerRef}
            className="my-4 flex justify-center overflow-x-auto rounded-xl border border-border/50 bg-white dark:bg-slate-950 p-4 shadow-sm"
            dangerouslySetInnerHTML={{ __html: svg }}
        />
    );
}
