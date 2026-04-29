# Claude Skills 技能库

一个为 Claude 准备的社区技能（Skill）集合，按类别整理，可直接下载安装使用。

## 什么是 Claude Skill？

Claude Skill 是一个可安装的指令包，能让 Claude 在特定任务上表现得更专业、更稳定。安装后，Claude 会在合适的时机自动调用对应的 Skill，无需你每次手动描述任务背景。

---

## 技能分类

| 类别 | 说明 | 技能数量 |
|------|------|----------|
| 📈 [finance](./finance/) | 金融市场分析、选股筛选、财报研究 | 6 |

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
