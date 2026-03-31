export interface SignalReport {
  timestamp: string;
  severity: string;
  all_flags: string[];
  vix: {
    current: number;
    regime: string;
    day_change: number;
    week_change: number;
    term_structure: string;
  };
  yield_curve: {
    spread_2s10s: number;
    curve_shape: string;
    steepening_trend: string;
  };
  currency: {
    levels: Record<string, number>;
    changes_1d: Record<string, number>;
  };
  sectors: {
    rotation_signal: string;
    leaders: string[];
    laggards: string[];
    returns_5d: Record<string, number>;
  };
  news: {
    sentiment_summary: string;
    themes: string[];
    top_stories: Array<{ title: string; source: string }>;
  };
}

export interface Thesis {
  thesis_id: string;
  title: string;
  summary: string;
  source: string;
  causal_chain: string[];
  tickers: TickerRec[];
  confidence: number;
  time_horizon: string;
  risks: string[];
  catalysts: string[];
  tags: string[];
  created_at: string;
}

export interface TickerRec {
  ticker: string;
  instrument_type: string;
  direction: string;
  rationale: string;
  entry_zone: string;
  target: string;
  stop_loss: string;
  position_size_pct: number;
  current_price?: number;
}

export interface TrackRecord {
  total_predictions: number;
  resolved: number;
  open: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_return_pct: number;
  best_trade: string;
  worst_trade: string;
  sharpe_estimate: number;
}

export interface GraphData {
  nodes: Array<{
    id: string;
    title: string;
    source: string;
    confidence: number;
    tags: string[];
    created_at: string;
    outcome_score?: number;
  }>;
  edges: Array<{
    source: string;
    target: string;
    relationship: string;
    strength: number;
  }>;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  created_at?: string;
}
