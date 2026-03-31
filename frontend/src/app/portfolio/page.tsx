"use client";

import { useState } from "react";
import { getProfile, updateProfile } from "@/lib/api";

export default function PortfolioPage() {
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  async function loadProfile() {
    setLoading(true);
    try {
      const res = await getProfile();
      if (res?.data) setProfile(res.data);
    } catch {}
    setLoading(false);
  }

  if (!profile && !loading) loadProfile();

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-cyan-400">Portfolio</h1>

      {/* User Profile */}
      {profile && (
        <section className="bg-[#1a1a2e] rounded-xl p-5 border border-gray-800">
          <h2 className="text-purple-400 font-semibold mb-4">Your Profile</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-500">Risk Tolerance</label>
              <select value={profile.risk_tolerance}
                onChange={(e) => {
                  const v = e.target.value;
                  setProfile({ ...profile, risk_tolerance: v });
                  updateProfile({ risk_tolerance: v });
                }}
                className="w-full mt-1 bg-[#0d0d20] border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200">
                <option value="conservative">Conservative</option>
                <option value="moderate">Moderate</option>
                <option value="aggressive">Aggressive</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Experience Level</label>
              <select value={profile.experience_level}
                onChange={(e) => {
                  const v = e.target.value;
                  setProfile({ ...profile, experience_level: v });
                  updateProfile({ experience_level: v });
                }}
                className="w-full mt-1 bg-[#0d0d20] border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200">
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Investment Horizon</label>
              <select value={profile.investment_horizon}
                onChange={(e) => {
                  const v = e.target.value;
                  setProfile({ ...profile, investment_horizon: v });
                  updateProfile({ investment_horizon: v });
                }}
                className="w-full mt-1 bg-[#0d0d20] border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200">
                <option value="short">Short (weeks)</option>
                <option value="medium">Medium (months)</option>
                <option value="long">Long (years)</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Portfolio Size</label>
              <input type="number" value={profile.portfolio_size}
                onChange={(e) => {
                  const v = parseFloat(e.target.value) || 0;
                  setProfile({ ...profile, portfolio_size: v });
                  updateProfile({ portfolio_size: v });
                }}
                className="w-full mt-1 bg-[#0d0d20] border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200"
              />
            </div>
          </div>
        </section>
      )}

      {/* Notable investors section */}
      <section className="bg-[#1a1a2e] rounded-xl p-5 border border-gray-800">
        <h2 className="text-purple-400 font-semibold mb-3">Tracked Institutional Investors</h2>
        <p className="text-sm text-gray-400 mb-4">13F filings monitored with causal WHY analysis</p>
        <div className="grid grid-cols-2 gap-3">
          {["Berkshire Hathaway", "Bridgewater Associates", "Renaissance Technologies", "Soros Fund Management", "Pershing Square Capital", "Citadel Advisors", "Two Sigma", "D.E. Shaw", "Tiger Global", "Appaloosa Management"].map((name) => (
            <div key={name} className="bg-[#0d0d20] rounded-lg p-3 flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-cyan-900/50 flex items-center justify-center text-cyan-400 font-bold text-xs">
                {name.split(" ").map(w => w[0]).join("").slice(0, 2)}
              </div>
              <span className="text-sm text-gray-300">{name}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
