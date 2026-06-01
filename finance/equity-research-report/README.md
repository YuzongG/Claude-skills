# 📑 业务驱动型深度研报生成器

输入任意美股 ticker，自动抓取业务、财务与估值数据，生成一份**以「业务深度分析」为核心**的中长线研报。
回答一个问题：**「这是不是一门好生意，现在的价格值不值得参与？」**

## 使用方法

在 Claude 对话中直接说：

> 「帮我写一份 HPE 的研报」  
> 「深度分析一下 PLTR 的业务」  
> 「帮我深挖 NVDA」  
> 「这只股票的基本面研报 / equity research」

## 输出内容（四大模块）

| 模块 | 内容 | 篇幅权重 |
|------|------|---------|
| 一、公司快照 | 一句话业务定义 + 基本信息 | 10% |
| **二、业务深度分析 ⭐** | **商业模式 / 收入构成 / 护城河 / 行业空间 / 竞争格局** | **45%** |
| 三、财务体检 | 3 年财务趋势，验证业务故事 | 25% |
| 四、估值判断 | 相对估值 + 合理价格区间 | 20% |

> 全篇核心是模块 2：不堆数据，重在「是不是好生意」的业务洞察。模块 3 用财务数字**验证或证伪**模块 2 的判断。

## 安装方法

### Claude.ai 网页版

下载 [equity-research-report.skill](./equity-research-report.skill)，在 Claude.ai → Settings → Skills 上传安装。

### Claude Code（本地）

将 `equity-research-report/` 文件夹放入 `~/.claude/skills/` 即可。需配置 Finnhub MCP 以获取实时行情：

```bash
cp .mcp.json.example .mcp.json   # 填入 Finnhub API Key
cd mcp-server && uv sync
claude                            # 在仓库根目录启动
```

## 与其他技能的协作

- 需要**精确内在价值** → 配合 `dcf-valuation`（三情景 DCF）
- 需要**最新财报电话会解读** → 配合 `earnings-call-analyzer`
- 需要**买卖时机/仓位评分** → 配合 `seven-dimension-filter`

本技能聚焦中长线基本面判断，时机与仓位交给上述技能。

## 所需 API

- **Finnhub API Key**（免费）：[https://finnhub.io/register](https://finnhub.io/register) — 实时股价、公司 profile、新闻
- 财务与分部数据从 SEC 财报 / Macrotrends / StockAnalysis 公开页面获取，无需额外 Key

> ⚠️ 本研报含主观定性判断，仅供参考，不构成投资建议。
