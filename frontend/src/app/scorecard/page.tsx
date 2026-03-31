"use client";

import { useState, useEffect } from "react";
import { getScorecard, getPredictions } from "@/lib/api";

export default function ScorecardPage() {
  const [scorecard, setScorecard] = useState<any>(null);
  const [predictions, setPredictions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getScorecard().catch(() => null),
      getPredictions().catch(() => null),
    ]).then(([scRes, predRes]) => {
      if (scRes?.track_record) setScorecard(scRes.track_record);
      if (predRes?.data) setPredictions(predRes.data);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-500">Loading scorecard...</p>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-cyan-400">Scorecard</h1>

      {scorecard && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800 text-center">
            <p className="text-3xl font-bold">{scorecard.win_rate}%</p>
            <p className="text-xs text-gray-500">Win Rate</p>
          </div>
          <div className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800 text-center">
            <p className={`text-3xl font-bold ${scorecard.avg_return_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
              {scorecard.avg_return_pct}%
            </p>
            <p className="text-xs text-gray-500">Avg Return</p>
          </div>
          <div className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800 text-center">
            <p className="text-3xl font-bold">{scorecard.sharpe_estimate}</p>
            <p className="text-xs text-gray-500">Sharpe Ratio</p>
          </div>
          <div className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800 text-center">
            <p className="text-3xl font-bold">{scorecard.total_predictions}</p>
            <p className="text-xs text-gray-500">Total Predictions</p>
          </div>
        </div>
      )}

      {scorecard && (
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-green-900/20 border border-green-900/50 rounded-xl p-4">
            <p className="text-green-400 font-semibold">Best Trade</p>
            <p className="text-sm text-gray-300 mt-1">{scorecard.best_trade}</p>
          </div>
          <div className="bg-red-900/20 border border-red-900/50 rounded-xl p-4">
            <p className="text-red-400 font-semibold">Worst Trade</p>
            <p className="text-sm text-gray-300 mt-1">{scorecard.worst_trade}</p>
          </div>
        </div>
      )}

      {/* Predictions table */}
      {predictions.length > 0 && (
        <section className="bg-[#1a1a2e] rounded-xl p-5 border border-gray-800 overflow-x-auto">
          <h2 className="text-purple-400 font-semibold mb-3">All Predictions</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 text-xs uppercase">
                <th className="text-left pb-3">Ticker</th>
                <th className="text-left pb-3">Direction</th>
                <th className="text-left pb-3">Entry</th>
                <th className="text-left pb-3">Target</th>
                <th className="text-left pb-3">Stop</th>
                <th className="text-left pb-3">Confidence</th>
                <th className="text-left pb-3">Outcome</th>
                <th className="text-left pb-3">Date</th>
              </tr>
            </thead>
            <tbody>
              {predictions.slice(0, 50).map((p: any, i: number) => (
                <tr key={i} className="border-t border-gray-800">
                  <td className="py-2 font-mono text-cyan-400">{p.ticker}</td>
                  <td className={p.direction === "LONG" ? "text-green-400" : "text-red-400"}>{p.direction}</td>
                  <td>${p.entry_price?.toFixed(2)}</td>
                  <td>${p.target_price?.toFixed(2)}</td>
                  <td>${p.stop_price?.toFixed(2)}</td>
                  <td>{((p.confidence || 0) * 100).toFixed(0)}%</td>
                  <td className={
                    p.outcome === "WIN" ? "text-green-400 font-bold" :
                    p.outcome === "LOSS" ? "text-red-400 font-bold" :
                    "text-gray-400"
                  }>{p.outcome}</td>
                  <td className="text-gray-500 text-xs">{p.created_at?.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {predictions.length === 0 && !loading && (
        <div className="text-center text-gray-500 py-12">
          <p>No predictions yet. Generate theses from the Dashboard to start building your track record.</p>
        </div>
      )}
    </div>
  );
}
