#!/usr/bin/env python3
"""
拐点雷达 ⑤ 总编排 —— 出两张表(当前信号扫描, 延迟一根确认)。
  表1 强势股入场:
     · 双腿+RS≥B (胜率王): 抬高底+回踩重启, 且个股 RS≥B
     · RS翘头   (利润王): RS线(个股/SPY)收回10EMA 且 >50EMA, 按 RS 等级排序
     过热(Parabolic≥55)的照常列出, 标注"⚠️可能过热"(不删)。
  表2 板块驱动: 按板块 3M×1W 强弱 → 强势领先=SDUAL点火 / 弱转强=DUAL筑底突破 / 其余skip。
用法: python3 scan.py                 (扫自带 ~200 只 + 板块分类)
      python3 scan.py NVDA,PANW,...    (扫指定, 仅表1)
仅标准库 + Yahoo。复用同目录各模块。
"""
import sys, os, datetime, concurrent.futures
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
import parabolic as pb
import signals as sg
from core import (SECTORS, SECT_ETF, RECENT, atr_series, rvol_series, hh_series,
                  gen_huicai, gen_dual_fresh, gen_sdual_ignition)

_spy = None
_etf = {}


def ret(a, n):
    return (a[-1] / a[-n - 1] - 1) * 100 if len(a) > n else 0


def sector_state(etf_fd):
    """按 3M×1W 相对 SPY 判板块 → (模式, 描述)。"""
    if not etf_fd or not _spy:
        return ('skip', '无数据')
    e, p = etf_fd[1], _spy[1]
    ex3, ex1 = ret(e, 63) - ret(p, 63), ret(e, 5) - ret(p, 5)
    tag = f'3M{ex3:+.0f}/1W{ex1:+.0f}'
    if ex3 > 0 and ex1 > 0: return ('SDUAL', f'强势领先({tag})')
    if ex3 <= 0 and ex1 > 0: return ('DUAL', f'弱转强({tag})')
    if ex3 > 0 and ex1 <= 0: return ('skip', f'见顶转弱({tag})')
    return ('skip', f'仍弱({tag})')


def align_spy(D, C):
    pmap = {_spy[0][k]: _spy[1][k] for k in range(len(_spy[0]))}
    keep = [k for k in range(len(D)) if D[k] in pmap]
    return [C[k] for k in keep], [pmap[D[k]] for k in keep]


def scan_one(item):
    sector, sym = item
    st = pb.fetch_dated(sym, "1y")
    if not st or len(st[1]) < 140:
        return None
    D, C, H, L, V = st
    n = len(C)
    e5, e10, e20 = sg.ema_series(C, 5), sg.ema_series(C, 10), sg.ema_series(C, 20)
    atr = atr_series(C, H, L)
    para = pb.score_core(C, H, L, V)
    pscore = para['total'] if para else 0
    rsg = sg.rs_grade(st, _spy, _etf.get(SECT_ETF.get(sector)))
    t1 = []

    # 表1a RS翘头
    aC, aP = align_spy(D, C)
    if len(aC) >= 60:
        rs = [aC[i] / aP[i] for i in range(len(aC))]
        r10, r50 = sg.ema_series(rs, 10), sg.ema_series(rs, 50)
        m = len(rs)
        for k in range(m - 1, max(0, m - 1 - RECENT), -1):
            if rs[k] > r10[k] and rs[k - 1] <= r10[k - 1] and rs[k] > r50[k]:
                t1.append('RS翘头'); break

    # 表1b 双腿+RS≥B
    for i, lo, two in gen_huicai(C, H, L, e5, e10, e20, atr, bots := sg.find_fractals(sg.merge_inclusion(H, L))[1]):
        if two and i >= n - RECENT and rsg and rsg['total'] >= 60:
            t1.append('双腿'); break

    res = {'sym': sym, 'sector': sector, 'pscore': pscore, 'rs': rsg, 't1': t1}
    return res, (C, H, L, V, e5, e10, e20, atr)


def check_table2(arrays, mode):
    C, H, L, V, e5, e10, e20, atr = arrays
    n = len(C); rv = rvol_series(V, 3)
    if mode == 'SDUAL':
        ign = gen_sdual_ignition(C, e20, rv)
        if ign and ign[-1] >= n - RECENT:
            return 'SDUAL点火(暴量)'
    elif mode == 'DUAL':
        hh = hh_series(H, 252)
        dist = [(hh[i] - C[i]) / hh[i] * 100 for i in range(n)]
        dual = [i for i in gen_dual_fresh(C, e5, e10, e20, rv) if dist[i] > 25]
        if dual and dual[-1] >= n - RECENT:
            return 'DUAL筑底突破'
    return None


def rstxt(r):
    return f"{r['rs']['grade']}({r['rs']['total']:.0f})" if r['rs'] else '—'


