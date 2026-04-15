"""
Finnhub MCP Server for stock screening skills.

Data sources:
- Finnhub API: real-time quote, company profile, news
- yfinance:     historical daily OHLCV (5-day volume for turnover rate calculation)
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections import deque
from datetime import datetime, timedelta

import httpx
import yfinance as yf
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")
if not FINNHUB_API_KEY:
    raise RuntimeError("FINNHUB_API_KEY environment variable is not set")

BASE_URL = "https://finnhub.io/api/v1"

mcp = FastMCP("finnhub")

# Shared async HTTP client (reused across all requests)
_client = httpx.AsyncClient(timeout=15.0)


# ---------------------------------------------------------------------------
# Rate limiter: 55 calls / 60 seconds (leaves 5 req/min headroom)
# ---------------------------------------------------------------------------

class _RateLimiter:
    def __init__(self, max_calls: int = 55, period: float = 60.0) -> None:
        self.max_calls = max_calls
        self.period = period
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            # Drop timestamps older than the window
            while self._timestamps and now - self._timestamps[0] >= self.period:
                self._timestamps.popleft()
            if len(self._timestamps) >= self.max_calls:
                sleep_for = self.period - (now - self._timestamps[0])
                if sleep_for > 0:
                    log.info("Rate limit reached, sleeping %.1fs", sleep_for)
                    await asyncio.sleep(sleep_for)
            self._timestamps.append(asyncio.get_event_loop().time())


_rate_limiter = _RateLimiter()


# ---------------------------------------------------------------------------
# Internal HTTP helper
# ---------------------------------------------------------------------------

async def _get(endpoint: str, params: dict) -> dict | list:
    """Make a rate-limited GET request to Finnhub and return parsed JSON."""
    await _rate_limiter.acquire()
    params["token"] = FINNHUB_API_KEY
    url = f"{BASE_URL}{endpoint}"
    resp = await _client.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_quote(symbol: str) -> dict:
    """Get real-time quote for a US stock symbol.

    Returns:
        c:  current price
        d:  price change vs previous close
        dp: percent change (%)
        h:  day high
        l:  day low
        o:  day open
        pc: previous close
    Note: volume is NOT available from Finnhub /quote on the free tier.
    Use get_turnover_data to compute turnover rates with today's volume from Finviz.
    """
    return await _get("/quote", {"symbol": symbol.upper()})


@mcp.tool()
async def get_profile(symbol: str) -> dict:
    """Get company profile for a US stock symbol.

    Returns key fields:
        name:                  company name
        ticker:                stock symbol
        finnhubIndustry:       GICS industry
        shareOutstanding:      shares outstanding in millions
        marketCapitalization:  market cap in millions USD
    """
    return await _get("/stock/profile2", {"symbol": symbol.upper()})


@mcp.tool()
async def get_news(symbol: str, days_back: int = 7) -> list:
    """Fetch recent company news for a US stock symbol.

    Args:
        symbol:    stock ticker (e.g. "AAPL")
        days_back: how many days of history to fetch (default 7)

    Returns list of news items, each with:
        headline, summary, datetime (unix), source, url
    Capped at 5 most recent items to keep context manageable.
    """
    to_date = datetime.today()
    from_date = to_date - timedelta(days=days_back)
    data = await _get("/company-news", {
        "symbol": symbol.upper(),
        "from": from_date.strftime("%Y-%m-%d"),
        "to": to_date.strftime("%Y-%m-%d"),
    })
    if isinstance(data, list):
        return data[:5]
    return data


@mcp.tool()
async def get_turnover_data(symbol: str, today_volume: int) -> dict:
    """Calculate today's turnover rate vs 5-day average turnover rate.

    This is the core metric for the stock-turnover-screener skill.
    A surge_ratio >= 2.0 means today's turnover rate doubled vs recent average.

    Args:
        symbol:        stock ticker (e.g. "NVDA")
        today_volume:  today's trading volume (integer, obtained from Finviz)

    Returns:
        today_turnover_rate_pct:   today's turnover rate in % (e.g. 4.12)
        avg_5d_turnover_rate_pct:  5-day avg turnover rate in % (e.g. 1.03)
        surge_ratio:               today / avg (e.g. 4.0 means 4x surge)
        float_shares:              float shares used in calculation
        avg_5d_volume:             5-day average daily volume
        hist_volumes:              list of last 5 days' volumes (oldest first)
        data_source:               always "yfinance+finnhub"
    """
    sym = symbol.upper()

    # --- Step 1: get float shares from Finnhub ---
    profile = await _get("/stock/profile2", {"symbol": sym})
    share_outstanding = profile.get("shareOutstanding")
    if not share_outstanding:
        return {"error": f"Could not retrieve shareOutstanding for {sym}"}

    float_shares = share_outstanding * 1_000_000  # convert millions → shares

    # --- Step 2: get last 5 complete trading days' volume from yfinance ---
    # Fetch 15 calendar days to ensure we get 5+ trading days.
    # Explicitly exclude today so intraday partial volume is never mixed in.
    today_str = datetime.today().strftime("%Y-%m-%d")
    loop = asyncio.get_event_loop()
    hist = await loop.run_in_executor(
        None,
        lambda: yf.Ticker(sym).history(period="15d")
    )

    if hist.empty or "Volume" not in hist.columns:
        return {"error": f"Could not retrieve historical volume for {sym} from yfinance"}

    # Drop today's row if yfinance returned partial intraday data
    hist.index = hist.index.tz_localize(None) if hist.index.tzinfo is not None else hist.index
    hist = hist[hist.index.strftime("%Y-%m-%d") < today_str]

    recent_volumes = hist["Volume"].tail(5).tolist()
    if len(recent_volumes) < 3:
        return {"error": f"Insufficient historical data for {sym} (only {len(recent_volumes)} days)"}

    avg_5d_vol = sum(recent_volumes) / len(recent_volumes)

    # --- Step 3: compute turnover rates ---
    today_turnover = today_volume / float_shares * 100
    avg_5d_turnover = avg_5d_vol / float_shares * 100
    surge_ratio = today_turnover / avg_5d_turnover if avg_5d_turnover > 0 else 0

    return {
        "today_turnover_rate_pct": round(today_turnover, 2),
        "avg_5d_turnover_rate_pct": round(avg_5d_turnover, 2),
        "surge_ratio": round(surge_ratio, 2),
        "float_shares": int(float_shares),
        "avg_5d_volume": int(avg_5d_vol),
        "hist_volumes": [int(v) for v in recent_volumes],
        "data_source": "yfinance+finnhub",
    }


@mcp.tool()
async def get_batch_quotes(symbols: list[str]) -> dict:
    """Fetch real-time quotes for multiple symbols with automatic rate limiting.

    Ideal for screening 20-40 tickers at once. Processes symbols sequentially
    with the built-in rate limiter (55 req/min).

    Args:
        symbols: list of stock tickers (e.g. ["AAPL", "NVDA", "TSLA"])

    Returns:
        dict mapping each symbol to its quote data (same fields as get_quote)
    """
    results = {}
    for sym in symbols:
        sym = sym.upper()
        try:
            results[sym] = await _get("/quote", {"symbol": sym})
        except Exception as e:
            results[sym] = {"error": str(e)}
    return results


@mcp.tool()
async def get_batch_turnover(symbol_volumes: dict[str, int]) -> dict:
    """Compute turnover rate surge ratios for multiple symbols at once.

    Args:
        symbol_volumes: dict mapping ticker → today's volume
                        e.g. {"AAPL": 95000000, "NVDA": 42000000}

    Returns:
        dict mapping each symbol to its turnover data (same as get_turnover_data)
    """
    results = {}
    for sym, vol in symbol_volumes.items():
        try:
            results[sym.upper()] = await get_turnover_data(sym, vol)
        except Exception as e:
            results[sym.upper()] = {"error": str(e)}
    return results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
