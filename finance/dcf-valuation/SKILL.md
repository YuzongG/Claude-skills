---
name: dcf-valuation
description: >
  对任意美股 ticker 进行 DCF（现金流折现）三情景估值分析，输出乐观 / 中性 / 悲观三种内在价值
  与当前股价的对比表。当用户说「帮我做 DCF 估值」「给这只股票估个值」「算一下内在价值」
  「做三情景估值」「乐观/悲观/中性估值」「这只股票值多少钱」「DCF」时触发此技能。
  自动识别公司类型（科技/消费/金融/生物科技/REIT）并调整估值方法。
  所有输出使用简体中文。
---

# DCF 三情景估值分析器

## 语言要求

**所有输出使用简体中文。** 股票代码、公司英文名、数字及百分比保留原格式（如 NVDA、+12.4%、4.2×）。
数据来源名称（Finnhub、yfinance）可保留英文。其余全部简体中文。

---

## 数据来源说明

| 数据 | 来源 | 说明 |
|------|------|------|
| 公司基本面（市值、Beta、行业） | `mcp__finnhub__get_profile` | Finnhub /stock/profile2 |
| 实时股价 | `mcp__finnhub__get_quote` | Finnhub /quote 端点 |
| 财务数据（FCF、收入、债务） | `WebFetch` Macrotrends / Wisesheets | 历史财务报表 |
| 近期新闻（补充背景） | `mcp__finnhub__get_news` | Finnhub /company-news |

---

## 功能说明

给定一个股票代码，本技能将：
1. 自动识别公司类型（普通股 / 生物科技 / REIT / 周期性行业）
2. 获取关键财务数据（FCF、收入、债务、Beta、流通股数）
3. 用 CAPM 计算 WACC
4. 对三种情景分别建立 10 年 FCF 模型 + 终值
5. 输出三情景内在价值 vs 当前股价的对比表及安全边际分析

---

## Step-by-Step 工作流

### Step 1 — 获取公司基本信息

调用：
```
mcp__finnhub__get_profile(symbol="TICKER")
mcp__finnhub__get_quote(symbol="TICKER")
```

从 profile 提取：
- `name`（公司名）
- `finnhubIndustry`（行业，用于判断公司类型）
- `marketCapitalization`（市值，单位：百万美元）
- `shareOutstanding`（流通股数，单位：百万股）
- `beta`（Beta 系数；若缺失则按行业默认值填充，见 `references/sector-defaults.md`）

从 quote 提取：
- `c`（当前股价）

---

### Step 2 — 判断公司类型

根据 `finnhubIndustry` 或行业关键词自动判断：

| 公司类型 | 判断依据 | 估值方法 |
|----------|---------|---------|
| **普通股** | 多数科技、消费、工业公司 | 标准 FCF-DCF |
| **生物科技** | Biotechnology / Pharmaceutical + 无收入 or FCF < 0 | 净现金清算（悲观）+ 管线成功概率加权 DCF |
| **REIT** | Real Estate Investment Trust | FFO 替代 FCF，附加股息率参考 |
| **周期性行业** | Materials / Energy / Industrials，且 FCF 波动剧烈 | 使用归一化/历史均值 FCF，并在报告中标注 |
| **金融** | Banks / Insurance | P/B 为主，DCF 仅作参考 |

> ⚠️ 若判断为金融股，说明 DCF 不适用，改用 P/B 估值并标注。

---

### Step 3 — 获取财务数据

**Step 3.1：TTM FCF（核心输入）**

优先顺序：
1. `WebFetch` Macrotrends FCF 页面获取历史 FCF（推荐，有结构化表格）
   ```
   web_fetch: https://www.macrotrends.net/stocks/charts/[TICKER]/[company-slug]/free-cash-flow
   ```
2. 若 Macrotrends 失败，尝试：
   ```
   web_search: "[TICKER] TTM free cash flow 2024 site:wisesheets.io OR site:stockanalysis.com"
   ```

提取：最近 3–5 年 FCF 数据（用于判断趋势、计算基准值）。

**对周期性行业：** 取 3–5 年均值作为归一化 FCF 基准（而非最新 TTM），并在报告中标注。
**对生物科技：** 获取现金及等价物（Cash & Equivalents）和年度 burn rate 即可。

**Step 3.2：净债务**

净债务 = 总债务 − 现金及等价物（单位：百万美元）

若净债务为负，表示净现金头寸（对估值有利）。

**Step 3.3：收入（可选，用于 P/S 参考）**

```
web_search: "[TICKER] TTM revenue 2024"
```

---

### Step 4 — WACC 计算

使用 CAPM 计算股权成本，再加权计算 WACC：

```
无风险利率 Rf = 4.3%（2026年参考美国10年期国债收益率）
市场风险溢价 ERP = 5.5%（长期历史均值）
股权成本 ke = Rf + β × ERP
税率 T = 21%（美国企业所得税标准税率）
债务成本 kd = 5.0%（若无数据则用此默认值）

E = 股权市值（market cap）
D = 总债务
WACC = E/(E+D) × ke + D/(E+D) × kd × (1-T)
```

**三情景 WACC 调整：**

| 情景 | WACC 调整 | 说明 |
|------|----------|------|
| 乐观 | WACC − 0.5% | 资本成本降低，增长确定性高 |
| 中性 | WACC（基准值） | 当前市场条件 |
| 悲观 | WACC + 1.0% | 风险溢价上升，融资成本提高 |

> 若 β < 0.5，使用最低值 0.5；若 β > 3.0，使用上限 3.0。

---

### Step 5 — 三情景 FCF 增长假设

以 TTM FCF（或归一化 FCF）为 FCF₀ 基准，按以下增长率序列推算 10 年 FCF：

