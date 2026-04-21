# 📊 DCF 三情景估值分析器

输入任意美股 ticker，自动获取财务数据，用 DCF 方法输出**乐观 / 中性 / 悲观**三种情景的内在价值，与当前股价对比。

## 使用方法

在 Claude 对话中直接说：

> 「帮我对 NVDA 做 DCF 估值」  
> 「AAPL 的内在价值大概是多少？」  
> 「给 GHRS 做一个三情景 DCF」  
> 「这只股票值多少钱 / 乐观悲观估值」

## 输出内容

- **关键假设一览**：FCF 基准、净债务、Beta、WACC
- **三情景估值对比表**：内在价值 / 安全边际 20% / 安全边际 30% vs 当前股价
- **逐年 FCF 预测**（中性情景）
- **结论与风险提示**：上行催化剂、下行风险
- 自动识别公司类型，调整估值方法：
  - 普通股 → 标准 FCF-DCF
  - 生物科技 → 净现金清算（悲观）+ 管线概率加权 DCF
  - REIT → FFO 替代 FCF
  - 周期股 → 历史均值归一化 FCF
  - 金融股 → P/B 估值（DCF 不适用）

## 安装方法

### Claude.ai 网页版

下载 [dcf-valuation.skill](./dcf-valuation.skill)，在 Claude.ai → Settings → Skills 上传安装，即可使用。

### Claude Code（本地 MCP）

需配置本地 Finnhub MCP 服务器以获取实时行情与公司基本面数据：

```bash
cp .mcp.json.example .mcp.json   # 填入 Finnhub API Key
cd mcp-server && uv sync
claude                            # 在仓库根目录启动
```

## 估值方法说明

**DCF（Discounted Cash Flow，现金流折现）**

以未来 10 年自由现金流（FCF）折现求和，加上终值（Gordon 增长模型），再减去净债务，得到每股内在价值。

```
内在价值 = [Σ FCFt/(1+WACC)^t] + [TV/(1+WACC)^10] − 净债务
TV = FCF₁₀ × (1+g) / (WACC−g)
```

**三情景增长路径（普通股默认）**

| 情景 | 年1–3 增长 | 年4–7 增长 | 年8–10 增长 | 终值 g | WACC |
|------|-----------|-----------|------------|--------|------|
| 乐观 | 8% | 6–7% | 3% | 2.5% | 基准 −0.5% |
| 中性 | 2–4% | 4% | 2% | 2.0% | 基准 |
| 悲观 | 0–1% | 2% | 1% | 1.5% | 基准 +1.0% |

> ⚠️ DCF 对增长率和折现率高度敏感，本工具仅供参考，不构成投资建议。

## 所需 API

- **Finnhub API Key**（免费）：[https://finnhub.io/register](https://finnhub.io/register)
  - 用于实时股价、公司 profile、Beta
- 财务数据（FCF、债务）从 Macrotrends / StockAnalysis 公开页面获取，无需额外 Key
