#!/usr/bin/env python3
"""
Sector RS Ranker — 拐点雷达 地基层①。
自上而下给一篮子板块/子行业 ETF 排相对强度(RS vs SPY)，找出
  「强势领先板块」(→钻里面的确认龙头, 生命周期③) 和
  「转强板块」(弱转强, →钻里面的新星, 生命周期①→②)。
两组都是后续下钻成分股的目标池。

用法:
  python3 sector_rs.py                 # 用内置板块/子行业 ETF 篮子
  python3 sector_rs.py XLK,SMH,IGV     # 只看指定 ETF
  python3 sector_rs.py --all           # 显示全部(默认只重点显示强势+转强)

设计要点:
  - 多周期 RS 超额(1W/1M/3M vs SPY), 近期权重更高 —— 强势看的是"持续跑赢"不是一日游。
  - RS 线"新鲜度": RS=ETF/SPY 比值序列, 峰值距今越近=领先刚确立还有劲; 峰值陈旧=可能已见顶。
  - 弱转强检测: 前半段 RS 弱 + 后半段转正 + 斜率向上 —— 抓资金刚流入、还没拥挤的子赛道。
  - ⚠️ 故意纳入子行业 ETF(网安/炼油/生科等): 弱大板块常藏强子赛道, 选股胜于选大 ETF。
  - 广度(breadth)校验留给下钻成分股那一步, 本层只做 RS。

仅用 Python 标准库 + Yahoo Finance chart JSON。无需 pandas/yfinance。
"""
import urllib.request, json, datetime, sys, ssl

# 板块/子行业 ETF 篮子 —— 11 大 SPDR + 热门子赛道(含等权版避免权重股失真)
BASKET = {
    'XLK': '科技大盘',   'XLF': '金融',      'XLE': '能源',       'XLV': '医疗',
    'XLI': '工业',       'XLY': '消费可选',  'XLP': '消费必需',   'XLU': '公用事业',
    'XLB': '材料',       'XLRE': '地产',     'XLC': '通信服务',
    'SMH': '半导体',     'IGV': '软件',      'CIBR': '网络安全',  'XBI': '生科(等权)',
    'ITA': '国防航天',   'XAR': '国防(等权)','XOP': '油气开采',   'OIH': '油服',
    'KRE': '区域银行',   'XHB': '住宅建筑',  'XRT': '零售',       'TAN': '太阳能',
    'XME': '金属矿业',   'GDX': '金矿',      'JETS': '航空',      'IYT': '运输',
    'ARKK': '创新成长',
}

_ctx = ssl.create_default_context()


def wpad(s, width):
    """按显示宽度左对齐(中文/全角算 2 格)。"""
    w = sum(2 if ord(ch) > 0x2E7F else 1 for ch in s)
    return s + ' ' * max(0, width - w)


