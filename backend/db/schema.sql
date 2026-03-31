-- Predictions log (the moat — track record accumulator)
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    thesis_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('LONG', 'SHORT')),
    entry_price REAL,
    target_price REAL,
    stop_price REAL,
    confidence REAL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    thesis_summary TEXT,
    time_horizon_days INTEGER,
    resolved_at TIMESTAMP,
    exit_price REAL,
    outcome TEXT CHECK (outcome IN ('WIN', 'LOSS', 'OPEN', 'EXPIRED'))
);

-- Signal snapshots (daily market state)
CREATE TABLE IF NOT EXISTS signal_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    signal_type TEXT NOT NULL,
    data_json TEXT NOT NULL
);

-- Tracked investor portfolios
CREATE TABLE IF NOT EXISTS tracked_portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    investor_name TEXT NOT NULL,
    investor_type TEXT NOT NULL CHECK (investor_type IN ('hedge_fund', 'congress', 'insider')),
    cik TEXT,
    last_updated TIMESTAMP
);

-- Portfolio holdings from filings
CREATE TABLE IF NOT EXISTS portfolio_holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER REFERENCES tracked_portfolios(id),
    ticker TEXT NOT NULL,
    cusip TEXT,
    shares REAL,
    value REAL,
    filing_date DATE,
    report_date DATE,
    change_type TEXT CHECK (change_type IN ('NEW', 'INCREASED', 'DECREASED', 'SOLD', 'UNCHANGED'))
);

-- Filing signals (from all layers — 13F, 13D/G, Form 3/4, options, ETF flows, predictive)
CREATE TABLE IF NOT EXISTS filing_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    signal_layer TEXT NOT NULL,
    source TEXT NOT NULL,
    investor_name TEXT,
    ticker TEXT,
    signal_type TEXT NOT NULL,
    confidence REAL,
    details_json TEXT NOT NULL,
    is_predictive BOOLEAN DEFAULT FALSE
);

-- Thesis graph nodes
CREATE TABLE IF NOT EXISTS theses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thesis_id TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT NOT NULL CHECK (source IN ('agent', 'user', 'hybrid')),
    title TEXT NOT NULL,
    summary TEXT,
    causal_chain_json TEXT,
    tickers_json TEXT,
    confidence REAL,
    time_horizon TEXT,
    risks_json TEXT,
    catalysts_json TEXT,
    tags_json TEXT,
    outcome_score REAL,
    resolved_at TIMESTAMP
);

-- Thesis graph edges (connections between theses)
CREATE TABLE IF NOT EXISTS thesis_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_thesis_id TEXT REFERENCES theses(thesis_id),
    to_thesis_id TEXT REFERENCES theses(thesis_id),
    relationship TEXT NOT NULL,
    strength REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User profiles (preference learning)
CREATE TABLE IF NOT EXISTS user_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    risk_tolerance TEXT DEFAULT 'moderate',
    sectors_of_interest_json TEXT DEFAULT '[]',
    investment_horizon TEXT DEFAULT 'medium',
    experience_level TEXT DEFAULT 'beginner',
    preferences_json TEXT DEFAULT '{}',
    portfolio_size REAL DEFAULT 10000.0
);

-- Chat history
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    metadata_json TEXT
);

-- Generated reports
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    report_type TEXT NOT NULL,
    content_html TEXT,
    content_text TEXT,
    delivered BOOLEAN DEFAULT FALSE
);
