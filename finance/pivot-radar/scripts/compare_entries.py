#!/usr/bin/env python3
"""
进场信号三方对比 —— 同一套止损/出场, 只换进场触发, 比纯"进场逻辑"的期望值。

三套进场:
  A 回踩重启(缠论)  = 抬高底(DIOK_HL) + 回踩重启(收回EMA5), 站上EMA20且不过热  [现行]
  B DUAL(均线穿越)  = EMA5>EMA10 + 收盘上穿EMA20 + 量≥1.5×前3日均量           [原富途]
  C SDUAL(均线站上) = EMA5>EMA10 + 收盘站上EMA20 + 量≥1.75×前3日均量(首次)      [原富途]

统一交易管理(隔离出进场差异): 进场=当根收盘; 止损=进场−2×ATR; 出场=止损/跌破EMA20/满40根;
不重叠持仓。量能基准=爆量前3日均量(今日量÷前3日均量)。

用法: python3 compare_entries.py NVDA,AVGO,AMD,... [SECTOR]
仅用标准库, 复用 signals.py/parabolic.py。
"""
import sys, os
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
import parabolic as pb
import signals as sg

# 公共常量/指标/回测原语统一来自 core (本模块为 3 方进场对比的研究脚本)
from core import MAXHOLD, WARMUP, STOP_ATR, RNG, atr_series, rvol_series, run, stats


def gen_huicai(sym, C, H, L, V):
    idx = []
    for i in range(WARMUP, len(C) - 1):
        sig = sg.analyze(sym, (C[:i + 1], H[:i + 1], L[:i + 1], V[:i + 1]))
        if sig and '双腿' in sig['verdict']:
            idx.append(i)
    return idx


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


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    syms = sys.argv[1].replace(',', ' ').split()
    pools = {'A 回踩重启(缠论)': [], 'B DUAL(穿越)': [], 'C SDUAL(站上)': []}
    for s in syms:
        st = pb.fetch_dated(s.upper(), RNG)
        if not st:
            continue
        D, C, H, L, V = st
        e5, e10, e20 = sg.ema_series(C, 5), sg.ema_series(C, 10), sg.ema_series(C, 20)
        atr = atr_series(C, H, L); rv = rvol_series(V, 3)
        pools['A 回踩重启(缠论)'] += run(gen_huicai(s.upper(), C, H, L, V), C, H, L, e20, atr)
        pools['B DUAL(穿越)'] += run(gen_dual(C, e5, e10, e20, rv), C, H, L, e20, atr)
        pools['C SDUAL(站上)'] += run(gen_sdual(C, e5, e10, e20, rv), C, H, L, e20, atr)

    print(f"====== 进场三方对比 · {len(syms)}只 · {RNG} · 量基准=前3日均量 · 统一止损/出场 ======")
    print(f"{'方案':<18}{'样本':>5}{'胜率':>6}{'期望R':>7}{'平均%/笔':>9}{'持仓天':>7}")
    print('-' * 56)
    for name, tr in pools.items():
        s = stats(tr)
        if not s:
            print(f"{name:<18}  无样本"); continue
        print(f"{name:<18}{s['n']:>5}{s['wr']*100:>5.0f}%{s['exp']:>+7.2f}{s['avgpct']:>+8.1f}%{s['avgbars']:>6.0f}")
    print("\n注: 三套用完全相同的止损(−2ATR)/出场(破EMA20/40天)/不重叠, 差异纯来自进场触发。")
    print("    期望R>0=长期正收益; 平均%/笔=满仓单笔实际收益。")


if __name__ == "__main__":
    main()
