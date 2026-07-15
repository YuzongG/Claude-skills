#!/usr/bin/env python3
"""
拐点雷达 信号层④ —— 回测期望引擎。

把 ③ 的信号在历史上一根根往前走(无未来函数, 复用 analyze 的切片能力), 每个进场信号
模拟一笔交易, 用 R 倍数记赚亏, 汇总出每类信号的【胜率/平均R/期望值】。
核心: 用期望值(非胜率)判断信号值不值得下手; 并按 RS 分组, 验证 RS 过滤到底加不加分。

用法:
  python3 backtest.py PANW,FTNT,CRWD,NET,OKTA,ZS,RBRK,DDOG,DT [SECTOR_ETF]
    多只票池化统计; 第二参数=板块 ETF(作 RS 第二基准, 选填)。

交易规则(ATR/结构化, 待自身校准):
  进场 = 📈 信号触发, 以当根收盘买入(不重叠持仓)。
  止损 = 底分型低点(结构失效)。 风险 1R = 进场 − 止损。
  出场 = 止损 / 跌破 EMA20(趋势破) / 持仓满 MAXHOLD 根(时间止损), 先到先算。
  逃顶信号另做前瞻验证: 触发后 FWD 根的平均涨跌(应为负才算有效)。

仅用 Python 标准库。复用同目录 signals.py / parabolic.py。
"""
import sys, os
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
import parabolic as pb
import signals as sg

MAXHOLD = 40      # [CALIB] 时间止损(交易日)
WARMUP = 90       # 起步预热
FWD = 10          # 逃顶前瞻窗口
RNG = "2y"        # 拉两年增加样本


def bucket(rs):
    if not rs:
        return ('无RS', '无RS')
    g = 'RS≥B' if rs['total'] >= 60 else 'RS<B'
    s2, s3 = rs['s2'], rs['s3']
    if s2 >= 70 and s3 >= 70: ch = '全能'
    elif s3 >= 70: ch = '领涨'
    elif s2 >= 70: ch = '防守'
    else: ch = '杂'
    return (g, ch)


def backtest_ticker(sym, spy_fd, sect_fd):
    st = pb.fetch_dated(sym, RNG)
    if not st:
        return [], []
    D, C, H, L, V = st
    n = len(C)
    e20 = sg.ema_series(C, 20)
    trades, shorts = [], []
    i = WARMUP
    while i < n - 1:
        sub = (C[:i + 1], H[:i + 1], L[:i + 1], V[:i + 1])
        sig = sg.analyze(sym, sub)
        if not sig:
            i += 1; continue
        v = sig['verdict']

        # ---- 逃顶前瞻验证 (不建仓, 只记后续涨跌) ----
        if v.startswith('📉') and i + FWD < n:
            fwd = (C[i + FWD] / C[i] - 1) * 100
            shorts.append(dict(sym=sym, fwd=fwd, pscore=sig['pscore']))

        # ---- 进场 → 模拟一笔多头交易 ----
        if v.startswith('📈') and 'stop' in sig:
            entry = C[i]; stop = sig['stop']
            if stop >= entry:
                stop = entry * 0.97
            risk = entry - stop
            kind = '双腿' if '双腿' in v else '单腿'
            rs = sg.rs_grade((D[:i + 1], C[:i + 1], H[:i + 1], L[:i + 1], V[:i + 1]), spy_fd, sect_fd)
            g, ch = bucket(rs)
            exitp, reason, jj = None, None, None
            for j in range(i + 1, n):
                if L[j] <= stop:
                    exitp, reason, jj = stop, '止损', j; break
                if C[j] < e20[j]:
                    exitp, reason, jj = C[j], '破EMA20', j; break
                if j - i >= MAXHOLD:
                    exitp, reason, jj = C[j], '时间', j; break
            if exitp is None:
                exitp, reason, jj = C[-1], '未平', n - 1
            R = (exitp - entry) / risk if risk > 0 else 0
            pct = (exitp - entry) / entry * 100          # 单笔满仓 % 收益
            trades.append(dict(sym=sym, kind=kind, R=R, pct=pct, reason=reason, bars=jj - i,
                               rs_g=g, rs_ch=ch, rs_total=(rs['total'] if rs else 0)))
            i = jj + 1                       # 不重叠, 平仓后继续
        else:
            i += 1
    return trades, shorts


