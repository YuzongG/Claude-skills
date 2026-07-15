#!/usr/bin/env python3
"""
拐点雷达 · 运行时公共库 (canonical)。
所有共享的常量/指标/信号生成器/回测原语都定义在这里, 被 scan.py 及各研究脚本复用。
—— scan.py 只依赖 core / parabolic / signals; 其余 *_validate/*_context 是推导用的研究脚本。
"""

# ---- 共享常量 ----
WARMUP = 90        # 回测/信号预热
MAXHOLD = 40       # 时间止损(交易日)
STOP_ATR = 2.0     # 默认 ATR 止损倍数
RNG = "2y"         # 默认拉取区间
RECENT = 2         # 扫描时"当前信号"= 最近几根内触发

# 板块 → RS 第二基准 ETF
SECT_ETF = {'半导体': 'SMH', '网络安全': 'CIBR', '软件': 'IGV', '生科': 'XBI', '金融': 'XLF',
            '医疗': 'XLV', '能源': 'XLE', '工业': 'XLI', '消费可选': 'XLY', '成长高波动': 'QQQ'}

# 自带扫描 universe (~200只/11板块)
SECTORS = {
    '半导体': ['NVDA', 'AVGO', 'AMD', 'MU', 'AMAT', 'ASML', 'TXN', 'LRCX', 'KLAC', 'ADI', 'QCOM', 'MRVL', 'CDNS', 'SNPS', 'MPWR', 'NXPI', 'TER', 'ARM', 'INTC', 'ON', 'SWKS', 'MCHP'],
    '网络安全': ['PANW', 'FTNT', 'CRWD', 'NET', 'OKTA', 'ZS', 'DDOG', 'CYBR', 'QLYS', 'TENB', 'S', 'GEN', 'FFIV', 'AKAM', 'RBRK', 'CHKP', 'FROG'],
    '软件': ['MSFT', 'PLTR', 'ORCL', 'CRM', 'APP', 'NOW', 'ADBE', 'INTU', 'EA', 'TTWO', 'ADSK', 'ROP', 'FICO', 'WDAY', 'ZM', 'NTNX', 'MSTR', 'SNOW', 'TEAM', 'MDB', 'HUBS', 'PATH'],
    '生科': ['MRNA', 'VKTX', 'KYMR', 'APGE', 'RVMD', 'BBIO', 'PCVX', 'CYTK', 'RYTM', 'INSM', 'NTRA', 'RARE', 'PTGX', 'ROIV', 'RLAY', 'COGT', 'TWST'],
    '金融': ['JPM', 'V', 'MA', 'BAC', 'GS', 'WFC', 'MS', 'C', 'AXP', 'SCHW', 'BLK', 'PGR', 'SPGI', 'CB', 'COF', 'PNC', 'USB', 'BX', 'HOOD', 'CME', 'ICE', 'AON'],
    '医疗': ['LLY', 'JNJ', 'ABBV', 'UNH', 'MRK', 'AMGN', 'TMO', 'GILD', 'ABT', 'ISRG', 'PFE', 'CVS', 'VRTX', 'DHR', 'BMY', 'SYK', 'MDT', 'ELV', 'CI', 'BSX', 'REGN', 'HCA'],
    '能源': ['XOM', 'CVX', 'COP', 'MPC', 'PSX', 'VLO', 'SLB', 'EOG', 'WMB', 'KMI', 'TRGP', 'OKE', 'BKR', 'DVN', 'OXY', 'FANG', 'EQT', 'HAL', 'APA'],
    '工业': ['CAT', 'GE', 'GEV', 'RTX', 'UNP', 'BA', 'ETN', 'UBER', 'DE', 'PH', 'VRT', 'HWM', 'TT', 'LMT', 'ADP', 'PWR', 'GD', 'CSX', 'CMI', 'JCI', 'WM', 'UPS'],
    '消费可选': ['AMZN', 'TSLA', 'HD', 'MCD', 'TJX', 'BKNG', 'SBUX', 'LOW', 'MAR', 'HLT', 'ORLY', 'RCL', 'DASH', 'ROST', 'GM', 'ABNB', 'NKE', 'AZO', 'CMG', 'CVNA', 'YUM', 'DHI'],
    '成长高波动': ['COIN', 'ROKU', 'RBLX', 'U', 'AFRM', 'SOFI', 'DKNG', 'SHOP', 'TWLO', 'SMCI', 'RKLB', 'IONQ', 'SOUN', 'CELH'],
}


