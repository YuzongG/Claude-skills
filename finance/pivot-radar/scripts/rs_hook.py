#!/usr/bin/env python3
"""
RS 回踩翘头信号验证 (固定持有 20/40/60 天)。
RS线 = 个股收盘 / SPY收盘。 翘头 = RS 收回其 10 日EMA 且 RS 在 50 日EMA 上方(相对趋势未破)。
对比回踩重启, 看这个"相对强度择时"信号有没有独立价值。
可选叠价格过滤(收盘>EMA50, 排除相对强但绝对下跌的票)。
用法: python3 rs_hook.py [START]
"""
import sys, os, datetime, concurrent.futures
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
import parabolic as pb
import signals as sg
from compare_entries import RNG
from universe_validate import SECTORS

START = None
_spy = None
WARMUP = 90


def process(item):
    sector, sym = item
    st = pb.fetch_dated(sym, RNG)
    if not st or len(st[1]) < 140:
        return []
    D, C, H, L, V = st
    pmap = {_spy[0][k]: _spy[1][k] for k in range(len(_spy[0]))}
    keep = [k for k in range(len(D)) if D[k] in pmap]
    if len(keep) < 140:
        return []
    aD = [D[k] for k in keep]; aC = [C[k] for k in keep]; aH = [H[k] for k in keep]
    aL = [L[k] for k in keep]; aV = [V[k] for k in keep]; aP = [pmap[D[k]] for k in keep]
    rs = [aC[i] / aP[i] for i in range(len(aC))]
    rs10, rs50 = sg.ema_series(rs, 10), sg.ema_series(rs, 50)
    e50 = sg.ema_series(aC, 50)
    n = len(aC); out = []
    for i in range(WARMUP, n):
        if i + 60 >= n:
            continue
        reclaim = rs[i] > rs10[i] and rs[i - 1] <= rs10[i - 1]     # RS翘头
        leader = rs[i] > rs50[i]                                    # 相对趋势未破
        if not (reclaim and leader):
            continue
        if START and aD[i] < START:
            continue
        para = pb.score_core(aC[:i + 1], aH[:i + 1], aL[:i + 1], aV[:i + 1])
        if para and para['total'] >= 55:
            continue
        out.append(dict(price_ok=aC[i] > e50[i],
                        r20=(aC[i + 20] / aC[i] - 1) * 100,
                        r40=(aC[i + 40] / aC[i] - 1) * 100,
                        r60=(aC[i + 60] / aC[i] - 1) * 100))
    return out


def line(label, tr):
    if not tr:
        print(f"  {label:<20} 无样本"); return

    def f(k):
        m = len(tr); w = sum(1 for t in tr if t[k] > 0) / m * 100; a = sum(t[k] for t in tr) / m
        return f"胜{w:>3.0f}% 利{a:>+5.1f}%"
    print(f"  {label:<20} n={len(tr):>4}  20天[{f('r20')}]  40天[{f('r40')}]  60天[{f('r60')}]")


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
    print(f"回测 {len(tasks)} 只 RS回踩翘头...", file=sys.stderr)
    allt = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(process, tasks):
            allt += r

    tag = f"(自 {START})" if START else "(全2年)"
    print(f"\n====== RS 回踩翘头 · 固定持有 {tag} · {len(tasks)}只 ======")
    line('RS翘头(全部)', allt)
    line('RS翘头 + 价格>EMA50', [t for t in allt if t['price_ok']])
    print("\n对照 回踩重启(全2年双腿): 20天胜53%/+1.5% · 40天胜54%/+3.1% · 60天胜54%/+5.0%")
    print("注: RS线=个股/SPY; 翘头=收回RS的10EMA且RS>50EMA; 纯持有不止损。")


if __name__ == "__main__":
    main()
