# 美股强势股筛选器（US Momentum Screener）

实时筛选今日盘中强势美股：涨幅≥4%、换手率≥4%、市值≥$1B，按涨幅排序并附新闻催化剂分析。

## 筛选条件

| 条件 | 默认值 |
|------|--------|
| 市场 | 美股（NYSE / NASDAQ） |
| 市值 | ≥ $1B |
| 今日涨幅 | +4% ~ +50% |
| 今日换手率 | ≥ 4% |
| 排序 | 涨幅从高到低 |

## 输出内容

1. **强势股排行表**：代码、公司、当前价、涨幅、换手率、成交量倍数、催化剂标签、建议等级
2. **逐只催化剂分析**：新闻摘要 + 2–3句分析 + 推荐等级
3. **免责声明**

## 数据来源

使用免费公开数据，无需 API Key：
- [Finviz Screener](https://finviz.com/screener.ashx) — 主要筛选数据
- [Yahoo Finance](https://finance.yahoo.com/screener/predefined/day_gainers) — 备选
- [StockAnalysis.com](https://stockanalysis.com/stocks/gainers/) — 备选
- 网络新闻搜索 — 催化剂分析

## 使用方式

直接告诉 Claude：
- 「帮我筛一下今天的美股强势股」
- 「今日有什么强势美股？」
- 「美股盘中涨幅大的有哪些？」

Claude 会自动抓取实时数据并输出分析报告，无需提供任何额外信息。

## 安装

下载 [`us-momentum-screener.skill`](./us-momentum-screener.skill) 文件，在 Claude 中上传安装。