# ---- 指标原语 ----
def atr_series(C, H, L, n=14):
    tr = [H[0] - L[0]] + [max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1])) for i in range(1, len(C))]
    return [sum(tr[max(0, i - n + 1):i + 1]) / (i - max(0, i - n + 1) + 1) for i in range(len(C))]


def rvol_series(V, n=3):
    """今日量 ÷ 前 n 日均量 (爆量前3天均量基准)。"""
    out = []
    for i in range(len(V)):
        w = V[max(0, i - n):i]
        m = sum(w) / len(w) if w else V[i]
        out.append(V[i] / m if m > 0 else 0)
    return out


def hh_series(H, n=252):
    return [max(H[max(0, i - n + 1):i + 1]) for i in range(len(H))]


# ---- 信号生成器 (输入均为预计算数组, 无未来函数) ----
def gen_huicai(C, H, L, e5, e10, e20, atr, bots):
    """回踩重启: 底分型确认(延迟一根) + 抬高底/回踩重启 + 趋势未破 + 回档≥1.2ATR。
    返回 [(entry_idx, 止损低点, 是否双腿)]。bots=find_fractals()[1]。"""
    out = []; prev_low = None
    for ci, lo, cf in bots:
        i = cf
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


def gen_dual_fresh(C, e5, e10, e20, rv):
    """DUAL 筑底突破: 上穿EMA20 + 量≥1.5×前3日均量 + 突破前10天≥6天在EMA20下方(新鲜从下方)。"""
    idx = []
    for i in range(WARMUP, len(C) - 1):
        if not (e5[i] > e10[i] and C[i] > e20[i] and C[i - 1] <= e20[i - 1] and rv[i] >= 1.5):
            continue
        if sum(1 for j in range(i - 10, i) if C[j] < e20[j]) >= 6:
            idx.append(i)
    return idx


def gen_sdual_ignition(C, e20, rv):
    """SDUAL 点火: 站上EMA20 + E20上行 + 近15日多数在E20上(已缓慢转强) + 今日量≥2.5×前3日均量(首日暴量)。"""
    idx = []
    for i in range(WARMUP, len(C) - 1):
        above = C[i] > e20[i]
        rising = e20[i] > e20[i - 10]
        recovering = sum(1 for j in range(i - 14, i + 1) if C[j] > e20[j]) >= 10
        if above and rising and recovering and rv[i] >= 2.5 and rv[i - 1] < 2.5:
            idx.append(i)
    return idx


def base_ready(i, C, H, L, e5, e10, e20):
    """筑底完成闸门(查突破前窗口): 均线纠缠 + 窄幅盘整 + EMA20走平。"""
    w = range(i - 20, i - 3)
    min_spread = min((max(e5[j], e10[j], e20[j]) - min(e5[j], e10[j], e20[j])) / C[j] for j in w)
    rng = (max(H[j] for j in w) - min(L[j] for j in w)) / C[i]
    return min_spread < 0.04 and rng < 0.25 and e20[i] >= e20[i - 12]


# ---- 回测原语 ----
def run(idx, C, H, L, e20, atr):
    """对进场索引列表模拟交易: 止损=-STOP_ATR·ATR; 出场=止损/破EMA20/满MAXHOLD; 不重叠。"""
    n = len(C); trades = []; last_exit = -1
    for i in idx:
        if i <= last_exit:
            continue
        entry = C[i]; a = atr[i]; stop = entry - STOP_ATR * a; risk = entry - stop
        if risk <= 0:
            continue
        ex = None
        for j in range(i + 1, n):
            if L[j] <= stop: ex = (stop, j); break
            if C[j] < e20[j]: ex = (C[j], j); break
            if j - i >= MAXHOLD: ex = (C[j], j); break
        if ex is None:
            ex = (C[-1], n - 1)
        exitp, j = ex
        trades.append(dict(R=(exitp - entry) / risk, pct=(exitp - entry) / entry * 100, bars=j - i))
        last_exit = j
    return trades


def stats(trades):
    if not trades:
        return None
    R = [t['R'] for t in trades]; P = [t['pct'] for t in trades]; B = [t['bars'] for t in trades]; n = len(R)
    wins = [r for r in R if r > 0]; losses = [r for r in R if r <= 0]
    return dict(n=n, wr=len(wins) / n,
                aw=(sum(wins) / len(wins) if wins else 0),
                al=(sum(losses) / len(losses) if losses else 0),
                exp=sum(R) / n, avgpct=sum(P) / n, avgbars=sum(B) / n)
