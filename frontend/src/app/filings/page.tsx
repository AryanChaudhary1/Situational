"use client";

import { useState, useEffect } from "react";
import { getFilings } from "@/lib/api";

export default function FilingsPage() {
  const [filings, setFilings] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getFilings()
      .then((res) => { if (res?.data) setFilings(res.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-500">Running filing intelligence scan...</p>;
  if (!filings) return <p className="text-gray-500">Unable to load filing intelligence.</p>;

  const renderSignals = (signals: any[], title: string, color: string) => (
    signals?.length > 0 && (
      <section className="bg-[#1a1a2e] rounded-xl p-5 border border-gray-800">
        <h2 className={`${color} font-semibold mb-3`}>{title} ({signals.length})</h2>
        <div className="space-y-3">
          {signals.map((s: any, i: number) => (
            <div key={i} className="bg-[#0d0d20] rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                  s.signal_type?.includes("BUY") || s.signal_type?.includes("BULLISH") || s.signal_type?.includes("ACCUMULATION")
                    ? "bg-green-900/50 text-green-400"
                    : s.signal_type?.includes("SELL") || s.signal_type?.includes("BEARISH") || s.signal_type?.includes("DISTRIBUTION")
                    ? "bg-red-900/50 text-red-400"
                    : "bg-gray-800 text-gray-400"
                }`}>{s.signal_type}</span>
                <span className="text-cyan-400 font-mono text-sm">{s.ticker}</span>
                <span className="text-gray-500 text-xs">{s.source}</span>
                <span className="text-gray-600 text-xs ml-auto">{(s.confidence * 100).toFixed(0)}% conf</span>
              </div>
              <p className="text-sm text-gray-300">{s.details}</p>
              {s.reasoning?.length > 0 && (
                <div className="mt-2 space-y-1">
                  {s.reasoning.map((r: string, j: number) => (
                    <p key={j} className="text-xs text-gray-500 pl-3 border-l border-purple-500">{r}</p>
                  ))}
                </div>
              )}
              {s.editable && (
                <div className="flex gap-2 mt-2">
                  <button className="px-2 py-1 text-xs bg-green-900/30 text-green-400 rounded hover:bg-green-900/50">Validate</button>
                  <button className="px-2 py-1 text-xs bg-red-900/30 text-red-400 rounded hover:bg-red-900/50">Invalidate</button>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>
    )
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-cyan-400">Filing Intelligence</h1>
        <p className="text-gray-500 text-sm">Multi-layer institutional activity detection</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800 text-center">
          <p className="text-2xl font-bold">{filings.layer1_signals?.length || 0}</p>
          <p className="text-xs text-gray-500">Layer 1: Fast Filings</p>
          <p className="text-xs text-gray-600">Form 3/4, 13D/13G</p>
        </div>
        <div className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800 text-center">
          <p className="text-2xl font-bold">{filings.layer2_signals?.length || 0}</p>
          <p className="text-xs text-gray-500">Layer 2: Real-time</p>
          <p className="text-xs text-gray-600">Options, ETF flows, Earnings</p>
        </div>
        <div className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800 text-center">
          <p className="text-2xl font-bold">{filings.layer3_signals?.length || 0}</p>
          <p className="text-xs text-gray-500">Layer 3: Predictive</p>
          <p className="text-xs text-gray-600">Front-running 13F</p>
        </div>
      </div>

      {filings.flags?.length > 0 && (
        <div className="bg-red-900/20 border border-red-900/50 rounded-xl p-4">
          {filings.flags.map((f: string, i: number) => (
            <p key={i} className="text-sm text-red-300">! {f}</p>
          ))}
        </div>
      )}

      {renderSignals(filings.layer1_signals, "Layer 1: Fast Filings (Form 3/4, 13D/13G)", "text-yellow-400")}
      {renderSignals(filings.layer2_signals, "Layer 2: Real-time (Options Flow, ETF Flows, Earnings)", "text-blue-400")}
      {renderSignals(filings.layer3_signals, "Layer 3: Predictive 13F Models", "text-purple-400")}
    </div>
  );
}
