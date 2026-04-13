---
name: stock-turnover-screener
description: >
  Screen stocks that have experienced a doubling (2×) or more in turnover rate today
  compared to their recent average. Use this skill whenever the user asks to screen for
  unusual volume, turnover spikes, high-activity stocks, stocks with 2x volume, or wants
  to find stocks with abnormal trading activity today. Also trigger when user asks for
  volume surge analysis, sector-based stock screening, or wants news-driven explanations
  for sudden stock moves. This skill categorizes results by sector, fetches current news
  to explain the surge, and provides ranked buy/watch/avoid recommendations.
  ALL output must be written in Simplified Chinese (简体中文), including sector names,
  catalyst tags, analysis paragraphs, recommendation labels, and the disclaimer.
---

# Stock Turnover Rate Doubler Screener

## Language Requirement

**所有输出必须使用简体中文。** This applies to every user-facing element:
- Report title, section headers, and table column names
- Sector names (see Chinese names in Step 4)
- Catalyst tag labels and recommendation tier labels
- All analysis paragraphs, commentary, and the disclaimer

Ticker symbols, company names, and numeric values stay in their original form (e.g. NVDA, +8.3%, 4.2×). News source names may stay in English. Everything else: **简体中文**.

---

## What This Skill Does

Given a market (default: US equities), this skill:
1. Identifies stocks where today's **turnover rate has doubled** (≥2×) vs. their 3–5 day average
2. Groups them by **GICS sector**
3. Fetches **current news** to explain each surge
4. **Ranks and recommends** each stock (Strong Watch / Watch / Neutral / Avoid)

**Turnover Rate** = Today's Volume ÷ Shares Outstanding (or Float)  
**Surge Threshold** = Today's Turnover Rate ÷ 3–5 day Avg Turnover Rate ≥ 2.0×  
**均值基准**：优先使用5日均量；若数据源仅提供3日均量，则以3日为准，并在报告中注明。

---

## Step-by-Step Workflow

### Step 1 — Clarify Scope (if not already clear)

Ask the user:
- Which market/exchange? (US, HK, TW, global)
- Any sector filter, or all sectors?
- How many stocks to return? (default: top 20 by surge ratio)
- Date: today (default) or a specific date?

If the user seems in a hurry or the context is clear, skip to Step 2 with defaults.

---

### Step 2 — Data Gathering Strategy

**Claude does NOT have direct access to a live stock feed.** Use the following approach:

#### Option A — Web Search for Screener Data (preferred)
Search for pre-built screener results using queries like:
- `"unusual volume" stocks today site:finviz.com`
- `"volume surge" stocks today 2x average`
- `site:stockanalysis.com unusual volume today`
- `"high turnover" stocks today [EXCHANGE]`
- `finviz unusual volume screener today`

Then fetch the actual screener page:
- `https://finviz.com/screener.ashx?v=111&f=sh_avgvol_o200,sh_relvol_o2&o=-relativevolume`
  - This shows stocks with relative volume > 2× — exactly what we need
- `https://stockanalysis.com/stocks/unusual-volume/`
- For HK/TW markets: search for local equivalents

Use `web_fetch` to retrieve and parse the screener table.

#### Option B — User-Provided Data
If the user uploads a CSV or pastes a table of stocks with volume data, use that directly. See `references/data-formats.md` for parsing guidance.

#### Required fields per stock:
| Field | Source |
|---|---|
| Ticker | screener |
| Company Name | screener |
| Sector | screener or lookup |
| Today's Volume | screener |
| Avg Volume (3–5d) | screener or compute |
| Relative Volume (ratio) | screener or compute |
| Price, % Change | screener |
| Market Cap | screener |

---

### Step 3 — Compute & Filter

For each stock in results:
```
turnover_surge_ratio = today_volume / avg_3_to_5d_volume
```
优先使用5日均量（`avg_5d_volume`）；若数据源不提供，改用3日均量（`avg_3d_volume`）并标注。

Filter to: `turnover_surge_ratio >= 2.0`

Sort by `turnover_surge_ratio` descending. Take top N (default 20).

---

