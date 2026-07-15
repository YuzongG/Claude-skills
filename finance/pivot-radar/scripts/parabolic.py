#!/usr/bin/env python3
"""
Parabolic Score — 拐点雷达 信号层②。
把"抛物线喷出/过热"从感觉量化成 0-100 分。用于逃顶/做空的【状态】判定
(真正的扳机是顶分型/首破 EMA5, 在信号层③), 以及做多时的【别追高否决】。

用法:
  python3 parabolic.py NVDA
  python3 parabolic.py PLTR,NVDA,CRWD,XOM

四个分量(纯价格, 权重):
  ① 曲率 39%  —— 对最近 15 根 ln(收盘) 做最小二乘二次拟合 y=ax²+bx+c。
                 a>0 = 上凸/加速(抛物线的数学定义); 乘拟合优度 R²(平滑地加速才算)。
                 匀速 45° 慢牛 a≈0 → 得分≈0, 正是要区分"加速"和"斜坡"。
  ② 加速度 22% —— 近5日涨幅 − 前5日涨幅, 除以 ATR% (跨股可比)。
  ③ ATR陡度 17% —— (C − C[5]) / (ATR × 5) = 每天涨几个 ATR。
  ④ 乖离 22%  —— 高出 EMA10/EMA20 多少个 ATR (皮筋张力)。
  (已去掉 climax 量: 本系统靠 RS 龙头+结构+抛物线, 量属冗余确认。)

阈值(初版, 待回测校准): ≥70 抛物线过热 · 55-70 加速中 · 35-55 偏强延伸 · <35 正常。
所有归一化常数标 [CALIB], 后续用回测引擎(信号层④)校准。

仅用 Python 标准库 + Yahoo Finance chart JSON。无需 pandas/yfinance。
"""
import urllib.request, json, datetime, sys, ssl, math, time

# ---- 归一化目标常数 (待回测校准) ----
CURV_TGT = 0.004     # [CALIB] 2a 目标(合成校准): 日对数收益线性升到 ~5-6% = 满分抛物线
ACCEL_ATR = 2.5      # [CALIB] 加速度目标 = 2.5×ATR%
SLOPE_TGT = 0.8      # [CALIB] ATR陡度目标: 每天涨 0.8 个 ATR
EXT_TGT = 5.0        # [CALIB] 乖离目标: 高出均线 5 个 ATR

# 纯价格版(已去掉 climax 量): 曲率/加速/陡度/乖离, 权重按去量后重新归一
W = dict(curv=0.39, accel=0.22, slope=0.17, ext=0.22)


