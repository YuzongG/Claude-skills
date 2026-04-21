# 行业默认参数参考表

当 Finnhub profile 返回的 Beta 缺失或异常时，使用以下行业默认值。

## 默认 Beta（无杠杆，近似值）

| 行业（finnhubIndustry 关键词） | 默认 Beta | WACC 参考范围 |
|-------------------------------|----------|--------------|
| Technology / Software | 1.3 | 9–12% |
| Semiconductors | 1.5 | 10–13% |
| Biotechnology / Pharmaceutical | 1.6 | 10–14% |
| Medical Devices | 1.1 | 8–11% |
| Consumer Discretionary / Retail | 1.1 | 8–11% |
| Consumer Staples / Food | 0.7 | 6–8% |
| Industrials / Aerospace | 1.0 | 8–10% |
| Energy / Oil & Gas | 1.2 | 9–12% |
| Materials / Chemicals | 1.1 | 8–11% |
| Financials / Banks | 1.0 | 8–10% |
| Real Estate / REIT | 0.8 | 6–9% |
| Utilities | 0.5 | 5–7% |
| Communication Services | 1.0 | 8–10% |

## 无风险利率 Rf（定期更新）

| 日期 | 美国10年期国债收益率 |
|------|------------------|
| 2026-04 | 4.3% |

> 使用前请确认当前国债收益率是否有重大变化（±0.5% 以上需更新）。

## 市场风险溢价 ERP

| 来源 | 数值 |
|------|------|
| Damodaran（2025 年美国） | 5.5% |
| 历史长期均值（1928–2024） | 5.5% |

## 生物科技管线成功率参考（FDA历史数据）

| 阶段 | 进入下一阶段概率 |
|------|----------------|
| Phase 1 → Phase 2 | 64% |
| Phase 2 → Phase 3 | 35% |
| Phase 3 → NDA提交 | 60% |
| NDA提交 → 获批 | 85% |
| **Phase 1 → 最终获批** | **~13%** |
| **Phase 2 → 最终获批** | **~20%** |
| **Phase 3 → 最终获批** | **~50%** |
