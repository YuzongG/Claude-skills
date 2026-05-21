# Claude Skills 技能库

一个为 Claude 准备的社区技能（Skill）集合，按类别整理，可直接下载安装使用。

## 什么是 Claude Skill？

Claude Skill 是一个可安装的指令包，能让 Claude 在特定任务上表现得更专业、更稳定。安装后，Claude 会在合适的时机自动调用对应的 Skill，无需你每次手动描述任务背景。

---

## 技能分类

| 类别 | 说明 | 技能数量 |
|------|------|----------|
| 📈 [finance](./finance/) | 金融市场分析、选股筛选、财报研究 | 6 |

此外还提供一个独立的交互式可视化工具：

| 工具 | 说明 |
|------|------|
| 📊 [产业链导图](./charts/) | AI 算力 + 机器人产业链关系图（实时股价 + 热力图 + 关联评分） |

---

## 📊 产业链导图（实时可视化）

一个独立运行的网页工具，把 **2 个产业链** 的所有标的可视化成关系图，每张卡片实时显示股价、按涨跌幅着色，鼠标 hover 显示上下游关联评分。

### 功能特点

- **两张产业链图谱**：AI 算力基础设施（30 个 ticker，6 层）+ 机器人产业链（24 个 ticker，6 层），左侧可折叠侧边栏一键切换
- **实时价格 + 热力图**：通过 TradingView WebSocket 推送实时股价，按 ±5% / ±3% / ±1% 涨跌幅给卡片着色，一眼看出当日热点
- **关联度可视化**：Hover 任何 ticker 自动高亮所有上下游公司，并显示 0–10 分关联评分（绿/黄/橙/红 四档颜色）
- **业务详情面板**：点击卡片右侧滑出详情，包含业务概要、实时报价、按评分排序的上下游列表
- **Finnhub 集成（可选）**：每个 ticker 可一键查询最近 30 天新闻、近 4 季度财报（EPS 实际 vs 预期 + 惊喜率）

### 安装与启动