def fetch_dated(sym, rng="1y"):
    """返回 (dates, C, H, L, V) 平行列表; 带日期用于跨票对齐(RS)。
    盘中运行时丢弃未收盘的最后一根 (延迟一根确认原则)。"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range={rng}&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for ctx in (ssl.create_default_context(), ssl._create_unverified_context()):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=30, context=ctx))
            r = d['chart']['result'][0]; ts = r['timestamp']; q = r['indicators']['quote'][0]
            D, C, H, L, V = [], [], [], [], []
            for i, t in enumerate(ts):
                c, h, l, v = q['close'][i], q['high'][i], q['low'][i], q['volume'][i]
                if None in (c, h, l): continue
                D.append(datetime.date.fromtimestamp(t))
                C.append(c); H.append(h); L.append(l); V.append(v or 0)
            try:
                reg = r['meta']['currentTradingPeriod']['regular']
                if reg['start'] <= time.time() <= reg['end'] and len(C) > 1:
                    D.pop(); C.pop(); H.pop(); L.pop(); V.pop()
            except Exception:
                pass
            return (D, C, H, L, V) if len(C) >= 65 else None
        except Exception:
            continue
    return None


def fetch(sym, rng="6mo"):
    """(closes, highs, lows, vols) — 薄封装 fetch_dated。"""
    fd = fetch_dated(sym, rng)
    return (fd[1], fd[2], fd[3], fd[4]) if fd else None


def ema(vals, n):
    k = 2 / (n + 1); e = vals[0]
    for v in vals[1:]:
        e = v * k + e * (1 - k)
    return e


def atr_abs(C, H, L, n=14):
    trs = [max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1])) for i in range(1, len(C))]
    return sum(trs[-n:]) / len(trs[-n:]) if trs else 0


def quad_fit(y):
    """最小二乘拟合 y=ax²+bx+c, x=0..n-1。返回 (a, b, c, R²)。"""
    n = len(y); x = list(range(n))
    Sx = sum(x); Sx2 = sum(i * i for i in x); Sx3 = sum(i ** 3 for i in x); Sx4 = sum(i ** 4 for i in x)
    Sy = sum(y); Sxy = sum(x[i] * y[i] for i in range(n)); Sx2y = sum(x[i] ** 2 * y[i] for i in range(n))
    # 正规方程矩阵 M·[a,b,c] = R
    M = [[Sx4, Sx3, Sx2], [Sx3, Sx2, Sx], [Sx2, Sx, n]]
    R = [Sx2y, Sxy, Sy]
    det = (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1])
           - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
           + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))
    if abs(det) < 1e-18:
        return 0, 0, y[-1], 0

    def solve(col):
        Mc = [row[:] for row in M]
        for r in range(3): Mc[r][col] = R[r]
        return (Mc[0][0] * (Mc[1][1] * Mc[2][2] - Mc[1][2] * Mc[2][1])
                - Mc[0][1] * (Mc[1][0] * Mc[2][2] - Mc[1][2] * Mc[2][0])
                + Mc[0][2] * (Mc[1][0] * Mc[2][1] - Mc[1][1] * Mc[2][0])) / det
    a, b, c = solve(0), solve(1), solve(2)
    ybar = Sy / n
    ss_tot = sum((yi - ybar) ** 2 for yi in y)
    ss_res = sum((y[i] - (a * i * i + b * i + c)) ** 2 for i in range(n))
    r2 = 1 - ss_res / ss_tot if ss_tot > 1e-18 else 0
    return a, b, c, r2


def clip01(x):
    return max(0.0, min(1.0, x))


def score_core(C, H, L, V):
    """对给定 OHLCV 数组(用其末端)算 Parabolic Score。可切片数组做历史回看。"""
    if len(C) < 65:
        return None
    atr = atr_abs(C, H, L)
    atr_pct = atr / C[-1] * 100 if C[-1] else 0
    e10, e20 = ema(C[-40:], 10), ema(C[-60:], 20)

    # ① 曲率 (带方向门: a>0 且价格确在上冲, 否则是"下跌筑底"的假正曲率)
    win = 15
    y = [math.log(v) for v in C[-win:]]
    a, b, c, r2 = quad_fit(y)
    curv_raw = 2 * a                       # 日对数收益的日增量
    end_slope = 2 * a * (win - 1) + b      # 窗口末端瞬时斜率
    rising = C[-1] > C[-win] and end_slope > 0
    s_curv = clip01(curv_raw / CURV_TGT) * clip01(r2) if (a > 0 and rising) else 0.0

    # ② 加速度
    g_now = (C[-1] / C[-6] - 1) * 100
    g_pre = (C[-6] / C[-11] - 1) * 100
    accel = g_now - g_pre
    s_accel = clip01(accel / (atr_pct * ACCEL_ATR)) if atr_pct > 0 else 0.0

    # ③ ATR陡度
    slope = (C[-1] - C[-6]) / (atr * 5) if atr > 0 else 0
    s_slope = clip01(slope / SLOPE_TGT)

    # ④ 乖离 (高出均线几个 ATR)
    ext = ((C[-1] - e10) / atr * 0.4 + (C[-1] - e20) / atr * 0.6) if atr > 0 else 0
    s_ext = clip01(ext / EXT_TGT)

    total = 100 * (W['curv'] * s_curv + W['accel'] * s_accel
                   + W['slope'] * s_slope + W['ext'] * s_ext)
    if total >= 70: tag = '🔥抛物线过热'
    elif total >= 55: tag = '🟠加速中'
    elif total >= 35: tag = '🟡偏强延伸'
    else: tag = '⚪正常'
    return dict(total=total, tag=tag, atr_pct=atr_pct, r2=r2, a=a,
                accel=accel, ext_atr=ext, gnow=g_now,
                s=dict(curv=s_curv, accel=s_accel, slope=s_slope, ext=s_ext))


def score_one(sym):
    data = fetch(sym)
    if not data:
        return None
    r = score_core(*data)
    if r:
        r['sym'] = sym
    return r


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    syms = ' '.join(sys.argv[1:]).replace(',', ' ').split()
    res = []
    for s in syms:
        r = score_one(s.upper())
        if r: res.append(r)
    if not res:
        print("[ERROR] 没有可用数据"); sys.exit(1)
    res.sort(key=lambda x: x['total'], reverse=True)

    print(f"====== Parabolic Score (纯价格) · {datetime.date.today()} ======")
    print(f"{'票':<6}{'总分':>5}  {'曲率':>6}{'加速':>6}{'陡度':>6}{'乖离':>6}   {'ATR%':>5}{'R²':>5}  状态")
    print('-' * 66)
    for r in res:
        s = r['s']
        print(f"{r['sym']:<6}{r['total']:>5.0f}  {s['curv']*100:>6.0f}{s['accel']*100:>6.0f}"
              f"{s['slope']*100:>6.0f}{s['ext']*100:>6.0f}   "
              f"{r['atr_pct']:>5.1f}{r['r2']:>5.2f}  {r['tag']}")
    print("(各分量列 = 该项 0-100 归一化得分; 总分 = 加权 曲率39/加速22/陡度17/乖离22)")
    print()
    print("提示: 高分=过热【状态】, 逃顶还需配顶分型/首破EMA5【扳机】(信号层③);")
    print("      做多时高分=别追高否决。乖离/陡度/加速均已按 ATR 归一化, 跨股可比。")


if __name__ == "__main__":
    main()