def fetch_closes(sym, rng="6mo"):
    """返回 {date: close}。证书异常时回退到不校验。"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range={rng}&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for ctx in (_ctx, ssl._create_unverified_context()):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=30, context=ctx))
            r = d['chart']['result'][0]; ts = r['timestamp']
            q = r['indicators']['quote'][0]['close']
            out = {}
            for i, t in enumerate(ts):
                if q[i] is not None:
                    out[datetime.date.fromtimestamp(t)] = q[i]
            return out
        except Exception:
            continue
    return None


def pct(a, b):
    return (a / b - 1) * 100 if b else 0.0


def analyze(etf_px, spy_px):
    """算一只 ETF 相对 SPY 的多维 RS 指标。"""
    ds = sorted(set(etf_px) & set(spy_px))
    if len(ds) < 65:
        return None
    e = [etf_px[d] for d in ds]
    s = [spy_px[d] for d in ds]
    # 多周期超额(ETF 涨幅 - SPY 涨幅)
    def excess(n):
        return pct(e[-1], e[-1 - n]) - pct(s[-1], s[-1 - n])
    ex1w, ex1m, ex3m = excess(5), excess(21), excess(63)
    # RS 线 = ETF/SPY, 取最近 35 根看形状
    rs = [e[i] / s[i] for i in range(len(e))][-35:]
    n = len(rs)
    peak_ago = n - 1 - max(range(n), key=lambda i: rs[i])
    trough_ago = n - 1 - min(range(n), key=lambda i: rs[i])
    off_peak = pct(rs[-1], max(rs))            # 距 RS 峰值(≤0), 0=创新高
    slope5 = pct(rs[-1], rs[-6])
    fh = pct(rs[n // 2], rs[0])                # 前半段 RS
    sh = pct(rs[-1], rs[n // 2])               # 后半段 RS
    strength = 0.2 * ex1w + 0.5 * ex1m + 0.3 * ex3m
    fresh = peak_ago <= 5                       # RS 新高新鲜
    # 分类
    # 🟢强势领先: 多周期跑赢 + RS 新高新鲜(峰值≤5日, 领先刚确立还有劲)
    # 🔵转强: 短中期(1W+1M)转正、斜率向上, 但中期(3M)还没确认领先 —— 早期轮动入场。
    #        要求 ex3m>-8 挡掉"深度落后里的诈尸反弹"(接飞刀)。
    if strength > 0 and ex1m > 0 and ex3m > -1 and fresh:
        tag = '🟢强势领先'
    elif ex1w > 0 and ex1m > 0 and slope5 > 0 and -8 < ex3m < 3:
        tag = '🔵转强(弱转强)'
    elif strength < -0.5 and slope5 < 0 and peak_ago > 8:
        tag = '🔴转弱/落后'
    else:
        tag = '⚪中性'
    return dict(ex1w=ex1w, ex1m=ex1m, ex3m=ex3m, strength=strength,
                peak_ago=peak_ago, trough_ago=trough_ago, off_peak=off_peak,
                slope5=slope5, fresh=fresh, tag=tag)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    show_all = '--all' in sys.argv
    if args:
        raw = ' '.join(args).replace(',', ' ').split()
        basket = {t.upper(): BASKET.get(t.upper(), t.upper()) for t in raw}
    else:
        basket = BASKET

    spy = fetch_closes('SPY')
    if not spy:
        print("[ERROR] 拉取基准 SPY 失败"); sys.exit(1)

    rows = []
    for etf, name in basket.items():
        px = fetch_closes(etf)
        if not px:
            continue
        r = analyze(px, spy)
        if r:
            rows.append((etf, name, r))
    if not rows:
        print("[ERROR] 没有可用数据"); sys.exit(1)

    rows.sort(key=lambda x: x[2]['strength'], reverse=True)

    print(f"====== 板块 RS 排名 · 基准 SPY · {datetime.date.today()} ======")
    print("强度 = 0.2×超额1W + 0.5×超额1M + 0.3×超额3M (近期权重更高)")
    print()
    print(f"{'ETF':<6}{wpad('板块', 12)}{'强度':>4}{'超额1W':>6}{'超额1M':>6}{'超额3M':>6}{'RS峰':>6}{'距峰%':>6}  状态")
    print('-' * 66)
    for etf, name, r in rows:
        print(f"{etf:<6}{wpad(name, 12)}{r['strength']:>+6.1f}{r['ex1w']:>+6.1f}%{r['ex1m']:>+6.1f}%"
              f"{r['ex3m']:>+6.1f}%{r['peak_ago']:>6d}日{r['off_peak']:>+5.1f}%  {r['tag']}")

    strong = [(e, n, r) for e, n, r in rows if r['tag'] == '🟢强势领先']
    turning = [(e, n, r) for e, n, r in rows if r['tag'] == '🔵转强(弱转强)']

    print()
    print("── 🟢 强势领先板块 → 下钻找【确认龙头】(生命周期③, 回踩买) ──")
    if strong:
        for e, n, r in strong:
            print(f"   {e} {n}  (强度{r['strength']:+.1f}, RS峰{r['peak_ago']}日前, 超额1M{r['ex1m']:+.1f}%)")
    else:
        print("   (今日无明确强势领先板块 —— 大盘可能无主线, 谨慎)")

    print()
    print("── 🔵 转强板块 → 下钻找【新星】(生命周期①→②, 小仓试, 别用总分门槛) ──")
    if turning:
        for e, n, r in turning:
            print(f"   {e} {n}  (后半RS转正, 5日斜率{r['slope5']:+.1f}%, 谷距今{r['trough_ago']}日)")
    else:
        print("   (今日无明显弱转强板块)")

    print()
    print("下一步: 对上面两组板块, 用 WebFetch 抓成分股 → 逐只跑 rs-leadership-scorer 深挖 →")
    print("        再用拐点雷达信号层(Parabolic/分型/量价)判扳机。")
    print("⚠️ 弱大板块别整个跳过: 里面的强子赛道(网安/炼油等)可能才是真龙头所在。")


if __name__ == "__main__":
    main()
