#!/usr/bin/env python3
"""
B 共振测试: 价格双腿(回踩重启) + RS强势(翘头/领先) 同时成立, 对比各自单独。
  价格双腿  = 抬高底 + 回踩重启 (缠论+均线)
  RS强势    = RS线(个股/SPY) > 其10EMA 且 > 50EMA (相对领先且向上)
  RS翘头单独 = RS 收回10EMA当根 且 RS>50EMA
  共振      = 价格双腿 且 当根 RS强势
固定持有 20/40/60 天, 不止损。 用法: python3 rs_confluence.py [START]
"""
import sys, os, datetime, concurrent.futures
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
import parabolic as pb
import signals as sg
from compare_entries import RNG
from universe_validate import SECTORS
from table1_validate import gen_huicai, atr_series

START = None
_spy = None
WARMUP = 90


def fwd(aC, i):
    return dict(r20=(aC[i + 20] / aC[i] - 1) * 100, r40=(aC[i + 40] / aC[i] - 1) * 100,
               r60=(aC[i + 60] / aC[i] - 1) * 100)


def process(item):
    sector, sym = item
    st = pb.fetch_dated(sym, RNG)
    if not st or len(st[1]) < 140:
        return ([], [], [])
    D, C, H, L, V = st
    pmap = {_spy[0][k]: _spy[1][k] for k in range(len(_spy[0]))}
    keep = [k for k in range(len(D)) if D[k] in pmap]
    if len(keep) < 140:
        return ([], [], [])
    aD = [D[k] for k in keep]; aC = [C[k] for k in keep]; aH = [H[k] for k in keep]
    aL = [L[k] for k in keep]; aV = [V[k] for k in keep]; aP = [pmap[D[k]] for k in keep]
    rs = [aC[i] / aP[i] for i in range(len(aC))]
    rs10, rs50 = sg.ema_series(rs, 10), sg.ema_series(rs, 50)
    e5, e10, e20 = sg.ema_series(aC, 5), sg.ema_series(aC, 10), sg.ema_series(aC, 20)
    atr = atr_series(aC, aH, aL)
    bots = sg.find_fractals(sg.merge_inclusion(aH, aL))[1]
    two_leg = set(i for i, lo, two in gen_huicai(aC, aH, aL, e5, e10, e20, atr, bots) if two)
    n = len(aC)
    price_l, rshook_l, conf_l = [], [], []

    def veto(i):
        p = pb.score_core(aC[:i + 1], aH[:i + 1], aL[:i + 1], aV[:i + 1])
        return p and p['total'] >= 55
    for i in range(WARMUP, n):
        if i + 60 >= n or (START and aD[i] < START):
            continue
        rs_strong = rs[i] > rs10[i] and rs[i] > rs50[i]
        rs_hook = rs[i] > rs10[i] and rs[i - 1] <= rs10[i - 1] and rs[i] > rs50[i]
        price = i in two_leg
        if not (price or rs_hook):
            continue
        if veto(i):
            continue
        f = fwd(aC, i)
        if price:
            price_l.append(f)
        if rs_hook:
            rshook_l.append(f)
        if price and rs_strong:
            conf_l.append(f)
    return (price_l, rshook_l, conf_l)


def line(label, tr):
    if not tr:
        print(f"  {label:<18} 无样本"); return

    def f(k):
        m = len(tr); w = sum(1 for t in tr if t[k] > 0) / m * 100; a = sum(t[k] for t in tr) / m
        return f"胜{w:>3.0f}% 利{a:>+5.1f}%"
    print(f"  {label:<18} n={len(tr):>4}  20天[{f('r20')}]  40天[{f('r40')}]  60天[{f('r60')}]")


def main():
    global START, _spy
    if len(sys.argv) > 1:
        START = datetime.date.fromisoformat(sys.argv[1])
    print("拉 SPY...", file=sys.stderr)
    _spy = pb.fetch_dated('SPY', RNG)
    seen = set(); tasks = []
    for sec, syms in SECTORS.items():
        for s in syms:
            if s not in seen:
                seen.add(s); tasks.append((sec, s))
    print(f"回测 {len(tasks)} 只...", file=sys.stderr)
    P, R, Cf = [], [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for p, r, c in ex.map(process, tasks):
            P += p; R += r; Cf += c
    tag = f"(自 {START})" if START else "(全2年)"
    print(f"\n====== B 共振测试 {tag} · {len(tasks)}只 ======")
    line('价格双腿(单独)', P)
    line('RS翘头(单独)', R)
    line('★共振(双腿+RS强)', Cf)
    print("\n注: 纯持有不止损; 共振=价格双腿入场当根 RS 也在10/50EMA之上。")


if __name__ == "__main__":
    main()
