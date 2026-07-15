#!/usr/bin/env python3
"""
拐点雷达 信号层③ —— 缠论顶底分型 + 结构信号 + 个股 RS (严格延迟一根确认, 无未来函数)。

把富途版的 REFX 未来函数改成"分型只在其后一根 K 收盘确认时才成立", 落实定稿三原则:
  ① 龙头用【延续信号】(抬高底+回踩重启), 不用穿越 DUAL;
  ② 所有幅度阈值 ATR 归一化;
  ③ 不看量 —— 本系统靠 RS 龙头+结构+抛物线三层, 量属冗余确认(仅在放量时作 bonus 标注)。

用法:
  python3 signals.py PANW,FTNT,CRWD [SECTOR_ETF]
    第二参数=板块 ETF(选填), 作 RS 第二基准(如 CIBR/SMH); 缺省则只对 SPY。

产出每只票: 个股 RS 等级(复用 rs-leadership-scorer 打分) + 当前信号判定。
  📈 进场(回踩重启) = 抬高底(底一个比一个高) + 回踩重启(收回 EMA5), 趋势未破且 Parabolic 不过热。
            两腿全中=双腿, 一腿=单腿。放量则加 +放量。(注: 已弃用原富途 DUAL穿越/SDUAL, 回测证明震荡里更差)
  📉 逃顶 = 顶分型/首破EMA5(扳机) + Parabolic 过热(状态) + 均线转空。
  分型严格延迟一根确认: 要知道第 t 根是分型, 必须等第 t+1 根收盘。

仅用 Python 标准库 + Yahoo chart JSON。复用同目录 parabolic.py + 兄弟 skill rs_score.py。
"""
import sys, os, datetime
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
sys.path.insert(0, os.path.join(_here, '..', '..', 'rs-leadership-scorer', 'scripts'))
import parabolic as pb          # 复用 fetch_dated / ema / atr_abs / score_core
try:
    import rs_score as rslib    # 复用 zigzag/get_pivots/atr_pct/rets/lin + 打分口径
except Exception:
    rslib = None

# ---- 阈值 (ATR 归一化, 待④回测校准) ----
PB_MIN = 1.2       # [CALIB] 有效回档最小 ATR 倍数
FRESH = 2          # [CALIB] 分型确认距今 <= 几 bar 算"新鲜"
RV2 = 1.75         # [CALIB] 放量(仅 bonus 标注): 今日量 >= 1.75×50日均量
PARA_HOT = 55      # [CALIB] Parabolic 逃顶状态门槛
PARA_VETO = 55     # [CALIB] Parabolic 追高否决门槛


