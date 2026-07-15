#!/usr/bin/env python3
"""
表1 验算 —— RS龙头(A/B) + 回踩重启, 大universe(~198只)。
回踩重启 = 底分型确认(延迟一根) + 抬高底/回踩重启 + 趋势未破(E10>E20,C>E20)
          + 回档≥1.2ATR + Parabolic<55(不追高)。 止损=底分型低点; 出场=破EMA20/40天。
按 RS 等级分组, 重点看 [双腿 + RS≥B] 这个默认过滤的胜率/期望/每笔%。
用法: python3 table1_validate.py [START]
"""
import sys, os, datetime, concurrent.futures
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
import parabolic as pb
import signals as sg
from compare_entries import stats, MAXHOLD, WARMUP, RNG
from universe_validate import SECTORS

SECT_ETF = {'半导体': 'SMH', '网络安全': 'CIBR', '软件': 'IGV', '生科': 'XBI', '金融': 'XLF',
            '医疗': 'XLV', '能源': 'XLE', '工业': 'XLI', '消费可选': 'XLY', '成长高波动': 'QQQ'}
START = None
_spy = None
_etf = {}


def atr_series(C, H, L, n=14):
    tr = [H[0] - L[0]] + [max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1])) for i in range(1, len(C))]
    return [sum(tr[max(0, i - n + 1):i + 1]) / (i - max(0, i - n + 1) + 1) for i in range(len(C))]


def gen_huicai(C, H, L, e5, e10, e20, atr, bots):
    """预计算分型版回踩重启; 返回 [(entry_idx, 止损低点, 是否双腿)]。"""
    out = []; prev_low = None
    for ci, lo, cf in bots:
        i = cf                                   # 确认那根进场(延迟一根)
        if WARMUP <= i < len(C) - 1:
            trend_ok = e10[i] > e20[i] and C[i] > e20[i]
            reclaim = C[i] > e5[i]
            hl = prev_low is not None and lo > prev_low
            rhi = max(C[max(0, ci - 10):ci + 1])
            pb_atr = (rhi - lo) / atr[i] if atr[i] > 0 else 0
            if trend_ok and pb_atr >= 1.2 and (hl or reclaim):
                out.append((i, lo, hl and reclaim))
        prev_low = lo
    return out


def process(item):
    sector, sym = item
    st = pb.fetch_dated(sym, RNG)
    if not st or len(st[1]) < 140:
        return []
    D, C, H, L, V = st
    e5, e10, e20 = sg.ema_series(C, 5), sg.ema_series(C, 10), sg.ema_series(C, 20)
    atr = atr_series(C, H, L)
    tops, bots = sg.find_fractals(sg.merge_inclusion(H, L))
    topcf = set(cf for _, _, cf in tops)              # 顶分型确认位置
    trades = []; last_exit = -1
    for i, lo, two in gen_huicai(C, H, L, e5, e10, e20, atr, bots):
        if i <= last_exit:
            continue
        if START and D[i] < START:
            continue
        para = pb.score_core(C[:i + 1], H[:i + 1], L[:i + 1], V[:i + 1])
        if para and para['total'] >= 55:            # 追高否决
            continue
        rs = sg.rs_grade((D[:i + 1], C[:i + 1], H[:i + 1], L[:i + 1], V[:i + 1]), _spy, _etf.get(SECT_ETF.get(sector)))
        entry = C[i]; stop = lo if lo < entry else entry * 0.97; risk = entry - stop
        # 出场A: 破EMA20; 出场B: 顶分型出 (都带 止损/40天 保底)
        exA = exB = None
        for j in range(i + 1, len(C)):
            hit_stop = L[j] <= stop
            if exA is None:
                if hit_stop: exA = (stop, j)
                elif C[j] < e20[j]: exA = (C[j], j)
                elif j - i >= MAXHOLD: exA = (C[j], j)
            if exB is None:
                if hit_stop: exB = (stop, j)
                elif j in topcf: exB = (C[j], j)
                elif j - i >= MAXHOLD: exB = (C[j], j)
            if exA and exB: break
        if exA is None: exA = (C[-1], len(C) - 1)
        if exB is None: exB = (C[-1], len(C) - 1)
        rsg = 'RS≥B' if (rs and rs['total'] >= 60) else 'RS<B'
        trades.append(dict(kind='双腿' if two else '单腿', rs=rsg,
                           Re=(exA[0] - entry) / risk, pe=(exA[0] - entry) / entry * 100, be=exA[1] - i,
                           Rd=(exB[0] - entry) / risk, pd=(exB[0] - entry) / entry * 100, bd=exB[1] - i))
        last_exit = exA[1]
    return trades


def st(tr, R, P, B):
    if not tr:
        return None
    n = len(tr); wins = [t for t in tr if t[R] > 0]
    return dict(n=n, wr=len(wins) / n, exp=sum(t[R] for t in tr) / n,
                pct=sum(t[P] for t in tr) / n, bars=sum(t[B] for t in tr) / n)


def line(label, tr):
    a = st(tr, 'Re', 'pe', 'be'); b = st(tr, 'Rd', 'pd', 'bd')
    if not a:
        print(f"  {label:<14} 无样本"); return
    print(f"  {label:<14} n={a['n']:>4} | 破EMA20: 胜{a['wr']*100:>3.0f}% 期望{a['exp']:>+5.2f}R 每笔{a['pct']:>+5.1f}% 持{a['bars']:.0f}天"
          f" | 顶分型出: 胜{b['wr']*100:>3.0f}% 期望{b['exp']:>+5.2f}R 每笔{b['pct']:>+5.1f}% 持{b['bars']:.0f}天")


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
    print(f"回测 {len(tasks)} 只回踩重启...", file=sys.stderr)
    allt = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(process, tasks):
            allt += r

    tag = f"(自 {START})" if START else "(全2年)"
    print(f"\n====== 表1 回踩重启 验算 {tag} · {len(tasks)}只 · {RNG} ======")
    print("\n--- 全部回踩重启 ---")
    line('全部', allt)
    print("\n--- 按信号腿数 ---")
    for k in ['双腿', '单腿']:
        line(k, [t for t in allt if t['kind'] == k])
    print("\n--- 按 RS 过滤 ---")
    for g in ['RS≥B', 'RS<B']:
        line(g, [t for t in allt if t['rs'] == g])
    print("\n--- 表1 默认过滤 ---")
    line('双腿+RS≥B', [t for t in allt if t['kind'] == '双腿' and t['rs'] == 'RS≥B'])
    line('回踩重启+RS≥B', [t for t in allt if t['rs'] == 'RS≥B'])
    print("\n注: R=以底分型止损为1单位风险; 样本≥30才算稳健。")


if __name__ == "__main__":
    main()
