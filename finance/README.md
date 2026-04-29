# 📈 Finance 金融类技能

适用于金融市场分析、选股筛选、财报研究等场景的 Claude Skill 集合。

## 技能列表

| 技能 | 简介 | 触发词示例 | 输出语言 |
|------|------|-----------|----------|
| [stock-turnover-screener](./stock-turnover-screener/) | 筛选今日换手率较5日均值翻倍（≥2×）的个股，按板块分类并结合新闻给出推荐 | 「帮我筛倍量股」「换手率异动」 | 简体中文 |
| [us-momentum-screener](./us-momentum-screener/) | 实时筛选美股强势股（涨幅≥4%、换手率≥4%、市值≥$1B），按涨幅排序并附新闻催化剂分析 | 「帮我筛强势股」「今日强势美股」 | 简体中文 |
| [earnings-call-analyzer](./earnings-call-analyzer/) | 输入 ticker，自动获取最新财报电话会并输出七章节深度分析报告 | 「分析财报电话会」「earnings call」 | 繁体中文 |
| [dcf-valuation](./dcf-valuation/) | 输入 ticker，自动获取财务数据，用 DCF 方法输出乐观/中性/悲观三情景内在价值与安全边际 | 「帮我做DCF估值」「算内在价值」 | 简体中文 |
| [news-stock-funnel](./news-stock-funnel/) | 从今日最重要的3条新闻出发，逐层推导：事件→趋势→受影响产业→今日放量个股 | 「早餐选股」「从新闻找机会」「四阶漏斗」 | 简体中文 |
| [seven-dimension-filter](./seven-dimension-filter/) | 输入 ticker，从七个维度自动评分（满分35），输出仓位建议（满仓/标准/试单/放弃） | 「帮我评分」「七维度打分」「TICKER 能不能买」 | 繁体中文 |

---

## 数据架构说明

所有选股与评分技能采用双数据源设计：

```
Finviz（网页筛选）
  └─ 候选股票列表 + 今日成交量
        ↓
Finnhub MCP Server（精确计算）
  ├─ get_batch_turnover    →  今日换手率 vs 5/20日均换手率 + surge_ratio
  ├─ get_turnover_data     →  近20日历史成交量（七维度评分使用）
  ├─ get_batch_quotes      →  实时价格 / 涨跌幅
  ├─ get_profile           →  流通股数 / 市值 / 行业
  └─ get_news              →  近期公司新闻（催化剂识别）
```

> Finnhub `/quote` 端点在免费套餐不返回成交量字段，因此今日成交量必须从 Finviz 获取。  
> 历史成交量由 MCP 服务器通过 `yfinance` 在本地计算，无需额外 API Key。

---

## 技能使用场景

```
早上开盘前（30分钟）推荐工作流：

  1. news-stock-funnel       → 今日3条重要新闻 → 推导受影响产业
         ↓
  2. stock-turnover-screener → 在目标产业中找今日放量个股
     us-momentum-screener   → 找今日涨幅强势个股
         ↓
  3. seven-dimension-filter  → 对候选个股逐一打分，决定是否出手及仓位大小
         ↓
  4. dcf-valuation           → 对有意向的个股做估值，确认安全边际
  5. earnings-call-analyzer  → 深挖近期财报，理解基本面质量
```

---

## 安装方法

### Claude.ai 网页版（`.skill` 文件）

直接下载对应 `.skill` 文件，在 Claude.ai → Settings → Skills 中上传安装，无需任何配置。

| 技能 | 直接下载 |
|------|----------|
| stock-turnover-screener | [stock-turnover-screener.skill](./stock-turnover-screener/stock-turnover-screener.skill) |
| us-momentum-screener | [us-momentum-screener.skill](./us-momentum-screener/us-momentum-screener.skill) |
| earnings-call-analyzer | [earnings-call-analyzer.skill](./earnings-call-analyzer/earnings-call-analyzer.skill) |
| dcf-valuation | [dcf-valuation.skill](./dcf-valuation/dcf-valuation.skill) |
| news-stock-funnel | [news-stock-funnel.skill](./news-stock-funnel/news-stock-funnel.skill) |
| seven-dimension-filter | [seven-dimension-filter.skill](./seven-dimension-filter/seven-dimension-filter.skill) |

### Claude Code（MCP 服务器，精确数据）

需要额外配置本地 MCP 服务器，可获得精确的换手率计算和实时结构化数据：

1. 在仓库根目录执行 `cp .mcp.json.example .mcp.json`
2. 填入你的 Finnhub API Key 和本地路径
3. 执行 `cd mcp-server && uv sync` 安装依赖
4. 在仓库根目录运行 `claude` 启动 Claude Code

详细步骤见 [mcp-server/README.md](../mcp-server/README.md)

---

## 获取 Finnhub API Key（免费）

1. 访问 [https://finnhub.io/register](https://finnhub.io/register) 注册
2. 登录后在 Dashboard 复制 API Key
3. 填入 `.mcp.json` 的 `FINNHUB_API_KEY` 字段

> 免费套餐：60 次请求/分钟，对所有技能的正常使用完全足够。

---

> 更多金融类技能持续更新中，欢迎 PR 贡献。