### Step 4 — Sector Categorization

Group stocks into GICS sectors, using the Chinese names below in all output:

| English | 简体中文 |
|---|---|
| Technology | 信息技术 |
| Health Care | 医疗保健 |
| Financials | 金融 |
| Consumer Discretionary | 非必需消费品 |
| Consumer Staples | 必需消费品 |
| Industrials | 工业 |
| Energy | 能源 |
| Materials | 材料 |
| Real Estate | 房地产 |
| Utilities | 公用事业 |
| Communication Services | 通信服务 |

If sector is missing, do a quick web search: `[TICKER] sector GICS`

---

### Step 5 — News Lookup Per Stock

For each stock (focus on top 10–15 to keep this manageable), search:
```
web_search: "[TICKER] [Company Name] news today"
web_search: "[TICKER] stock volume surge reason April 2026"
```

Categorize the news driver into one of:
| 标签 | 含义 |
|---|---|
| 📢 财报 | 业绩超预期/不及预期/业绩指引 |
| 💊 临床/FDA | 药物获批、临床试验数据 |
| 🤝 并购 | 合并、收购、私有化传闻 |
| 📋 监管 | SEC、DOJ、政府监管行动 |
| 🔧 产品 | 新产品、合作协议、合同 |
| 📉 宏观 | 行业整体联动、宏观经济消息 |
| ❓ 不明 | 未找到明确催化剂 |

---

### Step 6 — Scoring & Ranking

Score each stock 1–10 using this rubric:

| 评分因子 | 权重 | 说明 |
|---|---|---|
| 换手率涨幅 | 30% | 倍数越高，得分越高 |
| 新闻明确性 | 25% | 有明确正面催化剂得分更高 |
| 价格走势 | 20% | 量价齐升为看涨确认 |
| 板块动能 | 15% | 整个板块是否同步走强 |
| 市值规模 | 10% | 市值越大，可信度越高 |

**推荐等级：**
- **🟢 重点关注**（7–10分）：催化剂明确，价格确认，值得密切跟踪
- **🟡 观察**（5–6.9分）：有一定吸引力，但催化剂不明确或价格走势混乱
- **⚪ 中性**（3–4.9分）：出现放量，但无明显信号
- **🔴 回避**（3分以下）：可能是噪音、小盘股炒作或负面催化剂

> ⚠️ 请提醒用户：本工具仅为筛选参考，不构成投资建议，请自行独立核实后决策。

---

### Step 7 — Output Format

Present results as a structured report **entirely in Simplified Chinese**:

```
# 📊 换手率异动报告 — [日期]
本次筛选：共 [N] 只个股今日换手率较3–5日均值翻倍（≥2×）

---
## 🏆 各板块精选个股

### 💻 信息技术（N只）
| 排名 | 代码 | 公司 | 换手倍数 | 涨跌幅 | 催化剂 | 建议 |
|------|------|------|----------|--------|--------|------|
| 1 | NVDA | NVIDIA | 4.2× | +8.3% | 📢 财报超预期 | 🟢 重点关注 |

**分析：** [2–3句话解释异动原因及后续关注要点]

### 🏥 医疗保健（N只）
...

---
## 📋 全量排名列表
[按得分排序的所有个股汇总表]

---
## ⚠️ 免责声明
本报告仅供信息参考，不构成任何投资建议。
投资有风险，入市须谨慎，请独立判断后审慎决策。
```

---

## 特殊情况处理

- **仙股／微盘股**：标注提示。小盘股高换手往往是操纵迹象，市值低于5000万美元自动扣2分。
- **ETF**：默认排除，除非用户明确要求纳入。
- **盘前／盘后数据**：注明数据为盘前/盘后，换手率倍数可能偏高，需谨慎参考。
- **停牌股票**：标注 ⛔ 并从推荐列表中剔除。
- **未找到新闻**：标注 ❓ 不明，并降低新闻明确性得分。

---

## References

- `references/data-formats.md` — How to parse CSV/pasted data from the user
- `references/sector-lookup.md` — Manual sector tags for common tickers (saves search calls)

Read these only if needed.