#### 普通股 / 成熟科技公司

| 情景 | 年1 | 年2 | 年3 | 年4 | 年5 | 年6 | 年7 | 年8 | 年9 | 年10 | 终值 g |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|------|--------|
| 乐观 | 8% | 8% | 7% | 7% | 6% | 5% | 4% | 3% | 3% | 3% | 2.5% |
| 中性 | 2% | 2% | 4% | 4% | 4% | 4% | 3% | 2% | 2% | 2% | 2.0% |
| 悲观 | 0% | 0% | 1% | 1% | 2% | 2% | 2% | 1% | 1% | 1% | 1.5% |

#### 高增长科技（近3年收入/FCF CAGR > 20%）

| 情景 | 年1-3 | 年4-6 | 年7-10 | 终值 g |
|------|-------|-------|--------|--------|
| 乐观 | 25% | 15% | 8% | 2.5% |
| 中性 | 15% | 10% | 5% | 2.0% |
| 悲观 | 5% | 3% | 2% | 1.5% |

#### 生物科技（FCF 持续为负）

| 情景 | 说明 |
|------|------|
| 乐观 | 主要管线获批概率 × 峰值收入 DCF（参考行业类比药物） |
| 中性 | 管线成功概率打七折，推迟上市 1–2 年 |
| 悲观 | **净现金清算价值** = (现金 − 2年 burn rate) ÷ 流通股数 |

#### REIT

用 FFO（营运资金）替代 FCF，其余同普通股。悲观情景使用股息折现（DDM）：P = D₁ / (ke − g)。

---

### Step 6 — DCF 计算

对每种情景执行以下计算：

```python
# 10年FCF列表
fcf_list = [FCF₀ × Π(1+r) for each year]

# 折现求和
pv_fcfs = Σ fcf_t / (1+WACC)^t,  t=1..10

# 终值（Gordon Growth Model）
TV = fcf₁₀ × (1 + g) / (WACC − g)
PV_TV = TV / (1+WACC)^10

# 企业价值
EV = pv_fcfs + PV_TV

# 股权价值（扣除净债务）
Equity = EV − Net_Debt（百万美元）

# 每股内在价值
Intrinsic = Equity / Shares（百万股）
```

**安全边际 (MOS)：**
- MOS 20% = Intrinsic × 0.80（建议买入价）
- MOS 30% = Intrinsic × 0.70（保守买入价）

---

### Step 7 — 输出格式

```
# 📊 DCF 三情景估值报告 — [TICKER] [公司名]
日期：[今日日期]  |  当前股价：$XX.XX  |  数据来源：Finnhub + Macrotrends

---
## 📐 关键财务假设

| 指标 | 数值 |
|------|------|
| TTM FCF（基准） | $XXX M |
| 净债务 / 净现金 | $XXX M |
| 流通股数 | XXX M 股 |
| Beta | X.XX |
| 股权成本 ke | X.X% |
| 基准 WACC | X.X% |

---
## 💰 三情景估值对比

| 情景 | FCF增长假设 | WACC | 10年PV | 终值PV | 内在价值/股 | 安全边际20% | 安全边际30% | vs 当前价 |
|------|-----------|------|--------|--------|-----------|------------|------------|---------|
| 🟢 乐观 | 高增长路径 | X.X% | $X.XX | $X.XX | **$XX.XX** | $XX.XX | $XX.XX | +XX% |
| 🟡 中性 | 基准增长路径 | X.X% | $X.XX | $X.XX | **$XX.XX** | $XX.XX | $XX.XX | +XX% |
| 🔴 悲观 | 低增长/清算 | X.X% | $X.XX | $X.XX | **$XX.XX** | $XX.XX | $XX.XX | -XX% |

---
## 📈 逐年 FCF 预测（中性情景）

| 年份 | 增长率 | 预测 FCF | 折现 FCF |
|------|--------|---------|---------|
| 第1年 | X% | $XXM | $XXM |
| ...  | ... | ... | ... |
| 终值 | g=X% | — | $XXM |

---
## 🔍 估值结论与风险提示

**综合判断：**
[2–3 句话总结：当前股价相对三情景的位置、主要驱动因素、关注风险]

**上行催化剂：** [基于新闻和行业背景]
**下行风险：** [主要风险因素]

**公司类型标注：** [普通股 / 生物科技（管线估值）/ REIT（FFO法）/ 周期性（归一化FCF）]

---
## ⚠️ 免责声明
本报告基于公开财务数据和假设参数，仅供参考，不构成任何投资建议。
DCF 估值对增长率和折现率高度敏感，实际结果可能与预测存在重大差异。
投资有风险，入市须谨慎，请在独立核实后审慎决策。
```

---

## 特殊情况处理

- **FCF 为负（非生物科技）：** 使用收入替代，搭配 P/S 区间参考；说明 DCF 暂不适用，给出 P/S 估算。
- **Beta 缺失：** 从 `references/sector-defaults.md` 读取行业默认 Beta。
- **生物科技无收入：** 自动切换到净现金清算（悲观）+ 管线概率加权 DCF（乐观/中性）。
- **金融股：** 说明 DCF 方法局限性，改用 P/B 估值（P/B_target × Book Value per Share）。
- **Macrotrends 数据抓取失败：** 切换到 WebSearch 查找 FCF，并标注数据来源。
- **终值占 EV > 80%：** 在报告中标注「终值占比过高，估值对终值增长率 g 极为敏感，请谨慎参考」。

---

## References

- `references/sector-defaults.md` — 各行业默认 Beta、WACC 参考范围
- `references/wacc-guide.md` — WACC 详细计算说明与参数来源

Read these only if needed (e.g., when Beta is missing or sector is unclear).
