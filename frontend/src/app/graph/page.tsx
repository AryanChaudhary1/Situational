"use client";

import { useState, useEffect } from "react";
import { getGraph, getGraphTrends } from "@/lib/api";

export default function GraphPage() {
  const [graph, setGraph] = useState<any>(null);
  const [trends, setTrends] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getGraph().catch(() => null),
      getGraphTrends().catch(() => null),
    ]).then(([graphRes, trendsRes]) => {
      if (graphRes?.data) setGraph(graphRes.data);
      if (trendsRes?.data) setTrends(trendsRes.data);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-500">Loading thesis graph...</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-cyan-400">Thesis Graph</h1>
        <p className="text-gray-500 text-sm">Connected investment theses over time</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800 text-center">
          <p className="text-2xl font-bold">{graph?.nodes?.length || 0}</p>
          <p className="text-xs text-gray-500">Theses</p>
        </div>
        <div className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800 text-center">
          <p className="text-2xl font-bold">{graph?.edges?.length || 0}</p>
          <p className="text-xs text-gray-500">Connections</p>
        </div>
        <div className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800 text-center">
          <p className="text-2xl font-bold">{trends?.length || 0}</p>
          <p className="text-xs text-gray-500">Trend Insights</p>
        </div>
      </div>

      {/* Graph visualization placeholder */}
      <div className="bg-[#1a1a2e] rounded-xl p-8 border border-gray-800 min-h-[300px] flex items-center justify-center">
        {graph?.nodes?.length > 0 ? (
          <div className="w-full">
            <p className="text-gray-500 text-sm mb-4 text-center">Thesis Network (interactive graph coming soon — install react-force-graph-2d)</p>
            <div className="flex flex-wrap gap-3 justify-center">
              {graph.nodes.map((node: any) => (
                <div key={node.id} className="bg-[#0d0d20] rounded-lg p-3 border border-gray-700 max-w-xs">
                  <p className="text-cyan-400 text-sm font-semibold">{node.title}</p>
                  <div className="flex gap-2 mt-1">
                    <span className="text-xs text-gray-500">{node.source}</span>
                    <span className="text-xs text-gray-500">{(node.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div className="flex gap-1 mt-2 flex-wrap">
                    {node.tags?.map((tag: string) => (
                      <span key={tag} className="px-1.5 py-0.5 bg-purple-900/30 text-purple-400 rounded text-xs">{tag}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            {graph.edges?.length > 0 && (
              <div className="mt-4 space-y-1">
                <p className="text-sm text-gray-500 text-center">Connections:</p>
                {graph.edges.map((edge: any, i: number) => (
                  <p key={i} className="text-xs text-gray-500 text-center">
                    {edge.source.slice(0, 8)}... → {edge.target.slice(0, 8)}... : {edge.relationship} ({(edge.strength * 100).toFixed(0)}%)
                  </p>
                ))}
              </div>
            )}
          </div>
        ) : (
          <p className="text-gray-500">No theses yet. Generate some from the Dashboard to build your graph.</p>
        )}
      </div>

      {/* Trend Insights */}
      {trends.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-purple-400">Trend Insights</h2>
          {trends.map((t: any, i: number) => (
            <div key={i} className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800">
              <div className="flex items-center gap-2 mb-2">
                <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                  t.type === "recurring_theme" ? "bg-purple-900/50 text-purple-400" :
                  t.type === "accuracy_pattern" ? "bg-cyan-900/50 text-cyan-400" :
                  t.type === "concentration_risk" ? "bg-red-900/50 text-red-400" :
                  "bg-gray-800 text-gray-400"
                }`}>{t.type}</span>
                <span className="text-sm font-semibold text-gray-200">{t.title}</span>
              </div>
              <p className="text-sm text-gray-400">{t.details}</p>
              {t.recommendation && (
                <p className="text-sm text-cyan-300 mt-2">{t.recommendation}</p>
              )}
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
