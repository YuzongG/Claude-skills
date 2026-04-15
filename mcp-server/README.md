# Finnhub MCP Server

A lightweight MCP (Model Context Protocol) server that gives Claude Code direct access to Finnhub real-time data and Yahoo Finance historical volume — no WebFetch parsing required.

## What it does

| Tool | Description |
|------|-------------|
| `get_quote` | Real-time price, change %, high/low for a single symbol |
| `get_batch_quotes` | Same as above for a list of symbols (rate-limited) |
| `get_profile` | Company name, sector, shares outstanding, market cap |
| `get_news` | Latest 5 company news items (up to N days back) |
| `get_turnover_data` | Today's turnover rate vs 5-day average; returns surge_ratio |
| `get_batch_turnover` | Same as above for a dict of `{symbol: today_volume}` |

> **Why MCP instead of WebFetch?**  
> WebFetch passes HTML through an LLM, losing field fidelity and breaking on layout changes.  
> This server calls Finnhub's JSON API directly and uses `yfinance` for historical volume — 
> giving structured, reliable data every time.

## Prerequisites

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** — fast Python package manager
- A free **[Finnhub API key](https://finnhub.io/register)** (takes ~2 minutes)

## Setup

### 1. Clone the repo (if you haven't already)

```bash
git clone https://github.com/yuzongg/claude-skills.git
cd claude-skills
```

### 2. Install dependencies

```bash
cd mcp-server
uv sync
```

This installs `mcp[cli]`, `httpx`, and `yfinance` into an isolated virtual environment.

### 3. Get a free Finnhub API key

1. Go to [https://finnhub.io/register](https://finnhub.io/register)
2. Sign up (free, no credit card)
3. Copy the API key from your Dashboard

### 4. Configure `.mcp.json`

In the **root of the repo**, copy the example config and fill in your details:

```bash
cp .mcp.json.example .mcp.json
```

Then edit `.mcp.json`:

```json
{
  "mcpServers": {
    "finnhub": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/claude-skills/mcp-server",
        "run",
        "server.py"
      ],
      "env": {
        "FINNHUB_API_KEY": "your_actual_api_key_here"
      }
    }
  }
}
```

Replace `/absolute/path/to/claude-skills/mcp-server` with the real path on your machine.  
You can get it by running `pwd` inside the `mcp-server/` directory.

> ⚠️ `.mcp.json` is listed in `.gitignore` — your API key will never be committed.

### 5. Open the project in Claude Code

```bash
cd /path/to/claude-skills
claude
```

Claude Code will automatically detect `.mcp.json` and start the MCP server.  
You should see `finnhub` listed under active MCP servers.

## Verify it works

In a Claude Code session, ask:

> "用 get_quote 查一下 AAPL 的实时价格"

You should get back a structured JSON response with `c`, `dp`, `h`, `l` fields.

## Rate limits

The server enforces **55 requests / 60 seconds** to stay within Finnhub's free tier limit of 60 req/min.  
Batch tools (`get_batch_quotes`, `get_batch_turnover`) process symbols sequentially — no manual throttling needed.

## Data sources

| Data | Source | Notes |
|------|--------|-------|
| Real-time quotes | Finnhub `/quote` | No `volume` field on free tier |
| Company profile | Finnhub `/stock/profile2` | Includes `shareOutstanding` |
| Company news | Finnhub `/company-news` | Capped at 5 most recent |
| 5-day historical volume | `yfinance` | Free, no API key needed |
| Today's volume | Must be passed in by caller | Obtained from Finviz in skills |
