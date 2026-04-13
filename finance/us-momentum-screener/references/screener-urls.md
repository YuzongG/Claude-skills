# 免费筛选器 URL 汇总

## Finviz（首选，无需注册）

### 强势股基础筛选（涨幅≥4%，市值≥$300M）
```
https://finviz.com/screener.ashx?v=111&f=cap_smallover,ta_change_u4&o=-change
```

### 强势股严格筛选（涨幅≥4%，市值≥$2B）
```
https://finviz.com/screener.ashx?v=111&f=cap_midover,ta_change_u4&o=-change
```

### 带相对成交量（涨幅≥4% + 成交量≥2倍均量）
```
https://finviz.com/screener.ashx?v=111&f=cap_smallover,ta_change_u4,sh_relvol_o2&o=-change
```

### 字段说明（Finviz 表格列名）
| Finviz 列名 | 含义 |
|------------|------|
| Ticker | 股票代码 |
| Company | 公司名 |
| Sector | GICS 行业板块 |
| Industry | 细分行业 |
| Country | 国家 |
| Market Cap | 市值 |
| P/E | 市盈率 |
| Price | 当前价 |
| Change | 今日涨跌幅 |
| Volume | 今日成交量 |
| Rel Volume | 相对成交量（今日量/近期均量） |
| Avg Volume | 近期平均成交量（约3个月） |
| Float | 流通股数（百万） |

### 换手率计算
```
换手率(%) = Volume / (Float × 1,000,000) × 100
```

---

## Yahoo Finance

### 今日涨幅最大
```
https://finance.yahoo.com/screener/predefined/day_gainers
```

### 高成交量股票
```
https://finance.yahoo.com/screener/predefined/most_actives
```

---

## StockAnalysis.com

### 今日最大涨幅
```
https://stockanalysis.com/stocks/gainers/
```

### 异常成交量
```
https://stockanalysis.com/stocks/unusual-volume/
```

---

## 搜索模板

```
# 找当日强势股
web_search: "stocks up 5% today high volume site:finviz.com"
web_search: "top gainers today US stocks momentum"

# 找个股催化剂
web_search: "[TICKER] stock news today catalyst"
web_search: "[TICKER] why is stock up today"
web_search: "[TICKER] earnings announcement upgrade"
```
