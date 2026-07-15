#!/usr/bin/env python3
"""
表1 回踩重启 —— 固定持有 20/40/60 天的胜率 & 利润率 (纯持有, 不止损)。
入场=回踩重启(底分型确认+抬高底/回踩重启+趋势未破+回档≥1.2ATR+Parabolic<55)。
利润率 = (第N天收盘/入场收盘 − 1); 胜率 = N天后为正的比例。
用法: python3 table1_hold.py [START]
"""
import sys, os, datetime, concurrent.futures
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
import parabolic as pb
import signals as sg
from compare_entries import RNG
from universe_validate import SECTORS
from table1_validate import gen_huicai, atr_series, SECT_ETF

START = None
_spy = None
_etf = {}


def process(item):
    sector, sym = item
    st = pb.fetch_dated(sym, RNG)
    if not st or len(st[1]) < 140:
        return []
    D, C, H, L, V = st
    e5, e10, e20 = sg.ema_series(C, 5), sg.ema_series(C, 10), sg.ema_series(C, 20)
    atr = atr_series(C, H, L)
    bots = sg.find_fractals(sg.merge_inclusion(H, L))[1]
    out = []
    n = len(C)
    for i, lo, two in gen_huicai(C, H, L, e5, e10, e20, atr, bots):
        if START and D[i] < START:
            continue
        if i + 60 >= n:                       # 需要 60 天前瞻, 三个周期用同一批交易
            continue
        para = pb.score_core(C[:i + 1], H[:i + 1], L[:i + 1], V[:i + 1])
        if para and para['total'] >= 55:
            continue
        rs = sg.rs_grade((D[:i + 1], C[:i + 1], H[:i + 1], L[:i + 1], V[:i + 1]), _spy, _etf.get(SECT_ETF.get(sector)))
        rsg = 'RS≥B' if (rs and rs['total'] >= 60) else 'RS<B'
        out.append(dict(kind='双腿' if two else '单腿', rs=rsg,
                        r20=(C[i + 20] / C[i] - 1) * 100,
                        r40=(C[i + 40] / C[i] - 1) * 100,
                        r60=(C[i + 60] / C[i] - 1) * 100))
    return out


def line(label, tr):
    if not tr:
        print(f"  {label:<14} 无样本"); return

    def f(k):
        m = len(tr); w = sum(1 for t in tr if t[k] > 0) / m * 100; a = sum(t[k] for t in tr) / m
        return f"胜{w:>3.0f}% 利{a:>+5.1f}%"
    print(f"  {label:<14} n={len(tr):>4}  20天[{f('r20')}]  40天[{f('r40')}]  60天[{f('r60')}]")


def main():
    global START, _spy, _etf
    if len(sys.argv) > 1:
        START = datetime.date.fromisoformat(sys.argv[1])
    print("拉基准 ETF...", file=sys.stderr)
    _spy = pb.fetch_dated('SPY', RNG)
    for e in set(SECT_ETF.values()):
        _etf[e] = pb.fetch_dated(e, RNG)
    seen = set(); tasks = []
    for sec, syms in SECTORS.items():
        for s in syms:
            if s not in seen:
                seen.add(s); tasks.append((sec, s))
    print(f"回测 {len(tasks)} 只...", file=sys.stderr)
    allt = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(process, tasks):
            allt += r

    tag = f"(自 {START})" if START else "(全2年)"
    print(f"\n====== 表1 回踩重启 · 固定持有胜率/利润率 {tag} · {len(tasks)}只 ======")
    line('全部', allt)
    line('双腿', [t for t in allt if t['kind'] == '双腿'])
    line('单腿', [t for t in allt if t['kind'] == '单腿'])
    line('RS≥B', [t for t in allt if t['rs'] == 'RS≥B'])
    line('RS<B', [t for t in allt if t['rs'] == 'RS<B'])
    line('双腿+RS≥B', [t for t in allt if t['kind'] == '双腿' and t['rs'] == 'RS≥B'])
    print("\n注: 纯持有N天不止损; 胜率=N天后为正比例, 利=平均每笔%收益。")


if __name__ == "__main__":
    main()
