#!/usr/bin/env python3
"""
DUAL(新鲜从下方突破版) 分板块 · 加闸门 vs 不加闸门。
新鲜定义: 上穿EMA20当根 + 突破前10天至少6天在EMA20【下方】(排除"早就站上很久"的延续)。
闸门 = base_ready(突破前窗口 均线纠缠+窄幅+EMA20走平)。
统一止损-2ATR/出场破EMA20/40天; 量=前3日均量。
用法: python3 sector_dual.py
"""
import sys, os
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
import parabolic as pb
import signals as sg
from compare_entries import atr_series, rvol_series, run, stats, WARMUP, RNG
from base_validate import base_ready

SECTORS = {
    '半导体':   ['NVDA', 'AVGO', 'AMD', 'MU', 'AMAT', 'ASML', 'TXN', 'LRCX', 'KLAC', 'ADI', 'QCOM', 'MRVL', 'CDNS', 'SNPS', 'MPWR', 'NXPI', 'TER', 'ARM'],
    '网络安全': ['PANW', 'FTNT', 'CRWD', 'NET', 'OKTA', 'ZS', 'DDOG', 'CYBR', 'QLYS', 'TENB', 'S', 'GEN'],
    '软件云':   ['CRM', 'ADBE', 'ORCL', 'NOW', 'INTU', 'SNOW', 'TEAM', 'WDAY', 'PLTR', 'MDB', 'HUBS', 'PATH'],
    '高波动成长': ['COIN', 'MSTR', 'ROKU', 'RBLX', 'U', 'AFRM', 'SOFI', 'CVNA', 'DKNG', 'ABNB', 'SHOP', 'TWLO'],
}


def gen_dual_fresh(C, e5, e10, e20, rv):
    idx = []
    for i in range(WARMUP, len(C) - 1):
        if not (e5[i] > e10[i] and C[i] > e20[i] and C[i - 1] <= e20[i - 1] and rv[i] >= 1.5):
            continue
        days_below = sum(1 for j in range(i - 10, i) if C[j] < e20[j])
        if days_below >= 6:                      # 突破前多数在EMA20下方=新鲜从下方冒出
            idx.append(i)
    return idx


def line(label, s):
    if not s:
        print(f"    {label:<12} 无样本"); return
    print(f"    {label:<12} n={s['n']:>3}  胜率{s['wr']*100:>3.0f}%  期望{s['exp']:>+5.2f}R  平均每笔{s['avgpct']:>+5.1f}%")


def main():
    print(f"====== DUAL(新鲜从下方突破) 分板块 · ±筑底闸门 · {RNG} ======")
    tot_ng, tot_g = [], []
    for name, syms in SECTORS.items():
        ng, g = [], []
        for s in syms:
            st = pb.fetch_dated(s, RNG)
            if not st:
                continue
            D, C, H, L, V = st
            e5, e10, e20 = sg.ema_series(C, 5), sg.ema_series(C, 10), sg.ema_series(C, 20)
            atr = atr_series(C, H, L, 14); rv = rvol_series(V, 3)
            idx = gen_dual_fresh(C, e5, e10, e20, rv)
            idxg = [i for i in idx if base_ready(i, C, H, L, e5, e10, e20)]
            ng += run(idx, C, H, L, e20, atr)
            g += run(idxg, C, H, L, e20, atr)
        print(f"\n【{name}】")
        line('不加闸门', stats(ng))
        line('加闸门', stats(g))
        tot_ng += ng; tot_g += g
    print(f"\n【全部合计】")
    line('不加闸门', stats(tot_ng))
    line('加闸门', stats(tot_g))
    print("\n注: 新鲜=突破前10天≥6天在EMA20下方; 闸门=突破前窗口纠缠+窄幅+走平。样本少的板块仅供参考。")


if __name__ == "__main__":
    main()
