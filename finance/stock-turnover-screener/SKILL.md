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

## 数据来源说明

本 Skill 使用两个数据源协同工作：

| 数据 | 来源 | 说明 |
|------|------|------|
| 候选股票列表、今日成交量 | Finviz（WebFetch） | Finnhub 无筛选器端点，需从 Finviz 抓取 |
| 换手率计算（今日/5日均值/倍数） | `mcp__finnhub__get_turnover_data` | Finnhub 提供流通股数，yfinance 提供5日历史量 |
| 实时行情（价格、涨跌幅） | `mcp__finnhub__get_quote` / `mcp__finnhub__get_batch_quotes` | Finnhub /quote 端点 |
| 公司新闻 | `mcp__finnhub__get_news` | Finnhub /company-news 端点 |

> ⚠️ **注意**：Finnhub `/quote` 端点**不返回成交量字段**，今日成交量必须从 Finviz 获取。

---

## What This Skill Does

Given a market (default: US equities), this skill:
1. Identifies stocks where today's **turnover rate has doubled** (≥2×) vs. their 5-day average
2. Groups them by **GICS sector**
3. Fetches **current news** to explain each surge
4. **Ranks and recommends** each stock (Strong Watch / Watch / Neutral / Avoid)

**换手率定义**  
- 今日换手率 (%) = 今日成交量 ÷ 流通股数 × 100  
- 5日均换手率 (%) = 近5个交易日日均成交量 ÷ 流通股数 × 100  
- **翻倍倍数** = 今日换手率 ÷ 5日均换手率 ≥ 2.0× 触发筛选

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

### Step 2 — 获取候选股票列表（Finviz）

Finviz 是唯一能同时提供「筛选」+「今日成交量」的免费数据源，必须在此步骤获取。

**Step 2.1：抓取第一页**

```
web_fetch: https://finviz.com/screener.ashx?v=111&f=sh_avgvol_o200,sh_relvol_o2&o=-relativevolume
```

参数说明：
- `sh_relvol_o2` → 相对成交量 > 2×（初步筛选放量股）
- `sh_avgvol_o200` → 日均成交量 > 200K（排除流动性极差的仙股）
- `o=-relativevolume` → 按相对成交量倒序

从页面表格提取：**Ticker、公司名、当前价格、涨跌幅%、今日成交量（Volume）**。

**Step 2.2：按需抓取更多页**（可选，获取 40–60 只候选）

```
web_fetch: https://finviz.com/screener.ashx?v=111&f=sh_avgvol_o200,sh_relvol_o2&o=-relativevolume&r=21
web_fetch: https://finviz.com/screener.ashx?v=111&f=sh_avgvol_o200,sh_relvol_o2&o=-relativevolume&r=41
```

**Step 2.3：过滤 ETF 和极低价股**

从候选列表中剔除：
- ETF（名称含 ETF / Fund / Trust 且无实际业务）
- 股价 < $1 的仙股（换手率异动往往是操控迹象）

---

### Step 3 — 精确计算换手率（MCP Tools）

对筛选后的候选股票，构建 `symbol_volumes` 字典（Ticker → 今日成交量），调用批量工具：

```
mcp__finnhub__get_batch_turnover(
  symbol_volumes={
    "AVNS": 21670823,
    "TVTX": 11914259,
    "GSAT": 11170811,
    ...
  }
)
```

每只股票返回：

```json
{
  "today_turnover_rate_pct": 46.59,
  "avg_5d_turnover_rate_pct": 10.92,
  "surge_ratio": 4.26,
  "float_shares": 46510000,
  "avg_5d_volume": 5081120,
  "hist_volumes": [369400, 373500, 312200, 413200, 23937300],
  "data_source": "yfinance+finnhub"
}
```

**过滤条件：** `surge_ratio >= 2.0`

**排序：** 按 `surge_ratio` 倒序，取 Top N（默认 20）。

> 若个别股票返回 `{"error": "..."}` 则跳过，标注数据不可用。

---

### Step 4 — 补充实时行情

若 Finviz 的价格/涨跌幅数据已经足够，可跳过此步。  
若需要更精确的实时价格，批量调用：

```
mcp__finnhub__get_batch_quotes(symbols=["AVNS", "TVTX", "GSAT", ...])
```