需要本地有 [Node.js 14+](https://nodejs.org/)，然后：

```bash
# 1. 克隆仓库（如果还没克隆）
git clone https://github.com/YuzongG/Claude-skills.git
cd Claude-skills/server

# 2. 安装依赖
npm install

# 3. 启动服务器（同时托管 HTML 页面和 WebSocket 实时数据桥）
npm start
```

终端会输出：

```
╔══════════════════════════════════════════════╗
║   AI Supply Chain — TradingView Bridge       ║
║   WebSocket: ws://localhost:8080             ║
║   Press Ctrl+C to stop                       ║
╚══════════════════════════════════════════════╝

[TV] Connecting to TradingView…
[TV] Subscribed to 51 symbols
```

### 使用方式

1. 浏览器打开 **<http://localhost:8080>**
2. 顶部状态栏变绿即代表实时数据已连接
3. 左侧侧边栏点击切换：🧠 AI 算力 / 🤖 机器人
4. 卡片交互：
   - **Hover** → 显示所有关联 ticker 与评分
   - **点击** → 右侧滑出业务详情 + 实时报价 + 新闻 / 财报按钮
   - **点击关联项** → 跳转到该 ticker 的详情

### Finnhub 新闻 & 财报（可选）

点击页面右上角的 ⚙ 按钮，填入 Finnhub API Key（[免费注册](https://finnhub.io/register)，60 次/分钟免费额度）即可启用：

- 📰 **最近新闻** — 抓取最近 30 天该公司的新闻头条 + 来源 + 链接
- 📊 **过往财报** — 显示最近 4 个季度 EPS 实际 / 预期 / 惊喜率

API Key 仅存储在浏览器本地（localStorage），不上传任何服务器。

### 技术架构

```
TradingView WebSocket（实时报价）
            ↓
  Node.js 桥接服务器 (server/server.js)
            ↓ HTTP + WebSocket
       浏览器 (ai-supply-chain.html)
            ↓ （可选）
       Finnhub API（新闻 & 财报）
```

**关键设计**：

- 服务器订阅 51 个 ticker 的实时报价（两图共用一个连接）
- Stale-connection watchdog：超过 60 秒无数据自动重连 TradingView
- 浏览器端用 localStorage 保存所有用户状态（API key、侧边栏折叠、当前图表）
- 切换图表时共享 `liveQuotes` 缓存，瞬时呈现热力图，无需重新订阅

### 自定义产业链

`charts/ai-supply-chain.html` 内的 `CHARTS` 对象包含所有数据：

```javascript
const CHARTS = {
  ai:    { title, layerNames, nodes: [...], edges: [...], info: {...} },
  robot: { title, layerNames, nodes: [...], edges: [...], info: {...} },
};
```

每个节点格式：`{id, co, desc, l: layer, x, u: 是否核心标的}`。
新增产业链只需添加一个新 key，并在 sidebar 加对应 tab 按钮即可。

如果新增了 ticker，记得在 `server/server.js` 的 `SYMBOLS` 映射中加上对应的 TradingView 交易所前缀（如 `'NASDAQ:NVDA'`）。

---

## 使用方式

本库的技能支持两种运行模式：

### 模式一：Claude.ai 网页版（`.skill` 文件安装）

适合普通用户，无需任何配置。

1. 进入你想安装的技能目录（如 [`finance/stock-turnover-screener/`](./finance/stock-turnover-screener/)）
2. 下载该目录下的 `.skill` 文件
3. 打开 [Claude.ai](https://claude.ai) → **Settings → Skills → Upload Skill**
4. 安装完成后，Claude 会在对话中自动识别并调用

### 模式二：Claude Code（MCP 服务器，数据更精准）

适合开发者，通过本地 MCP 服务器直连 Finnhub API，获得实时、精确的金融数据。

**相比网页版的提升：**
- 精确的换手率计算（vs Finviz 估算值）
- 20 日历史成交量（通过 yfinance 获取，七维度评分使用）
- 实时行情直接返回结构化 JSON（无需解析 HTML）
- 结构化公司新闻，无需网络搜索

**快速配置（约 5 分钟）：**

```bash
# 1. 克隆仓库
git clone https://github.com/YuzongG/Claude-skills.git
cd Claude-skills

# 2. 安装 MCP 服务器依赖（需要先安装 uv）
cd mcp-server && uv sync && cd ..

# 3. 复制配置模板
cp .mcp.json.example .mcp.json
```

然后编辑 `.mcp.json`，填入你自己的 Finnhub API Key 和本地路径：

```json
{
  "mcpServers": {
    "finnhub": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/Claude-skills/mcp-server",
        "run",
        "server.py"
      ],
      "env": {
        "FINNHUB_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

> 用 `pwd` 命令获取 `mcp-server/` 目录的绝对路径填入上方。

最后在项目根目录打开 Claude Code：

```bash
claude
```

Claude Code 会自动检测 `.mcp.json` 并启动 MCP 服务器，`finnhub` 工具即可使用。

> 详细说明见 [`mcp-server/README.md`](./mcp-server/README.md)

---

## 获取 Finnhub API Key（免费，2 分钟）

1. 访问 [https://finnhub.io/register](https://finnhub.io/register) 注册
2. 登录后在 Dashboard 复制 API Key
3. 填入 `.mcp.json` 的 `FINNHUB_API_KEY` 字段即可

> 免费方案限额：60 次请求/分钟，对所有技能的正常使用完全足够。

---

## 目录结构

```
Claude-skills/
├── .mcp.json.example      # MCP 配置模板（复制后填入自己的 Key）
├── mcp-server/            # Finnhub MCP 服务器（Claude Code 使用）
│   ├── server.py
│   ├── pyproject.toml
│   └── README.md
├── charts/                # 产业链导图网页
│   └── ai-supply-chain.html
├── server/                # TradingView 实时数据桥 + HTML 托管服务器
│   ├── server.js
│   └── package.json
└── finance/               # 金融类技能
    ├── stock-turnover-screener/   # 换手率翻倍筛选器
    ├── us-momentum-screener/      # 美股强势股筛选器
    ├── earnings-call-analyzer/    # 财报电话会深度分析
    ├── dcf-valuation/             # DCF 三情景估值
    ├── news-stock-funnel/         # 新闻→趋势→产业→个股 四阶漏斗
    └── seven-dimension-filter/    # 七维度过滤框架评分器
```

每个技能目录包含：

```
skill-name/
├── SKILL.md          # 技能主文件（Claude 读取的指令）
├── README.md         # 技能说明文档
├── skill-name.skill  # 打包文件，供 Claude.ai 直接安装
└── references/       # 参考资料（可选）
```

---

## 贡献指南

欢迎提交 PR 贡献新技能！请参考现有技能的目录结构，确保每个技能包含 `SKILL.md`、`README.md` 和打包好的 `.skill` 文件。

---

## 许可证

MIT License — 自由使用、修改和分发。
