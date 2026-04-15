---
name: earnings-call-analyzer
description: >
  深度分析上市公司最新一次财报电话会议（Earnings Call）。用户输入股票代码（ticker），
  自动获取最新财报逐字稿或摘要，按专业框架输出中文分析报告，涵盖管理层语气、
  核心财务数据、Q&A精华、投资机会信号侦测与投资意涵。
  当用户提到「分析财报」、「财报电话会」、「earnings call」、「帮我看一下XX的财报」、
  「XX最新业绩怎么样」、输入股票代码并询问业绩或前景时，必须调用此技能。
  所有输出均为繁体中文（台湾用语习惯）。
---

# Earnings Call Analyzer — 财报电话会深度分析

## 语言要求

**所有输出使用繁体中文，台湾用语习惯。** 专业术语保留英文原文（如 EPS、CapEx、Book-to-Bill、ASP、Design Win 等）。股票代码、公司名称、数字保留原格式。

---

## Finnhub API 配置

本 Skill 使用 **Finnhub API** 获取结构化财务数据，包括 EPS 实际值 vs 预期值、关键财务指标与公司基本资料。

### 获取 API Key

1. 前往 [https://finnhub.io/register](https://finnhub.io/register) 免费注册
2. 复制 Dashboard 页面上的 API Key
3. 免费方案限制：**60 次请求/分钟**

### API Key 读取顺序

1. 优先检查环境变量 `FINNHUB_API_KEY`
2. 若未检测到，询问用户：「请提供 Finnhub API Key 以获取精确财务数据（可在 finnhub.io 免费注册）：」
3. 若用户无法提供，全程使用 web_search / web_fetch 替代

### 核心 API 端点（Base URL: `https://finnhub.io/api/v1`）

| 用途 | 端点 | 关键字段 |
|------|------|---------|
| 公司基本资料 | `GET /stock/profile2?symbol={symbol}&token={key}` | `name`、`exchange`、`finnhubIndustry`、`marketCapitalization`、`shareOutstanding` |
| EPS 历史与预期 | `GET /stock/earnings?symbol={symbol}&limit=8&token={key}` | `actual`（实际 EPS）、`estimate`（预期 EPS）、`surprise`（超预期幅度）、`surprisePercent`、`period`（财季） |
| 基本财务指标 | `GET /stock/metric?symbol={symbol}&metric=all&token={key}` | `revenueGrowthTTMYoy`、`grossMarginTTM`、`operatingMarginTTM`、`peBasicExclExtraTTM`、`52WeekHigh`、`52WeekLow` |
| 最新公司新闻 | `GET /company-news?symbol={symbol}&from={YYYY-MM-DD}&to={YYYY-MM-DD}&token={key}` | `headline`、`summary`、`source`（财报相关新闻） |
| 实时行情 | `GET /quote?symbol={symbol}&token={key}` | `c`（现价）、`dp`（今日涨跌幅%）、`pc`（昨收） |

---

## 工作流程

### Step 1 — 确认输入

用户应提供 ticker（股票代码）。若未提供，询问：「请问您要分析哪支股票的财报？」

若用户提供公司名称而非代码，先推断代码（如 NVIDIA → NVDA），确认后继续。

---

### Step 2 — 获取财报资料

**同步执行两条线，合并后进行分析：**

#### 线路 A — Finnhub API（结构化数据，优先执行）

若有 `FINNHUB_API_KEY`，依序调用：

**1. 公司基本资料：**
```
web_fetch: https://finnhub.io/api/v1/stock/profile2?symbol={TICKER}&token={FINNHUB_API_KEY}
```

**2. EPS 历史（最近 8 季）：**
```
web_fetch: https://finnhub.io/api/v1/stock/earnings?symbol={TICKER}&limit=8&token={FINNHUB_API_KEY}
```
返回每季 `actual`、`estimate`、`surprise`、`surprisePercent`，直接用于第三章财务数据表格。

**3. 关键财务指标：**
```
web_fetch: https://finnhub.io/api/v1/stock/metric?symbol={symbol}&metric=all&token={FINNHUB_API_KEY}
```
从 `metric` 对象中提取：`revenueGrowthTTMYoy`（营收 YoY%）、`grossMarginTTM`（毛利率）、`operatingMarginTTM`（营业利润率）、`currentRatioAnnual`（流动比率）、`52WeekHigh` / `52WeekLow`。

**4. 财报相关新闻（财报日前后各 7 天）：**
```
web_fetch: https://finnhub.io/api/v1/company-news?symbol={TICKER}&from={财报日-7天}&to={财报日+7天}&token={FINNHUB_API_KEY}
```
筛选含 "earnings"、"results"、"revenue"、"EPS" 关键字的新闻，取前 5 条。

**5. 实时股价（了解财报后市场反应）：**
```
web_fetch: https://finnhub.io/api/v1/quote?symbol={TICKER}&token={FINNHUB_API_KEY}
```

#### 线路 B — 逐字稿与管理层叙述（必须执行）

**优先：逐字稿（Transcript）**
```
web_search: "[TICKER] earnings call transcript Q[N] [YEAR] site:seekingalpha.com"
web_search: "[TICKER] Q[N] [YEAR] earnings call transcript"
web_search: "[TICKER] investor relations earnings transcript [最新季度]"
```

**次选：财报摘要 + 新闻**
```
web_search: "[TICKER] earnings results Q[N] [YEAR] revenue EPS guidance"
web_search: "[TICKER] Q[N] [YEAR] earnings call highlights analyst questions"
web_fetch: https://stockanalysis.com/stocks/{ticker}/financials/
```

**补充数据来源：**
- `https://finance.yahoo.com/quote/{TICKER}/`
- SeekingAlpha、Motley Fool、Benzinga 的财报摘要

#### 资料门槛：

- **Finnhub API 可用**：EPS、财务指标、新闻已从 API 取得，逐字稿/新闻稿至少 1 项即可输出完整报告
- **无 API Key**：须取得逐字稿或官方新闻稿 + 至少 3 篇独立财报报导

若资料不足，告知用户并说明缺失部分，其余已有资料照常分析。

---

### Step 3 — 识别最新季度

确认是哪个财季（如 Q1 FY2026）。注意各公司财年起始月不同：
- Apple：FY 起始 10 月
- Microsoft：FY 起始 7 月
- 其他：通常为自然年

---

### Step 4 — 按框架输出分析报告

严格按照以下架构输出，不得省略任何章节。

---

## 输出架构

### 报告标题
```
📋 [公司名称]（[TICKER]）财报电话会分析
📅 [财季]｜[电话会日期]
```

---

### 一、管理层前景观点（2-3句）

概括管理层对业务前景的整体判断，并标注语气等级：

> **语气等级：[极度乐观 / 审慎乐观 / 中性务实 / 保守谨慎 / 防御回避]**

说明依据（引用管理层具体用词或表述）。

---

### 二、核心重点与商业逻辑

用 3-5 个 bullet 总结本次会议最重要的讯息：
- **[重点标题]**：内容说明。背后商业逻辑：...

涵盖：重大里程碑、产品进展、市场动态、战略转向。每个 bullet 必须解释「为什么这件事重要」。

---

### 三、关键财务数据

> 📡 **数据来源标注：** 标注 `[API]` 表示来自 Finnhub 实时数据，标注 `[稿]` 表示来自逐字稿/新闻稿。

**本季实际数据：**

| 指标 | 数值 | YoY | 是否超预期 | 来源 |
|------|------|-----|-----------|------|
| 营收 | | | | |
| 毛利率 | `metric.grossMarginTTM` | | | [API] |
| 营业利润率 | `metric.operatingMarginTTM` | | | [API] |
| 净利润 | | | | |
| EPS | `earnings[0].actual` vs `earnings[0].estimate` | | `surprisePercent`% | [API] |
| 自由现金流 | | | | |

> EPS 超预期幅度直接来自 Finnhub `/stock/earnings` 的 `surprise` 字段；若 API 无法取得，从逐字稿中手动填入。

**最近 4 季 EPS 表现（来自 Finnhub）：**

| 财季 | 实际 EPS | 预期 EPS | 超预期幅度 |
|------|---------|---------|-----------|
| （最新） `earnings[0].period` | `actual` | `estimate` | `surprisePercent`% |
| `earnings[1].period` | | | |
| `earnings[2].period` | | | |
| `earnings[3].period` | | | |

**业务线拆分**（若有）：

| 业务线 | 营收 | YoY |
|--------|------|-----|
| | | |

**其他关键指标**（若有提及）：用户数、客户数、CapEx、库存天数、递延营收等。  
参考 Finnhub `metric` 中的：`currentRatioAnnual`（流动比率）、`inventoryTurnoverAnnual`（库存周转率）。

**未来指引（Guidance）：**
- 下季营收区间：
- 毛利率目标：
- CapEx 规划：
- 全年指引：

> 若公司未提供明确指引，标注：**未提供**

---

### 四、管理层语气与态度

**整体语气：[标签]** — 1-2句说明依据。

**信心最强的领域：**
- [议题]：管理层用词主动、给出具体数据或承诺

**刻意淡化的领域：**
- [议题]：一笔带过、措辞模糊或被动回应

**宏观与产业观点：**
管理层对宏观经济、供应链、产业趋势的看法与应对策略。

---

### 五、Q&A 精华

列出分析师追问最密集的 3-5 个议题：

**议题一：[议题名称]**
- 管理层回应：（精炼摘要）
- 信号判读：🟢 正面具体 / 🟡 中性一般 / 🔴 负面或防御性

**议题二：[议题名称]**
- 管理层回应：
- 信号判读：

（依此类推）

---

### 六、投资机会侦测

逐一扫描，标记「🟢 侦测到」或「🔴 本次未侦测到」：

**6.1 订单与指引的「极端落差」**
- 订单指引是否远超当季营收？
- Book-to-Bill > 1.5x？
- 季中数据提前揭露？

**6.2 供应链与产能的「提前布局」**
- 是否启用委外代工（CM）？
- 生产线是否已有大量系统在组装？

**6.3 客户行为的「结构性转变」**
- 从测试转向量产？
- Design Win 嵌入客户芯片设计？
- 主要客户垂直扩张（从 A 产品到 B 产品）？

**6.4 叙事逻辑的「去旧换新」**
- 对旧核心业务主动保守？
- 将成长逻辑挂钩至宏观刚需（「不得不买」）？

**6.5 定价权与 ASP 动态**
- ASP 持续上升且客户未流失？
- 合约结构从「按件计价」转向「按价值计价」？
- 折扣/让利行为消失？

**6.6 资本配置的「反常信号」**
- 突然加大回购或宣布特别股息？
- CapEx 方向突变（维护性→扩张性）？
- 并购标的揭示战略意图？

**6.7 竞争格局扩大**
- 竞争对手退出或缩减？
- Win rate / Design Win 数量加速？
- 客户整合供应商（该公司被留下）？

**6.8 内部人行为**
- 管理层或董事近期大量买入？
- 激励方案 KPI 从营收转向利润/现金流？

---

### 七、投资意涵

1. **最重要的结论**：这份财报对投资人最关键的信息是什么？
2. **基本面方向**：改善 / 持平 / 恶化？说明依据。
3. **持续追踪的风险**：列出 2-3 个需要关注的风险点。
4. **潜在催化剂**：哪些事件可能触发股价重估？（如下季财报、产品发布、监管批准等）

---

## 特殊情况处理

- **逐字稿未公开**：注明「逐字稿尚未公开，以下分析基于新闻稿及媒体报导」，分析仍照常进行，第五章 Q&A 标注资料有限。
- **小型公司无法搜到足够资料**：告知用户，并分析已取得的内容。
- **非美股**：同样适用，搜寻时加上交易所（如 HK、TW）或公司官方 IR 页面。
- **用户上传逐字稿**：直接以上传内容为主要分析来源，跳过 Step 2 的网路搜寻。

---

## 参考资料

- `references/financial-terms.md` — 财务术语中英对照表，需要时参考
- `references/signal-rubric.md` — 投资机会侦测评分细则

有需要时才读取。
