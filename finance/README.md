# 📈 Finance 金融类技能

适用于金融市场分析、选股筛选、财报研究等场景的 Claude Skill 集合。

## 技能列表

| 技能 | 简介 | 输出语言 |
|------|------|----------|
| [stock-turnover-screener](./stock-turnover-screener/) | 筛选今日换手率较5日均值翻倍（≥2×）的个股，按板块分类并结合新闻给出推荐 | 简体中文 |
| [us-momentum-screener](./us-momentum-screener/) | 实时筛选美股强势股（涨幅≥4%、换手率≥4%、市值≥$1B），按涨幅排序并附新闻催化剂分析 | 简体中文 |
| [earnings-call-analyzer](./earnings-call-analyzer/) | 输入 ticker，自动获取最新财报电话会并输出七章节深度分析报告 | 繁体中文 |
| [dcf-valuation](./dcf-valuation/) | 输入 ticker，自动获取财务数据，用 DCF 方法输出乐观/中性/悲观三情景内在价值与安全边际 | 简体中文 |

---

## 数据架构说明

这两个选股技能（stock-turnover-screener、us-momentum-screener）采用双数据源设计：

```
Finviz（网页筛选）
  └─ 候选股票列表 + 今日成交量
        ↓
Finnhub MCP Server（精确计算）
  ├─ get_batch_turnover  →  今日换手率 vs 5日均换手率 + surge_ratio
  ├─ get_batch_quotes    →  实时价格 / 涨跌幅
  ├─ get_profile         →  流通股数 / 市值 / 行业
  └─ get_news            →  近期公司新闻（催化剂识别）
```

> Finnhub `/quote` 端点在免费套餐不返回成交量字段，因此今日成交量必须从 Finviz 获取。  
> 5 日历史成交量由 MCP 服务器通过 `yfinance` 在本地计算，无需额外 API Key。

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

> 免费套餐：60 次请求/分钟，对选股技能的正常使用完全足够。

---

> 更多金融类技能持续更新中，欢迎 PR 贡献。
