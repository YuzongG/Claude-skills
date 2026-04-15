# 🚀 美股强势股筛选器（US Momentum Screener）

实时筛选今日盘中强势美股：涨幅≥4%、换手率≥4%、市值≥$1B，按涨幅排序并附新闻催化剂分析。所有输出均为**简体中文**。

---

## 筛选条件

| 条件 | 默认值 |
|------|--------|
| 市场 | 美股（NYSE / NASDAQ） |
| 市值 | ≥ $1B |
| 今日涨幅 | +4% ~ +50% |
| 今日换手率 | ≥ 4% |
| 排序 | 涨幅从高到低，取 Top 20 |

---

## 安装方法

### Claude.ai 网页版（推荐普通用户）

1. 下载本目录下的 [`us-momentum-screener.skill`](./us-momentum-screener.skill) 文件
2. 打开 [Claude.ai](https://claude.ai) → **Settings → Skills**
3. 点击 **Upload Skill**，选择下载的文件，安装完成 ✓

### Claude Code（精确数据模式）

需要配置本地 Finnhub MCP 服务器，获得精确的换手率和实时行情数据：

```bash
git clone https://github.com/yuzongg/claude-skills.git
cd claude-skills
cp .mcp.json.example .mcp.json   # 填入你的 Finnhub API Key 和路径
cd mcp-server && uv sync && cd ..
claude                           # 启动 Claude Code
```

详细配置步骤见 [mcp-server/README.md](../../mcp-server/README.md)

---

## 触发方式

安装后，直接告诉 Claude：

> "帮我筛一下今天的美股强势股"  
> "今日有什么强势美股？"  
> "美股盘中涨幅大的有哪些？"  
> "找一下今天的强势股"

Claude 会自动抓取实时数据并输出分析报告，无需提供任何额外信息。

---

## 输出示例

```
📊 美股强势股报告 — 2026-04-15 14:30 ET
筛选条件：市值≥$1B｜涨幅+4%~+50%｜换手率≥4%
数据来源：Finviz（成交量）× Finnhub MCP（行情/资料/新闻）
本次共筛出 7 只强势股，按涨幅排序如下：

🏆 强势股排行

| 排名 | 代码 | 公司             | 当前价   | 涨幅     | 换手率  | 市值    | 催化剂            | 建议        |
|------|------|------------------|----------|----------|---------|---------|-------------------|-------------|
|  1   | BE   | Bloom Energy Corp | $219.03 | +23.98%  | 8.90%   | $61.4B  | 🔧 产品/合作       | 🟢 重点关注  |
|  2   | IONQ | IONQ Inc          | $35.76  | +20.16%  | 18.25%  | $13.1B  | 📋 监管/政策       | 🟢 重点关注  |
```

---

## 评分体系

| 评分因子 | 权重 | 说明 |
|---------|------|------|
| 涨幅强度 | 30% | 涨幅越高得分越高 |
| 催化剂明确性 | 30% | 有具体正面消息得分高 |
| 换手率 | 20% | 换手率越高、量价配合越好 |
| 市值规模 | 10% | 市值越大可信度越高 |
| 板块动能 | 10% | 同板块多只股票同涨，加成 |

| 等级 | 分数 | 含义 |
|------|------|------|
| 🟢 重点关注 | 7–10 | 催化剂明确，量价齐升 |
| 🟡 观察 | 5–6.9 | 有吸引力但催化剂不清晰 |
| ⚪ 中性 | 3–4.9 | 涨幅和换手率达标，但无明显信号 |
| 🔴 回避 | <3 | 可能是短线炒作或负面背景 |

---

## 数据来源

| 数据 | 来源 | 说明 |
|------|------|------|
| 候选股票 + 今日成交量 | Finviz 筛选器 | 无需 API Key |
| 实时行情（价格/涨跌幅） | `mcp__finnhub__get_batch_quotes` | Finnhub /quote（不含成交量字段） |
| 流通股数 / 市值 / 行业 | `mcp__finnhub__get_profile` | Finnhub /stock/profile2 |
| 公司新闻 | `mcp__finnhub__get_news` | Finnhub /company-news |

> 换手率计算：Finviz 今日成交量 ÷ (shareOutstanding × 1,000,000) × 100

---

## 文件结构

```
us-momentum-screener/
├── SKILL.md                      # 技能主文件（Claude 读取的指令）
├── README.md                     # 本说明文档
├── us-momentum-screener.skill    # 可直接安装的打包文件
└── references/
    ├── sector-map.md             # 行业板块中英文对照
    └── screener-urls.md          # 筛选器 URL 汇总
```

---

> **本工具仅供参考，不构成投资建议。**