def stats(trades):
    if not trades:
        return None
    R = [t['R'] for t in trades]; P = [t['pct'] for t in trades]
    B = [t['bars'] for t in trades]; n = len(R)
    wins = [r for r in R if r > 0]; losses = [r for r in R if r <= 0]
    wr = len(wins) / n
    aw = sum(wins) / len(wins) if wins else 0
    al = sum(losses) / len(losses) if losses else 0
    return dict(n=n, wr=wr, aw=aw, al=al, exp=sum(R) / n,
                avgpct=sum(P) / n, avgbars=sum(B) / n)


def line(label, s):
    if not s:
        print(f"  {label:<16} 样本不足"); return
    print(f"  {label:<16} n={s['n']:>3}  胜率{s['wr']*100:>3.0f}%  期望{s['exp']:>+5.2f}R  "
          f"平均每笔{s['avgpct']:>+5.1f}%  (赢{s['aw']:>+3.1f}R/亏{s['al']:>+3.1f}R, 持{s['avgbars']:.0f}天)")


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    syms = sys.argv[1].replace(',', ' ').split()
    sector = sys.argv[2].upper() if len(sys.argv) > 2 else None
    spy_fd = pb.fetch_dated('SPY', RNG)
    sect_fd = pb.fetch_dated(sector, RNG) if sector else None

    all_t, all_s = [], []
    for s in syms:
        t, sh = backtest_ticker(s.upper(), spy_fd, sect_fd)
        all_t += t; all_s += sh

    print(f"====== 拐点雷达 回测④ · {len(syms)}只票 · {RNG} · RS基准 {'SPY+'+sector if sector else 'SPY'} ======")
    if not all_t:
        print("无进场交易样本"); return

    print("\n--- 全部进场信号 ---")
    line('全部', stats(all_t))

    print("\n--- 按信号类型 ---")
    for k in ['双腿', '单腿']:
        line(k, stats([t for t in all_t if t['kind'] == k]))

    print("\n--- 按 RS 过滤 (验证 RS 加不加分) ---")
    for g in ['RS≥B', 'RS<B']:
        line(g, stats([t for t in all_t if t['rs_g'] == g]))
    print("  · 组合: 双腿 + RS≥B")
    line('  双腿+RS≥B', stats([t for t in all_t if t['kind'] == '双腿' and t['rs_g'] == 'RS≥B']))

    print("\n--- 按 RS 性质 ---")
    for ch in ['全能', '领涨', '防守', '杂']:
        line(ch, stats([t for t in all_t if t['rs_ch'] == ch]))

    print("\n--- 出场原因分布 ---")
    from collections import Counter
    cnt = Counter(t['reason'] for t in all_t)
    print("  " + "  ".join(f"{k}:{v}" for k, v in cnt.most_common()))

    print(f"\n--- 逃顶信号前瞻验证 (触发后 {FWD} 日涨跌, 越负越有效) ---")
    if all_s:
        avg = sum(x['fwd'] for x in all_s) / len(all_s)
        neg = sum(1 for x in all_s if x['fwd'] < 0) / len(all_s)
        print(f"  n={len(all_s)}  平均 {FWD}日后 {avg:+.1f}%  下跌占比 {neg*100:.0f}%")
    else:
        print("  无逃顶样本(区间内无过热顶)")

    print("\n注: R=以底分型止损为1单位风险的盈亏倍数; 期望值>0 即长期正收益, 不看胜率。[CALIB]阈值待此表反调。")


if __name__ == "__main__":
    main()
