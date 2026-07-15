#!/usr/bin/env python3
"""
验证两件事:
  ① 筑底闸门是否让 DUAL 更肥:  裸DUAL(深调) vs DUAL(深调)+筑底完成闸门
  ② SDUAL点火版是否有 edge:    已缓慢转强 + 突然暴量(≥2.5×前3日均量)

筑底完成闸门 base_ready(全成立):
  均线纠缠  (max(E5,E10,E20)−min)/C < 4%   —— 下跌散开、筑底缠绕
  波动收缩  ATR(10)/ATR(60) < 0.9          —— 大圆底末端振幅缩窄(VCP)
  均线走平  EMA20 现值 ≥ EMA20(10日前)      —— 从缓跌转平, 不再新低

SDUAL点火 gen_sdual_ignition:
  站上E20 且 E20上行 且 近15日多数在E20上(已缓慢转强) 且 今日量≥2.5×前3日均量(突然暴量, 首日)

统一止损-2ATR/出场破EMA20/40天。用法: python3 base_validate.py TICKERS
"""
import sys, os
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
import parabolic as pb
import signals as sg
from compare_entries import atr_series, rvol_series, run, stats, WARMUP, RNG
from dual_context import hh_series, gen_dual


def base_ready(i, C, H, L, e5, e10, e20):
    """查突破【之前】那段窗口有没有筑底(纠缠+窄幅+走平), 而非突破当根。"""
    w = range(i - 20, i - 3)
    min_spread = min((max(e5[j], e10[j], e20[j]) - min(e5[j], e10[j], e20[j])) / C[j] for j in w)
    converged = min_spread < 0.04                                    # 期间均线曾纠缠
    rng = (max(H[j] for j in w) - min(L[j] for j in w)) / C[i]
    narrow = rng < 0.25                                              # 期间窄幅盘整
    turned = e20[i] >= e20[i - 12]                                   # EMA20 从底走平/上翘
    return converged and narrow and turned


def gen_sdual_ignition(C, e20, rv):
    idx = []
    for i in range(WARMUP, len(C) - 1):
        above = C[i] > e20[i]
        rising = e20[i] > e20[i - 10]
        recovering = sum(1 for j in range(i - 14, i + 1) if C[j] > e20[j]) >= 10
        surge = rv[i] >= 2.5
        fresh = rv[i - 1] < 2.5
        if above and rising and recovering and surge and fresh:
            idx.append(i)
    return idx


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    syms = sys.argv[1].replace(',', ' ').split()
    pools = {'DUAL深调(裸)': [], 'DUAL深调+筑底闸门': [], 'SDUAL点火(暴量2.5x)': []}
    for s in syms:
        st = pb.fetch_dated(s.upper(), RNG)
        if not st:
            continue
        D, C, H, L, V = st
        e5, e10, e20 = sg.ema_series(C, 5), sg.ema_series(C, 10), sg.ema_series(C, 20)
        atr14 = atr_series(C, H, L, 14); a10 = atr_series(C, H, L, 10); a60 = atr_series(C, H, L, 60)
        rv = rvol_series(V, 3); hh = hh_series(H, 252)
        dist = [(hh[i] - C[i]) / hh[i] * 100 for i in range(len(C))]

        dual = [i for i in gen_dual(C, e5, e10, e20, rv) if dist[i] > 25]
        dual_base = [i for i in dual if base_ready(i, C, H, L, e5, e10, e20)]
        ign = gen_sdual_ignition(C, e20, rv)

        pools['DUAL深调(裸)'] += run(dual, C, H, L, e20, atr14)
        pools['DUAL深调+筑底闸门'] += run(dual_base, C, H, L, e20, atr14)
        pools['SDUAL点火(暴量2.5x)'] += run(ign, C, H, L, e20, atr14)

    print(f"====== 筑底闸门 + SDUAL点火 验证 · {len(syms)}只 · {RNG} ======")
    print(f"{'方案':<22}{'样本':>5}{'胜率':>6}{'期望R':>7}{'平均%/笔':>9}{'持仓天':>7}")
    print('-' * 58)
    for name, tr in pools.items():
        s = stats(tr)
        if not s:
            print(f"{name:<22}  无样本"); continue
        print(f"{name:<22}{s['n']:>5}{s['wr']*100:>5.0f}%{s['exp']:>+7.2f}{s['avgpct']:>+8.1f}%{s['avgbars']:>6.0f}")
    print("\n① 若'+筑底闸门'期望明显>'裸', 证明筑底确认(纠缠+缩量+走平)加分。")
    print("② SDUAL点火>0 即'已转强+暴量'那一下值得抓, 不漏掉。")


if __name__ == "__main__":
    main()
