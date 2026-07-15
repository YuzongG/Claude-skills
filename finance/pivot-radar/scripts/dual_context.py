#!/usr/bin/env python3
"""
验证假设: DUAL/SDUAL 在"深调筑底后(远离高点)"远好于"高位(已延伸)"。
—— 即你朋友说的"筑底突破出 DUAL 最好, 高点出 DUAL 没用"(Stage1→2 转折 vs 已延伸)。

把每个 DUAL/SDUAL 进场按触发时的位置分组比期望值:
  位置 = 距 52 周高多少%:  深调>25%(筑底区) / 中位15-25% / 高位<15%(已延伸)
  另按均线:  MA底部(EMA20≤EMA50, 未成趋势) / MA趋势(EMA20>EMA50)
统一止损/出场同 compare_entries。量基准=前3日均量。

用法: python3 dual_context.py NVDA,AVGO,... (可给一大堆, 不需板块)
"""
import sys, os
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
import parabolic as pb
import signals as sg
from compare_entries import atr_series, rvol_series, run, stats, MAXHOLD, WARMUP, RNG


def hh_series(H, n=252):
    return [max(H[max(0, i - n + 1):i + 1]) for i in range(len(H))]


def gen_dual(C, e5, e10, e20, rv):
    return [i for i in range(WARMUP, len(C) - 1)
            if e5[i] > e10[i] and C[i] > e20[i] and C[i - 1] <= e20[i - 1] and rv[i] >= 1.5]


def gen_sdual(C, e5, e10, e20, rv):
    idx = []
    for i in range(WARMUP, len(C) - 1):
        cond = e5[i] > e10[i] and C[i] > e20[i] and rv[i] >= 1.75
        prev = e5[i - 1] > e10[i - 1] and C[i - 1] > e20[i - 1] and rv[i - 1] >= 1.75
        if cond and not prev:
            idx.append(i)
    return idx


def dist_bucket(d):
    if d > 25: return '深调>25%(筑底区)'
    if d >= 15: return '中位15-25%'
    return '高位<15%(已延伸)'


def run_ctx(idx, C, H, L, e20, atr, dist, e50):
    """同 run 但给每笔打上位置/均线标签。"""
    n = len(C); trades = []; last_exit = -1
    for i in idx:
        if i <= last_exit:
            continue
        entry = C[i]; a = atr[i]; stop = entry - 2.0 * a; risk = entry - stop
        if risk <= 0:
            continue
        ex = None
        for j in range(i + 1, n):
            if L[j] <= stop: ex = (stop, j); break
            if C[j] < e20[j]: ex = (C[j], j); break
            if j - i >= MAXHOLD: ex = (C[j], j); break
        if ex is None: ex = (C[-1], n - 1)
        exitp, j = ex
        trades.append(dict(R=(exitp - entry) / risk, pct=(exitp - entry) / entry * 100, bars=j - i,
                           dist=dist_bucket(dist[i]),
                           ma=('MA底部(E20≤E50)' if e20[i] <= e50[i] else 'MA趋势(E20>E50)')))
        last_exit = j
    return trades


def report(title, trades):
    print(f"\n=== {title} (n={len(trades)}) ===")
    print("  按【距52周高】分组:")
    for b in ['深调>25%(筑底区)', '中位15-25%', '高位<15%(已延伸)']:
        s = stats([t for t in trades if t['dist'] == b])
        if s:
            print(f"    {b:<18} n={s['n']:>3}  期望{s['exp']:>+5.2f}R  平均每笔{s['avgpct']:>+5.1f}%")
        else:
            print(f"    {b:<18} 无样本")
    print("  按【均线位置】分组:")
    for b in ['MA底部(E20≤E50)', 'MA趋势(E20>E50)']:
        s = stats([t for t in trades if t['ma'] == b])
        if s:
            print(f"    {b:<18} n={s['n']:>3}  期望{s['exp']:>+5.2f}R  平均每笔{s['avgpct']:>+5.1f}%")
        else:
            print(f"    {b:<18} 无样本")


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    syms = sys.argv[1].replace(',', ' ').split()
    dual_all, sdual_all = [], []
    for s in syms:
        st = pb.fetch_dated(s.upper(), RNG)
        if not st:
            continue
        D, C, H, L, V = st
        e5, e10, e20, e50 = sg.ema_series(C, 5), sg.ema_series(C, 10), sg.ema_series(C, 20), sg.ema_series(C, 50)
        atr = atr_series(C, H, L); rv = rvol_series(V, 3); hh = hh_series(H, 252)
        dist = [(hh[i] - C[i]) / hh[i] * 100 for i in range(len(C))]
        dual_all += run_ctx(gen_dual(C, e5, e10, e20, rv), C, H, L, e20, atr, dist, e50)
        sdual_all += run_ctx(gen_sdual(C, e5, e10, e20, rv), C, H, L, e20, atr, dist, e50)

    print(f"====== DUAL/SDUAL 位置分组验证 · {len(syms)}只 · {RNG} · 量=前3日均量 ======")
    print("假设: 深调筑底区(远离高点) 应远好于 高位(已延伸)")
    report('DUAL (上穿EMA20+量)', dual_all)
    report('SDUAL (站上EMA20+量)', sdual_all)
    print("\n注: 统一止损-2ATR/出场破EMA20/40天; 距52周高越大=越像筑底突破, 越小=越高位。")


if __name__ == "__main__":
    main()