def ema_series(vals, n):
    k = 2 / (n + 1); out = [vals[0]]
    for v in vals[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def merge_inclusion(H, L):
    """缠论包含处理: 相邻含包含关系的 K 线按趋势方向合并。返回 [(orig_idx, h, l)]。"""
    bars = [(0, H[0], L[0])]
    up = True
    for i in range(1, len(H)):
        _, ph, pl = bars[-1]
        h, l = H[i], L[i]
        if (h <= ph and l >= pl) or (h >= ph and l <= pl):   # 有包含 → 合并
            bars[-1] = (i, max(ph, h), max(pl, l)) if up else (i, min(ph, h), min(pl, l))
        else:
            up = h > ph                                       # 无包含 → 定方向后新增
            bars.append((i, h, l))
    return bars


def find_fractals(bars):
    """在合并序列上找分型。返回 tops/bots = [(中心orig_idx, 价, 确认orig_idx)]。
    确认 idx = 后一根合并 K 的 orig_idx (最早能确认它的那根, 天然延迟>=1)。"""
    tops, bots = [], []
    for k in range(1, len(bars) - 1):
        (_, h0, l0), (i1, h1, l1), (i2, h2, l2) = bars[k - 1], bars[k], bars[k + 1]
        if h1 > h0 and h1 > h2 and l1 > l0 and l1 > l2:
            tops.append((i1, h1, i2))
        if l1 < l0 and l1 < l2 and h1 < h0 and h1 < h2:
            bots.append((i1, l1, i2))
    return tops, bots


def rs_grade(st, spy, sect):
    """复用 rs-leadership-scorer 打分口径, 对齐日期后算个股 RS。
    st/spy/sect = (D,C,H,L,V); sect 为 None 则以 SPY 兼作板块基准。"""
    if rslib is None or st is None or spy is None:
        return None
    if sect is None:
        sect = spy

    def mp(fd):
        return {fd[0][i]: (fd[1][i], fd[2][i], fd[3][i]) for i in range(len(fd[0]))}
    sm, pm, km = mp(st), mp(spy), mp(sect)
    dates = sorted(set(sm) & set(pm) & set(km))[-42:]
    if len(dates) < 25:
        return None
    S = [sm[d][0] for d in dates]; Sh = [sm[d][1] for d in dates]; Sl = [sm[d][2] for d in dates]
    P = [pm[d][0] for d in dates]; Ph = [pm[d][1] for d in dates]; Pl = [pm[d][2] for d in dates]
    K = [km[d][0] for d in dates]
    ap = rslib.atr_pct(S, Sh, Sl); mpp = rslib.atr_pct(P, Ph, Pl)

    pv = rslib.get_pivots(S, ap)
    lows = sorted([x for x in pv if x[2] == 'L'], key=lambda x: x[1])[:3]
    highs = sorted([x for x in pv if x[2] == 'H'], key=lambda x: -x[1])[:3]
    lp = [x[1] for x in sorted(lows, key=lambda x: x[0])]
    hp = [x[1] for x in sorted(highs, key=lambda x: x[0])]
    hl_b = len(lp) >= 2 and all(lp[i] < lp[i + 1] for i in range(len(lp) - 1))
    hh_b = len(hp) >= 2 and all(hp[i] < hp[i + 1] for i in range(len(hp) - 1))

    rS = rslib.rets(S); rP = rslib.rets(P); thr = 0.5 * mpp
    dn = [i for i, r in enumerate(rP) if r < -thr]; up = [i for i, r in enumerate(rP) if r > thr]
    dcap = (sum(rS[i] for i in dn) / len(dn)) / (sum(rP[i] for i in dn) / len(dn)) if dn else float('nan')
    ucap = (sum(rS[i] for i in up) / len(up)) / (sum(rP[i] for i in up) / len(up)) if up else float('nan')
    green = sum(1 for i in dn if rS[i] >= 0) / len(dn) if dn else 0
    win = sum(1 for i in up if rS[i] > rP[i]) / len(up) if up else 0
    rs_m = [S[i] / P[i] for i in range(len(S))]; rs_k = [S[i] / K[i] for i in range(len(K))]
    rs_spy_nh = rs_m[-1] >= max(rs_m) * 0.99; rs_sect_nh = rs_k[-1] >= max(rs_k) * 0.99
    peak_ago = (len(rs_m) - 1) - max(range(len(rs_m)), key=lambda i: rs_m[i])

    s1 = 95 if (hl_b and hh_b) else (60 if (hl_b or hh_b) else 20)
    cap_s = rslib.lin(dcap, [(-0.5, 100), (0, 90), (0.5, 62), (0.8, 45), (1.0, 30), (1.5, 10), (2.5, 0)]) if dcap == dcap else 50
    grn_s = rslib.lin(green, [(0, 0), (0.3, 40), (0.5, 72), (0.7, 95), (1.0, 100)])
    s2 = 0.7 * cap_s + 0.3 * grn_s
    rs_s = 100 if (rs_spy_nh and rs_sect_nh) else (60 if (rs_spy_nh or rs_sect_nh) else 25)
    uc_s = rslib.lin(ucap, [(0, 25), (0.5, 45), (1.0, 60), (1.5, 80), (2.0, 92), (3.0, 100)]) if ucap == ucap else 50
    win_s = rslib.lin(win, [(0, 0), (0.3, 40), (0.5, 65), (0.7, 90), (1.0, 100)])
    s3 = 0.45 * rs_s + 0.30 * uc_s + 0.25 * win_s
    total = 0.25 * s1 + 0.35 * s2 + 0.40 * s3
    grade = "A" if total >= 75 else ("B" if total >= 60 else ("C" if total >= 45 else "F"))
    return dict(total=total, grade=grade, s1=s1, s2=s2, s3=s3, dcap=dcap,
                rs_spy_nh=rs_spy_nh, rs_sect_nh=rs_sect_nh, peak_ago=peak_ago)


def analyze(sym, data):
    """data = (C,H,L,V)。返回信号 dict。"""
    if not data or len(data[0]) < 65:
        return None
    C, H, L, V = data
    n = len(C)
    atr = pb.atr_abs(C, H, L)
    e5, e10, e20 = ema_series(C, 5), ema_series(C, 10), ema_series(C, 20)
    vma = sum(V[-50:]) / 50 if sum(V[-50:]) > 0 else 0
    vratio = V[-1] / vma if vma > 0 else 0

    bars = merge_inclusion(H, L)
    tops, bots = find_fractals(bars)
    para = pb.score_core(C, H, L, V)
    pscore = para['total'] if para else 0

    aligned = e5[-1] > e10[-1] > e20[-1]
    trend_ok = e10[-1] > e20[-1] and C[-1] > e20[-1]
    turn_bear = e5[-1] < e10[-1]
    reclaim5 = C[-1] > e5[-1]
    break5 = C[-1] < e5[-1] and C[-2] >= e5[-2]
    hot_vol = vratio >= RV2

    sig = {'sym': sym, 'pscore': pscore, 'atr_pct': atr / C[-1] * 100,
           'aligned': aligned, 'trend_ok': trend_ok, 'turn_bear': turn_bear,
           'verdict': '⚪ 无信号', 'note': ''}

    # ---- 📈 进场: 抬高底 + 回踩重启 (纯结构, 不看量), 趋势未破且不过热 ----
    if bots:
        i1, lo, i2 = bots[-1]
        confirm_ago = (n - 1) - i2
        hl = len(bots) >= 2 and lo > bots[-2][1]
        rhi = max(C[max(0, i1 - 10):i1 + 1] or [C[i1]])
        pb_atr = (rhi - lo) / atr if atr > 0 else 0
        if confirm_ago <= FRESH and trend_ok and pb_atr >= PB_MIN:
            legs = {'抬高底': hl, '回踩重启': reclaim5}
            got = sum(legs.values())
            veto = pscore >= PARA_VETO
            if got >= 1 and not veto:
                kind = '双腿' if got == 2 else '单腿'
                marks = ' '.join(k for k, v in legs.items() if v)
                bonus = ' +放量' if hot_vol else ''
                sig['verdict'] = f'📈 进场·{kind}'
                sig['stop'] = lo                      # 结构止损=底分型低点(回测用)
                sig['note'] = (f'底分型{confirm_ago}bar前确认 价{lo:.2f} 回档{pb_atr:.1f}ATR | {marks}{bonus}'
                               + (f' | ⚠️Parabolic{pscore:.0f}偏高' if pscore >= 40 else ''))
            elif veto and got >= 1:
                sig['verdict'] = '🚫 进场被否决(追高)'
                sig['note'] = f'结构够但 Parabolic {pscore:.0f} 过热, 别追'

    # ---- 📉 逃顶/做空: 扳机(顶分型/首破E5) + 过热状态 + 转空 ----
    trig, tnote = None, ''
    if tops:
        ti, th, tc = tops[-1]
        if (n - 1) - tc <= FRESH:
            trig = '顶分型'; tnote = f'顶分型{(n-1)-tc}bar前确认 价{th:.2f}'
    if break5:
        trig = (trig + '+首破E5') if trig else '首破E5'
        tnote = (tnote + ' | 首破EMA5') if tnote else '首破EMA5'
    if trig and pscore >= PARA_HOT and not sig['verdict'].startswith('📈'):
        strength = '强' if (pscore >= 70 and turn_bear and '顶分型' in trig) else '中'
        sig['verdict'] = f'📉 逃顶/做空·{strength}'
        sig['note'] = f'{tnote} | Parabolic {pscore:.0f}' + (' | 均线转空' if turn_bear else ' | 均线未转空(做空需谨慎)')
    return sig


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    syms = sys.argv[1].replace(',', ' ').split()
    sector = sys.argv[2].upper() if len(sys.argv) > 2 else None

    spy_fd = pb.fetch_dated('SPY')
    sect_fd = pb.fetch_dated(sector) if sector else None

    rows = []
    for s in syms:
        s = s.upper()
        st = pb.fetch_dated(s)
        if not st:
            continue
        sig = analyze(s, (st[1], st[2], st[3], st[4]))
        if not sig:
            continue
        sig['rs'] = rs_grade(st, spy_fd, sect_fd)
        rows.append(sig)
    if not rows:
        print("[ERROR] 无可用数据"); sys.exit(1)

    order = {'📈': 0, '🚫': 1, '📉': 2, '⚪': 3}
    rows.sort(key=lambda x: (order.get(x['verdict'][0], 9), -(x['rs']['total'] if x['rs'] else 0)))

    benchtxt = f"SPY + {sector}" if sector else "SPY"
    print(f"====== 拐点雷达 信号③ · RS基准 {benchtxt} · {datetime.date.today()} ======")
    for r in rows:
        rs = r['rs']
        rstag = f"RS:{rs['grade']}({rs['total']:.0f})" if rs else "RS:—"
        al = 'E5>E10>E20' if r['aligned'] else ('E10>E20' if r['trend_ok'] else '趋势破/纠缠')
        print(f"\n{r['sym']:<6} {rstag:<9} {r['verdict']}")
        print(f"   {r['note'] or '—'}")
        if rs:
            nh = ('大盘✓' if rs['rs_spy_nh'] else '大盘✗') + ('/板块✓' if rs['rs_sect_nh'] else '/板块✗')
            print(f"   RS: 结构{rs['s1']:.0f} 抗跌{rs['s2']:.0f}(下行捕获{rs['dcap']:.2f}) 领涨{rs['s3']:.0f} | RS线 {nh} 峰{rs['peak_ago']}日前")
        print(f"   均线:{al}  Parabolic:{r['pscore']:.0f}  ATR:{r['atr_pct']:.1f}%")
    print("\n(RS=复用rs-leadership-scorer 结构25/抗跌35/领涨40; 进场=抬高底+回踩重启, 不看量; 分型延迟一根确认)")


if __name__ == "__main__":
    main()
