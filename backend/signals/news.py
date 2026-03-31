from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import Counter
import re

import requests


@dataclass
class NewsSignal:
    top_stories: list[dict]       # [{title, source, url, tickers_mentioned}]
    themes: list[str]             # dominant themes extracted
    ticker_mentions: dict[str, int]  # ticker -> mention count
    sentiment_summary: str        # positive, negative, mixed, neutral
    flags: list[str]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


COMMON_TICKERS = {
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA", "JPM",
    "V", "JNJ", "WMT", "PG", "MA", "UNH", "HD", "DIS", "BAC", "XOM", "PFE",
    "AVGO", "COST", "TMO", "ABBV", "CRM", "AMD", "NFLX", "ADBE", "INTC",
    "QCOM", "TXN", "ORCL", "IBM", "GS", "MS", "C", "BA", "GE", "CAT",
}

NEGATIVE_WORDS = {"crash", "plunge", "fear", "recession", "default", "crisis", "collapse",
                  "sell-off", "selloff", "downgrade", "warning", "bankruptcy", "layoffs"}
POSITIVE_WORDS = {"surge", "rally", "boom", "record", "upgrade", "growth", "beat",
                  "outperform", "bullish", "breakout", "soar", "gain"}


def _extract_tickers(text: str) -> list[str]:
    words = set(re.findall(r'\b[A-Z]{2,5}\b', text))
    return [w for w in words if w in COMMON_TICKERS]


def _simple_sentiment(titles: list[str]) -> str:
    text = " ".join(titles).lower()
    neg = sum(1 for w in NEGATIVE_WORDS if w in text)
    pos = sum(1 for w in POSITIVE_WORDS if w in text)
    if neg > pos + 2:
        return "negative"
    elif pos > neg + 2:
        return "positive"
    elif neg > 0 or pos > 0:
        return "mixed"
    return "neutral"


def get_news_signal_perplexity(api_key: str) -> NewsSignal:
    """Use Perplexity sonar-finance for real-time financial news analysis."""
    if not api_key:
        return _get_news_signal_fallback()

    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "sonar-finance",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a financial news analyst. Respond only with valid JSON.",
                    },
                    {
                        "role": "user",
                        "content": (
                            "What are the top 10 most market-moving financial news stories right now? "
                            "For each, provide: title, source, key tickers mentioned, and whether it's "
                            "positive/negative for markets. Also identify the top 3 dominant themes. "
                            "Respond in this exact JSON format: "
                            '{"stories": [{"title": "...", "source": "...", "tickers": ["..."], "sentiment": "positive/negative/neutral"}], '
                            '"themes": ["..."], "overall_sentiment": "positive/negative/mixed/neutral"}'
                        ),
                    },
                ],
                "temperature": 0.1,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]

        import json
        # Try to extract JSON from the response
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            data = json.loads(json_match.group())
        else:
            return _get_news_signal_fallback()

        stories = data.get("stories", [])
        themes = data.get("themes", [])
        overall = data.get("overall_sentiment", "neutral")

        top_stories = []
        ticker_counter = Counter()
        for s in stories[:10]:
            tickers = s.get("tickers", [])
            for t in tickers:
                ticker_counter[t] += 1
            top_stories.append({
                "title": s.get("title", ""),
                "source": s.get("source", ""),
                "tickers_mentioned": tickers,
                "sentiment": s.get("sentiment", "neutral"),
            })

        flags = []
        neg_count = sum(1 for s in stories if s.get("sentiment") == "negative")
        if neg_count >= 6:
            flags.append(f"{neg_count}/10 top stories are negative — bearish news cycle")
        pos_count = sum(1 for s in stories if s.get("sentiment") == "positive")
        if pos_count >= 6:
            flags.append(f"{pos_count}/10 top stories are positive — bullish news cycle")

        return NewsSignal(
            top_stories=top_stories,
            themes=themes,
            ticker_mentions=dict(ticker_counter.most_common(20)),
            sentiment_summary=overall,
            flags=flags,
        )

    except Exception as e:
        return _get_news_signal_fallback(error=str(e))


def _get_news_signal_fallback(error: str = "") -> NewsSignal:
    """Fallback using yfinance news when Perplexity is unavailable."""
    import yfinance as yf

    flags = []
    if error:
        flags.append(f"Perplexity unavailable ({error}), using yfinance fallback")

    top_stories = []
    ticker_counter = Counter()

    for ticker_sym in ["SPY", "QQQ", "AAPL", "NVDA", "TSLA"]:
        try:
            t = yf.Ticker(ticker_sym)
            news = t.news or []
            for article in news[:3]:
                title = article.get("title", "")
                tickers = _extract_tickers(title)
                tickers.append(ticker_sym)
                for tk in tickers:
                    ticker_counter[tk] += 1
                top_stories.append({
                    "title": title,
                    "source": article.get("publisher", ""),
                    "tickers_mentioned": tickers,
                })
        except Exception:
            continue

    titles = [s["title"] for s in top_stories]
    sentiment = _simple_sentiment(titles)

    return NewsSignal(
        top_stories=top_stories[:10],
        themes=[],
        ticker_mentions=dict(ticker_counter.most_common(20)),
        sentiment_summary=sentiment,
        flags=flags,
    )