返回每只股票的 `c`（现价）、`dp`（涨跌幅%）、`h`/`l`（日高/低）。

---

### Step 5 — Sector Categorization

调用 `mcp__finnhub__get_profile` 获取行业分类（`finnhubIndustry`），映射到 GICS 板块中文名：

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

若 `get_batch_turnover` 已经调用过 `get_profile`（内部会调），直接复用 profile 数据即可，无需重复请求。

若行业仍不明确，执行：`web_search: "[TICKER] sector GICS`

---

### Step 6 — News Lookup Per Stock

对 Top 10–15 只股票，调用新闻工具获取催化剂：

```
mcp__finnhub__get_news(symbol="AVNS", days_back=7)
```

返回最多 5 条最新新闻，每条含 `headline`、`summary`、`source`。

取最新 2–3 条提炼催化剂标签：

| 标签 | 含义 |
|---|---|
| 📢 财报 | 业绩超预期/不及预期/业绩指引 |
| 💊 临床/FDA | 药物获批、临床试验数据 |
| 🤝 并购 | 合并、收购、私有化传闻 |
| 📋 监管 | SEC、DOJ、政府监管行动 |
| 🔧 产品 | 新产品、合作协议、合同 |
| 📉 宏观 | 行业整体联动、宏观经济消息 |
| ❓ 不明 | 未找到明确催化剂 |

若 Finnhub 新闻不够，补充网络搜索：

```
web_search: "[TICKER] [Company Name] news today"
```

---

### Step 7 — Scoring & Ranking

Score each stock 1–10 using this rubric:

| 评分因子 | 权重 | 说明 |
|---|---|---|
| 换手率涨幅（surge_ratio） | 30% | 倍数越高，得分越高 |
| 新闻明确性 | 25% | 有明确正面催化剂得分更高 |
| 价格走势（dp） | 20% | 量价齐升为看涨确认 |
| 板块动能 | 15% | 整个板块是否同步走强 |
| 市值规模 | 10% | 市值越大，可信度越高 |

**推荐等级：**
- **🟢 重点关注**（7–10分）：催化剂明确，价格确认，值得密切跟踪
- **🟡 观察**（5–6.9分）：有一定吸引力，但催化剂不明确或价格走势混乱
- **⚪ 中性**（3–4.9分）：出现放量，但无明显信号
- **🔴 回避**（3分以下）：可能是噪音、小盘股炒作或负面催化剂

> ⚠️ 请提醒用户：本工具仅为筛选参考，不构成投资建议，请自行独立核实后决策。

---

### Step 8 — Output Format

Present results as a structured report **entirely in Simplified Chinese**:

```
# 📊 换手率异动报告 — [日期]
本次筛选：共 [N] 只个股今日换手率较5日均值翻倍（≥2×）
数据来源：Finviz（今日成交量）× Finnhub+yfinance（换手率精算）

---
## 🏆 各板块精选个股

### 💻 信息技术（N只）
| 排名 | 代码 | 公司 | 当前价 | 今日换手率 | 5日均换手率 | 翻倍倍数 | 涨跌幅 | 催化剂 | 建议 |
|------|------|------|--------|-----------|------------|---------|--------|--------|------|
| 1 | NVDA | NVIDIA | $892.10 | 8.3% | 1.9% | 4.2× | +12.1% | 📢 财报超预期 | 🟢 重点关注 |

**分析：** [2–3句话解释异动原因及后续关注要点]

### 🏥 医疗保健（N只）
...

---
## 📋 全量排名列表

| 得分 | 代码 | 公司 | 当前价 | 翻倍倍数 | 涨跌幅 | 今日换手率 | 5日均换手率 | 催化剂 | 建议 |
|------|------|------|--------|---------|--------|-----------|------------|--------|------|
| 8.5 | NVDA | NVIDIA | $892.10 | 4.2× | +12.1% | 8.3% | 1.9% | 📢 财报超预期 | 🟢 重点关注 |

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
- **MCP 工具返回 error**：跳过该股票，标注「数据不可用」。
- **未找到新闻**：标注 ❓ 不明，并降低新闻明确性得分。

---

## References

- `references/data-formats.md` — How to parse CSV/pasted data from the user
- `references/sector-lookup.md` — Manual sector tags for common tickers (saves search calls)

Read these only if needed.
