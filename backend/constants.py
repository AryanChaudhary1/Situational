"""Centralized constants and tunable parameters.

All magic numbers, thresholds, and defaults that were previously scattered
across the codebase live here. Grouped by domain.
"""

# --- Signal severity scoring ---
# classify_severity() in scanner.py uses these to map flag counts to severity levels.
# Score = len(all_flags) + regime bonuses below.
SEVERITY_THRESHOLD_CRISIS = 6
SEVERITY_THRESHOLD_ALERT = 4
SEVERITY_THRESHOLD_ELEVATED = 2

# Bonus points added to severity score based on VIX regime
SEVERITY_BONUS_VIX_FEAR = 3
SEVERITY_BONUS_VIX_ELEVATED = 1
SEVERITY_BONUS_RISK_OFF = 1

# --- Signal caching ---
SIGNAL_CACHE_TTL_SECONDS = 300  # 5 minutes

# --- Filing confidence values ---
# Layer 1: Insider trades (Form 3/4)
CONFIDENCE_INSIDER_BUY = 0.7
CONFIDENCE_INSIDER_SELL = 0.5

# Layer 1: 13D/G filings
CONFIDENCE_13D_ACTIVIST = 0.75
CONFIDENCE_13G_PASSIVE = 0.6

# Filing convergence: how many same-direction signals before flagging
CONVERGENCE_THRESHOLD = 3

# --- Causal engine / LLM ---
LLM_MODEL = "claude-sonnet-4-20250514"
LLM_PASS1_MAX_TOKENS = 2048   # Free-form reasoning pass
LLM_PASS2_MAX_TOKENS = 4096   # Structured JSON pass

# --- Thesis defaults (when Claude omits fields) ---
DEFAULT_CONFIDENCE = 0.5
DEFAULT_TIME_HORIZON = "unknown"
DEFAULT_TIME_HORIZON_DAYS = 30
DEFAULT_POSITION_SIZE_PCT = 0.02
DEFAULT_DIRECTION = "LONG"
DEFAULT_INSTRUMENT_TYPE = "stock"

# --- Backtester defaults ---
# Applied when Claude doesn't provide target/stop prices
DEFAULT_TARGET_MULTIPLIER = 1.10   # +10% from entry
DEFAULT_STOP_MULTIPLIER = 0.95     # -5% from entry

# Sanity check: entry/current price ratio bounds (filters option vs stock mismatch)
PRICE_RATIO_MIN = 0.1
PRICE_RATIO_MAX = 10.0

# --- Sharpe ratio ---
RISK_FREE_RATE_ANNUAL = 0.05   # 5% annualized (approximate T-bill rate)
TRADING_DAYS_PER_YEAR = 252

# --- Database defaults ---
DEFAULT_THESIS_CONFIDENCE = 0.5
DEFAULT_EDGE_STRENGTH = 0.5

# --- Chat ---
CHAT_HISTORY_LIMIT = 50