def hot(r):
    return ' ⚠️可能过热' if r['pscore'] >= 55 else ''


def rs_char(r):
    """RS 性质: 全能(攻守都强) / 领涨型(能冲抗跌弱, 板块弱时真弱) / 防守型(抗跌强不领涨)。"""
    rs = r['rs']
    if not rs:
        return '—'
    s2, s3 = rs['s2'], rs['s3']            # s2=抗跌 s3=领涨
    if s2 >= 70 and s3 >= 70:
        return '全能'
    if s3 >= 70:
        return '领涨型⚠脆'
    if s2 >= 70:
        return '防守型'
    return '杂'


def dcaptxt(r):
    return f"{r['rs']['dcap']:+.2f}" if r['rs'] else '—'


def main():
    global _spy, _etf
    custom = sys.argv[1].replace(',', ' ').split() if len(sys.argv) > 1 else None
    sect_arg = sys.argv[2].upper() if len(sys.argv) > 2 else None
    print("拉 SPY + 板块ETF...", file=sys.stderr)
    _spy = pb.fetch_dated('SPY', '1y')
    for e in set(SECT_ETF.values()):
        _etf[e] = pb.fetch_dated(e, '1y')
    states = {sec: sector_state(_etf.get(SECT_ETF.get(sec))) for sec in SECTORS}

    if custom:
        if sect_arg:                       # 指定板块ETF: 用作 RS 第二基准 + 表2 板块状态
            sec_label = {v: k for k, v in SECT_ETF.items()}.get(sect_arg, sect_arg)
            SECT_ETF[sec_label] = sect_arg
            if sect_arg not in _etf:
                _etf[sect_arg] = pb.fetch_dated(sect_arg, '1y')
            states[sec_label] = sector_state(_etf.get(sect_arg))
            tasks = [(sec_label, s.upper()) for s in custom]
        else:
            tasks = [('自选', s.upper()) for s in custom]
    else:
        seen = set(); tasks = []
        for sec, syms in SECTORS.items():
            for s in syms:
                if s not in seen:
                    seen.add(s); tasks.append((sec, s))
    print(f"扫描 {len(tasks)} 只...", file=sys.stderr)

    t1_rows, t2_rows = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        for out in ex.map(scan_one, tasks):
            if not out:
                continue
            res, arrays = out
            if res['t1']:
                t1_rows.append(res)
            mode = states.get(res['sector'], ('skip', ''))[0]
            if mode in ('SDUAL', 'DUAL'):
                sig = check_table2(arrays, mode)
                if sig:
                    res['t2'] = (sig, states[res['sector']][1])
                    t2_rows.append(res)

    def rstot(r): return r['rs']['total'] if r['rs'] else 0
    legs = sorted([r for r in t1_rows if '双腿' in r['t1']], key=rstot, reverse=True)
    hooks = sorted([r for r in t1_rows if 'RS翘头' in r['t1']], key=rstot, reverse=True)

    print(f"\n{'='*66}\n拐点雷达扫描 · {datetime.date.today()} · {len(tasks)}只\n{'='*66}")

    def row(r):
        return (f"    {r['sym']:<6}{r['sector']:<8}RS {rstxt(r):<7}{rs_char(r):<8}"
                f"下行{dcaptxt(r):<6}Para {r['pscore']:>3.0f}{hot(r)}")
    print("\n📈 表1 · 强势股入场   (RS性质: 全能/领涨型⚠脆/防守型; 下行=下行捕获, 越低越抗跌)")
    print(f"\n  ▸ 双腿+RS≥B (胜率王, {len(legs)}只):")
    if legs:
        for r in legs:
            print(row(r))
    else:
        print("    今日无触发")
    print(f"\n  ▸ RS翘头 (利润王, 按RS排序, {len(hooks)}只):")
    if hooks:
        for r in hooks[:25]:
            print(row(r))
        if len(hooks) > 25:
            print(f"    …另 {len(hooks)-25} 只(略)")
    else:
        print("    今日无触发")

    print("\n📉 表2 · 板块驱动 (强势→SDUAL点火 / 弱转强→DUAL筑底)")
    if t2_rows:
        for r in t2_rows:
            print(f"    {r['sym']:<6}{r['sector']:<8}{r['t2'][0]:<16}[{r['t2'][1]}]  Para {r['pscore']:>3.0f}{hot(r)}")
    else:
        print("    今日无触发")

    print("\n板块状态 (3M水平 × 1W方向):")
    for sec, (mode, desc) in sorted(states.items(), key=lambda x: x[1][0]):
        print(f"    {sec:<8}{desc:<22}→ {mode}")
    print("\n免责: 基于历史价量客观规则, 仅研究参考非投资建议; 信号延迟一根确认, 强势有有效期请滚动复评。")


if __name__ == "__main__":
    main()
