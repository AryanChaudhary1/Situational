# Situation Room

Autonomous retail investment agent that automates what a quant fund does — signal scanning, causal thesis generation, filing intelligence, predictive 13F models, backtesting, and portfolio management. All through a conversational chatbot + dashboard accessible to beginners.

## Quick Start

```bash
# 1. Set up environment
cp .env.example .env
# Add your API keys (ANTHROPIC_API_KEY and FRED_API_KEY required)

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the full daily cycle
python -m backend.main run

# 4. Or generate a specific thesis
python -m backend.main thesis "yen carry trade unwinding"

# 5. Start the API server
python -m backend.main serve

# 6. Start the frontend
cd frontend && npm install && npm run dev
```

## Architecture

```
Signal Scanners (VIX, Yields, Currency, Sectors, News via Perplexity)
        |
Filing Intelligence (Form 3/4, 13D/G, Options Flow, ETF Flows, Predictive 13F)
        |
Causal Engine (Claude — two-pass thesis generation)
        |
   +----+----+
   |         |
Backtester  Report Generator --> Email/File
(Track Record)                --> Alpaca Paper Trading
   |
Thesis Graph (connected theses over time, statistical trend analysis)
   |
Chat Agent (learns preferences, explains to beginners)
   |
Dashboard (Next.js + Tailwind)
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `python -m backend.main run` | Full daily cycle (scan + theses + report) |
| `python -m backend.main thesis "query"` | Manual thesis on a topic |
| `python -m backend.main chat` | Interactive chat mode |
| `python -m backend.main scorecard` | Show prediction track record |
| `python -m backend.main portfolio` | Notable investor changes |
| `python -m backend.main serve` | Start FastAPI server (port 8000) |
| `python -m backend.main schedule` | Daily scheduler (6:30am ET) |

## Filing Intelligence (The Edge)

Instead of waiting 45 days for 13F filings like Autopilot:

- **Layer 1** — Form 3/4 (2 business days), 13D/13G (10 days)
- **Layer 2** — Unusual options flow, ETF flow analysis, earnings call inference
- **Layer 3** — Predictive 13F models that front-run expected filings based on fund behavior patterns

## API Keys

| Key | Required | Source |
|-----|----------|--------|
| `ANTHROPIC_API_KEY` | Yes | anthropic.com |
| `FRED_API_KEY` | Yes (free) | fred.stlouisfed.org |
| `PERPLEXITY_API_KEY` | Recommended | perplexity.ai |
| `ALPACA_API_KEY` | Optional | alpaca.markets |
| `FINNHUB_API_KEY` | Optional | finnhub.io |
| `SENDGRID_API_KEY` | Optional | sendgrid.com |

## Tech Stack

- **Backend**: Python, FastAPI, SQLite
- **AI**: Anthropic Claude (reasoning), Perplexity Finance (real-time data)
- **Data**: yfinance, FRED API, SEC EDGAR (edgartools)
- **Frontend**: Next.js 14, Tailwind CSS, React
- **Trading**: Alpaca (paper trading)
