"use client";

import { useState, useEffect } from "react";
import { getSignals } from "@/lib/api";

export default function SignalsPage() {
  const [signals, setSignals] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSignals()
      .then((res) => { if (res?.data) setSignals(res.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-500">Loading signals...</p>;
  if (!signals) return <p className="text-gray-500">Unable to load signals. Is the backend running?</p>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-cyan-400">Market Signals</h1>

      {/* VIX */}
      <section className="bg-[#1a1a2e] rounded-xl p-5 border border-gray-800">
        <h2 className="text-purple-400 font-semibold mb-3">VIX Volatility Index</h2>
        <div className="grid grid-cols-4 gap-4">
          <div><p className="text-xs text-gray-500">Level</p><p className="text-xl font-bold">{signals.vix?.current}</p></div>
          <div><p className="text-xs text-gray-500">Regime</p><p className="text-xl font-bold capitalize text-cyan-400">{signals.vix?.regime}</p></div>
          <div><p className="text-xs text-gray-500">Day Change</p><p className={`text-xl font-bold ${signals.vix?.day_change >= 0 ? "text-red-400" : "text-green-400"}`}>{signals.vix?.day_change}%</p></div>
          <div><p className="text-xs text-gray-500">Term Structure</p><p className="text-xl font-bold capitalize">{signals.vix?.term_structure}</p></div>
        </div>
      </section>

      {/* Yield Curve */}
      <section className="bg-[#1a1a2e] rounded-xl p-5 border border-gray-800">
        <h2 className="text-purple-400 font-semibold mb-3">Yield Curve</h2>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div><p className="text-xs text-gray-500">2s10s Spread</p><p className="text-xl font-bold">{signals.yield_curve?.spread_2s10s}</p></div>
          <div><p className="text-xs text-gray-500">Shape</p><p className="text-xl font-bold capitalize text-cyan-400">{signals.yield_curve?.curve_shape}</p></div>
          <div><p className="text-xs text-gray-500">Trend</p><p className="text-xl font-bold capitalize">{signals.yield_curve?.steepening_trend}</p></div>
        </div>
        {signals.yield_curve?.yields && (
          <div className="flex gap-3 flex-wrap">
            {Object.entries(signals.yield_curve.yields as Record<string, number>).map(([tenor, yld]) => (
              <span key={tenor} className="bg-[#0d0d20] px-3 py-1 rounded text-xs font-mono">
                {tenor}: {yld}%
              </span>
            ))}
          </div>
        )}
      </section>

      {/* Currencies */}
      <section className="bg-[#1a1a2e] rounded-xl p-5 border border-gray-800">
        <h2 className="text-purple-400 font-semibold mb-3">Currencies</h2>
        <div className="grid grid-cols-5 gap-4">
          {signals.currency?.levels && Object.entries(signals.currency.levels as Record<string, number>).map(([name, level]) => (
            <div key={name}>
              <p className="text-xs text-gray-500 uppercase">{name}</p>
              <p className="text-lg font-bold">{level}</p>
              <p className={`text-xs ${(signals.currency.changes_1d?.[name] || 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                {signals.currency.changes_1d?.[name] >= 0 ? "+" : ""}{signals.currency.changes_1d?.[name]}%
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Sectors */}
      <section className="bg-[#1a1a2e] rounded-xl p-5 border border-gray-800">
        <h2 className="text-purple-400 font-semibold mb-3">Sector Rotation</h2>
        <p className="text-sm mb-3">Signal: <span className="text-cyan-400 capitalize font-semibold">{signals.sectors?.rotation_signal?.replace("_", " ")}</span></p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-green-400 font-semibold mb-2">LEADERS (5d)</p>
            {signals.sectors?.leaders?.map((l: string) => <p key={l} className="text-sm text-gray-300">{l}</p>)}
          </div>
          <div>
            <p className="text-xs text-red-400 font-semibold mb-2">LAGGARDS (5d)</p>
            {signals.sectors?.laggards?.map((l: string) => <p key={l} className="text-sm text-gray-300">{l}</p>)}
          </div>
        </div>
      </section>

      {/* Flags */}
      {signals.all_flags?.length > 0 && (
        <section className="bg-[#1a1a2e] rounded-xl p-5 border border-red-900/50">
          <h2 className="text-red-400 font-semibold mb-3">Active Flags ({signals.all_flags.length})</h2>
          {signals.all_flags.map((flag: string, i: number) => (
            <p key={i} className="text-sm text-red-300 py-1">! {flag}</p>
          ))}
        </section>
      )}
    </div>
  );
}
