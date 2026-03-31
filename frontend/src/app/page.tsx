"use client";

import { useState, useEffect } from "react";
import { getSignals, getScorecard, generateTheses } from "@/lib/api";

export default function Dashboard() {
  const [signals, setSignals] = useState<any>(null);
  const [scorecard, setScorecard] = useState<any>(null);
  const [theses, setTheses] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [sigRes, scRes] = await Promise.all([
        getSignals().catch(() => null),
        getScorecard().catch(() => null),
      ]);
      if (sigRes?.data) setSignals(sigRes.data);
      if (scRes?.track_record) setScorecard(scRes.track_record);
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  }

  async function handleGenerate() {
    setLoading(true);
    try {
      const res = await generateTheses();
      if (res?.theses) setTheses(res.theses);
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  }

  useEffect(() => { loadData(); }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-cyan-400">Dashboard</h1>
          <p className="text-gray-500 text-sm">Real-time market intelligence</p>
        </div>
        <div className="flex gap-2">
          <button onClick={loadData} disabled={loading}
            className="px-4 py-2 bg-[#1a1a2e] border border-gray-700 rounded-lg text-sm hover:border-cyan-500 transition-colors disabled:opacity-50">
            Refresh Signals
          </button>
          <button onClick={handleGenerate} disabled={loading}
            className="px-4 py-2 bg-cyan-600 rounded-lg text-sm font-medium hover:bg-cyan-500 transition-colors disabled:opacity-50">
            {loading ? "Generating..." : "Generate Theses"}
          </button>
        </div>
      </div>

      {error && <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-300 text-sm">{error}</div>}

      {/* Signal cards */}
      {signals && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800">
            <p className="text-xs text-gray-500 uppercase">VIX</p>
            <p className="text-2xl font-bold mt-1">{signals.vix?.current}</p>
            <p className="text-xs mt-1">
              <span className={signals.vix?.day_change >= 0 ? "text-red-400" : "text-green-400"}>
                {signals.vix?.day_change >= 0 ? "+" : ""}{signals.vix?.day_change}%
              </span>
              {" "}| Regime: <span className="text-cyan-400">{signals.vix?.regime}</span>
            </p>
          </div>
          <div className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800">
            <p className="text-xs text-gray-500 uppercase">Yield Curve (2s10s)</p>
            <p className="text-2xl font-bold mt-1">{signals.yield_curve?.spread_2s10s}</p>
            <p className="text-xs mt-1">
              Shape: <span className="text-cyan-400">{signals.yield_curve?.curve_shape}</span>
              {" "}| {signals.yield_curve?.steepening_trend}
            </p>
          </div>
          <div className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800">
            <p className="text-xs text-gray-500 uppercase">Sector Rotation</p>
            <p className="text-2xl font-bold mt-1 capitalize">{signals.sectors?.rotation_signal?.replace("_", " ")}</p>
            <p className="text-xs mt-1 text-gray-400 truncate">
              Leaders: {signals.sectors?.leaders?.slice(0, 2).join(", ")}
            </p>
          </div>
          <div className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800">
            <p className="text-xs text-gray-500 uppercase">News Sentiment</p>
            <p className="text-2xl font-bold mt-1 capitalize">{signals.news?.sentiment_summary}</p>
            <p className="text-xs mt-1 text-gray-400 truncate">
              {signals.news?.themes?.slice(0, 3).join(", ")}
            </p>
          </div>
        </div>
      )}

      {/* Severity + Flags */}
      {signals?.all_flags?.length > 0 && (
        <div className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800">
          <div className="flex items-center gap-3 mb-3">
            <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${
              signals.severity === "crisis" ? "bg-red-900/50 text-red-400" :
              signals.severity === "alert" ? "bg-orange-900/50 text-orange-400" :
              signals.severity === "elevated" ? "bg-yellow-900/50 text-yellow-400" :
              "bg-green-900/50 text-green-400"
            }`}>{signals.severity}</span>
            <p className="text-sm text-gray-400">{signals.all_flags.length} active flags</p>
          </div>
          {signals.all_flags.map((flag: string, i: number) => (
            <p key={i} className="text-sm text-red-300 py-1">! {flag}</p>
          ))}
        </div>
      )}

      {/* Track Record */}
      {scorecard && scorecard.total_predictions > 0 && (
        <div className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800">
          <h2 className="text-sm font-semibold text-gray-400 uppercase mb-3">Track Record</h2>
          <div className="grid grid-cols-4 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold">{scorecard.win_rate}%</p>
              <p className="text-xs text-gray-500">Win Rate</p>
            </div>
            <div>
              <p className="text-2xl font-bold">{scorecard.total_predictions}</p>
              <p className="text-xs text-gray-500">Predictions</p>
            </div>
            <div>
              <p className={`text-2xl font-bold ${scorecard.avg_return_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                {scorecard.avg_return_pct}%
              </p>
              <p className="text-xs text-gray-500">Avg Return</p>
            </div>
            <div>
              <p className="text-2xl font-bold">{scorecard.sharpe_estimate}</p>
              <p className="text-xs text-gray-500">Sharpe</p>
            </div>
          </div>
        </div>
      )}

      {/* Generated Theses */}
      {theses.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-purple-400">Generated Theses</h2>
          {theses.map((thesis: any, i: number) => (
            <div key={i} className="bg-[#1a1a2e] rounded-xl p-5 border border-gray-800">
              <h3 className="text-cyan-400 font-bold text-lg">{thesis.title}</h3>
              <p className="text-gray-300 mt-2">{thesis.summary}</p>
              <div className="flex gap-3 mt-3 text-xs text-gray-500">
                <span>Confidence: {(thesis.confidence * 100).toFixed(0)}%</span>
                <span>Horizon: {thesis.time_horizon}</span>
              </div>
              <div className="mt-3 space-y-1">
                {thesis.causal_chain?.map((step: string, j: number) => (
                  <p key={j} className="text-sm text-gray-400 pl-3 border-l-2 border-purple-500">{step}</p>
                ))}
              </div>
              <div className="flex flex-wrap gap-2 mt-3">
                {thesis.tickers?.map((t: any, k: number) => (
                  <span key={k} className={`px-2 py-1 rounded text-xs font-mono ${
                    t.direction === "LONG" ? "bg-green-900/30 text-green-400 border-l-2 border-green-500" :
                    "bg-red-900/30 text-red-400 border-l-2 border-red-500"
                  }`}>
                    {t.ticker} {t.direction} | {t.entry_zone} → {t.target}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
