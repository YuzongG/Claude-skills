# Data Formats Reference

## CSV Upload Format (user-provided)

If the user uploads a CSV, expect columns in various orders. Map these common headers:

| Possible Header Names | Internal Field |
|---|---|
| ticker, symbol, code | ticker |
| name, company, stock | company_name |
| volume, vol, today_vol | today_volume |
| avg_vol, avgvol, 20d_avg, average_volume | avg_volume_20d |
| rel_vol, relvol, relative_volume, vol_ratio | relative_volume |
| price, last, close | price |
| chg%, change, pct_change, %chg | price_change_pct |
| mktcap, market_cap, cap | market_cap |
| sector, gics_sector | sector |

## Computing Relative Volume

If relative volume not provided:
```
relative_volume = today_volume / avg_volume_20d
```

If avg_volume not provided but 30d or 10d avg is:
- Use whatever average is available, note it in output
- 10d avg: results may be noisier
- 30d avg: acceptable substitute

## FinViz Screener Parsing

When fetching `https://finviz.com/screener.ashx?v=111&f=sh_avgvol_o200,sh_relvol_o2&o=-relativevolume`:

The table columns in order (as of 2024–2025):
1. No. (row number)
2. Ticker
3. Company
4. Sector
5. Industry
6. Country
7. Market Cap
8. P/E
9. Price
10. Change
11. Volume

Relative Volume is in the filter criteria but may not appear as a column — you may need to fetch the detailed view or compute it from the volume data shown.

Alternative: Use `v=161` view for more columns including Rel Volume:
`https://finviz.com/screener.ashx?v=161&f=sh_relvol_o2&o=-relativevolume`

## StockAnalysis.com Parsing

URL: `https://stockanalysis.com/stocks/unusual-volume/`

Table typically includes: Symbol, Name, Price, % Change, Volume, Avg Volume, Rel Volume, Market Cap

This is the cleanest source for rel volume data.

## Pasted Table Format

If the user pastes a table directly into chat, parse it flexibly using the header mapping above. Ask for clarification only if ticker and volume columns cannot be identified.
