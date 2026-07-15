#!/usr/bin/env python3
"""
大 universe 验证 (~250只/11板块, 并行拉数据) —— 坐实表2信号。
表2 DUAL = 深调>25% + 新鲜从下方(前10天≥6天在EMA20下), ±筑底闸门; 外加 SDUAL点火。
统一止损-2ATR/出场破EMA20/40天; 量=前3日均量; 2年。
用法: python3 universe_validate.py
"""
import sys, os, datetime, concurrent.futures
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
START = None   # 只统计此日期(含)之后进场的交易; 指标仍用全历史计算
import parabolic as pb
import signals as sg
from compare_entries import atr_series, rvol_series, run, stats, WARMUP, RNG
from base_validate import base_ready, gen_sdual_ignition
from dual_context import hh_series
from sector_dual import gen_dual_fresh

SECTORS = {
    '半导体': ['NVDA','AVGO','AMD','MU','AMAT','ASML','TXN','LRCX','KLAC','ADI','QCOM','MRVL','CDNS','SNPS','MPWR','NXPI','TER','ARM','INTC','ON','SWKS','MCHP'],
    '网络安全': ['PANW','FTNT','CRWD','NET','OKTA','ZS','DDOG','CYBR','QLYS','TENB','S','GEN','FFIV','AKAM','RBRK','CHKP','FROG'],
    '软件': ['MSFT','PLTR','ORCL','CRM','APP','NOW','ADBE','INTU','EA','TTWO','ADSK','ROP','FICO','WDAY','ZM','NTNX','MSTR','SNOW','TEAM','MDB','HUBS','PATH'],
    '生科': ['MRNA','VKTX','KYMR','APGE','RVMD','BBIO','PCVX','CYTK','RYTM','INSM','NTRA','RARE','PTGX','ROIV','RLAY','COGT','TWST'],
    '金融': ['JPM','V','MA','BAC','GS','WFC','MS','C','AXP','SCHW','BLK','PGR','SPGI','CB','COF','PNC','USB','BX','HOOD','CME','ICE','AON'],
    '医疗': ['LLY','JNJ','ABBV','UNH','MRK','AMGN','TMO','GILD','ABT','ISRG','PFE','CVS','VRTX','DHR','BMY','SYK','MDT','ELV','CI','BSX','REGN','HCA'],
    '能源': ['XOM','CVX','COP','MPC','PSX','VLO','SLB','EOG','WMB','KMI','TRGP','OKE','BKR','DVN','OXY','FANG','EQT','HAL','APA'],
    '工业': ['CAT','GE','GEV','RTX','UNP','BA','ETN','UBER','DE','PH','VRT','HWM','TT','LMT','ADP','PWR','GD','CSX','CMI','JCI','WM','UPS'],
    '消费可选': ['AMZN','TSLA','HD','MCD','TJX','BKNG','SBUX','LOW','MAR','HLT','ORLY','RCL','DASH','ROST','GM','ABNB','NKE','AZO','CMG','CVNA','YUM','DHI'],
    '成长高波动': ['COIN','ROKU','RBLX','U','AFRM','SOFI','DKNG','SHOP','TWLO','SMCI','RKLB','IONQ','SOUN','CELH'],
}


def process(sym):
    st = pb.fetch_dated(sym, RNG)
    if not st or len(st[1]) < 140:
        return None
    D, C, H, L, V = st
    e5, e10, e20 = sg.ema_series(C, 5), sg.ema_series(C, 10), sg.ema_series(C, 20)
    atr = atr_series(C, H, L, 14); rv = rvol_series(V, 3); hh = hh_series(H, 252)
    dist = [(hh[i] - C[i]) / hh[i] * 100 for i in range(len(C))]
    ok = lambda i: START is None or D[i] >= START
    dual = [i for i in gen_dual_fresh(C, e5, e10, e20, rv) if dist[i] > 25 and ok(i)]
    dualg = [i for i in dual if base_ready(i, C, H, L, e5, e10, e20)]
    ign = [i for i in gen_sdual_ignition(C, e20, rv) if ok(i)]
    return (run(dual, C, H, L, e20, atr), run(dualg, C, H, L, e20, atr), run(ign, C, H, L, e20, atr))


def line(label, s):
    if not s or s['n'] < 1:
        print(f"    {label:<16} 无样本"); return
    print(f"    {label:<16} n={s['n']:>4}  胜率{s['wr']*100:>3.0f}%  期望{s['exp']:>+5.2f}R  平均每笔{s['avgpct']:>+5.1f}%")


def main():
    global START
    if len(sys.argv) > 1:
        START = datetime.date.fromisoformat(sys.argv[1])
    seen = set(); tasks = []
    for sector, syms in SECTORS.items():
        for s in syms:
            if s not in seen:
                seen.add(s); tasks.append((sector, s))
    print(f"拉取 {len(tasks)} 只 (并行)...", file=sys.stderr)

    per = {sec: [[], [], []] for sec in SECTORS}
    fails = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(process, s): (sec, s) for sec, s in tasks}
        for fut in concurrent.futures.as_completed(futs):
            sec, s = futs[fut]
            try:
                r = fut.result()
            except Exception:
                r = None
            if not r:
                fails += 1; continue
            for k in range(3):
                per[sec][k] += r[k]

    tot = [[], [], []]
    print(f"\n====== 大universe验证 · {len(tasks)-fails}只成功 · {RNG} · 表2信号 ======")
    print("DUAL = 深调>25% + 新鲜从下方; 闸门 = 筑底(纠缠+窄幅+走平)")
    for sec in SECTORS:
        ng, g, ig = per[sec]
        for k, x in enumerate((ng, g, ig)):
            tot[k] += x
        print(f"\n【{sec}】")
        line('DUAL 不加闸门', stats(ng))
        line('DUAL 加闸门', stats(g))
        line('SDUAL点火', stats(ig))
    print(f"\n════════ 全部合计 ════════")
    line('DUAL 不加闸门', stats(tot[0]))
    line('DUAL 加闸门', stats(tot[1]))
    line('SDUAL点火', stats(tot[2]))
    print(f"\n(失败 {fails} 只; 样本≥30 才算稳健)")


if __name__ == "__main__":
    main()
