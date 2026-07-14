#!/usr/bin/env python3
"""
RS Leadership Scorer — 找"先抗跌、后领涨"的强势龙头股。
用法:
  python3 rs_score.py TICKER [SECTOR_ETF] [START] [END]
    TICKER      个股代码 (必填), e.g. RTX
    SECTOR_ETF  板块基准 ETF (选填, 默认 QQQ), e.g. ITA / SMH / WCLD / XLF
    START END   窗口起止 ISO 日期 (选填). 缺省 = 最近约两个月 (42 交易日)
仅用 Python 标准库 + Yahoo Finance chart JSON. 无需 pandas/yfinance.
"""
import urllib.request, json, datetime, sys

def fetch(sym, rng="1y"):
    url=f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range={rng}&interval=1d"
    req=urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    try:
        d=json.load(urllib.request.urlopen(req, timeout=30))
        r=d['chart']['result'][0]; ts=r['timestamp']; q=r['indicators']['quote'][0]
    except Exception as e:
        print(f"[ERROR] 拉取 {sym} 失败: {e}"); return None
    out={}
    for i,t in enumerate(ts):
        c=q['close'][i]; h=q['high'][i]; l=q['low'][i]
        if None in (c,h,l): continue
        out[datetime.date.fromtimestamp(t)]=(c,h,l)
    return out

def atr_pct(c,h,l,n=14):
    trs=[max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1]))/c[i] for i in range(1,len(c))]
    return sum(trs[-n:])/len(trs[-n:]) if trs else 0

def zigzag(c,pct):
    n=len(c); piv=[]
    if n<2: return piv
    trend=None; ei=0; ep=c[0]; sp=c[0]
    for i in range(1,n):
        p=c[i]
        if trend is None:
            if p>=sp*(1+pct): trend='up'; piv.append((0,c[0],'L')); ei,ep=i,p
            elif p<=sp*(1-pct): trend='down'; piv.append((0,c[0],'H')); ei,ep=i,p
            continue
        if trend=='up':
            if p>ep: ep,ei=p,i
            elif p<=ep*(1-pct): piv.append((ei,ep,'H')); trend='down'; ep,ei=p,i
        else:
            if p<ep: ep,ei=p,i
            elif p>=ep*(1+pct): piv.append((ei,ep,'L')); trend='up'; ep,ei=p,i
    piv.append((ei,ep,'H' if trend=='up' else 'L'))
    return piv

def get_pivots(c,ap):
    best=None
    for k in [1.4,1.2,1.0,0.8,0.6,0.45,0.35]:
        pct=max(0.02,k*ap); pv=zigzag(c,pct)
        nl=len([x for x in pv if x[2]=='L']); nh=len([x for x in pv if x[2]=='H'])
        best=pv
        if nl>=3 and nh>=3: return pv
    return best

def rets(c): return [c[i]/c[i-1]-1 for i in range(1,len(c))]

def lin(x,pts):
    if x<=pts[0][0]: return pts[0][1]
    if x>=pts[-1][0]: return pts[-1][1]
    for i in range(len(pts)-1):
        x0,y0=pts[i]; x1,y1=pts[i+1]
        if x0<=x<=x1: return y0+(y1-y0)*(x-x0)/(x1-x0)
    return pts[-1][1]

def main():
    if len(sys.argv)<2:
        print(__doc__); sys.exit(1)
    TICK=sys.argv[1].upper()
    SECT=(sys.argv[2].upper() if len(sys.argv)>2 else "QQQ")
    START=sys.argv[3] if len(sys.argv)>3 else None
    END=sys.argv[4] if len(sys.argv)>4 else None

    px=fetch(TICK); spy=fetch("SPY"); sect=fetch(SECT)
    if not (px and spy and sect): sys.exit(1)
    common=sorted(set(px)&set(spy)&set(sect))
    if START and END:
        sd=datetime.date.fromisoformat(START); ed=datetime.date.fromisoformat(END)
        dates=[d for d in common if sd<=d<=ed]
    else:
        if END:
            ed=datetime.date.fromisoformat(END)
            common=[d for d in common if d<=ed]
        dates=common[-42:]
    if len(dates)<25:
        print(f"[ERROR] 有效交易日仅 {len(dates)} 天，不足以分析（需≥25）。"); sys.exit(1)

    S=[px[d][0] for d in dates]; P=[spy[d][0] for d in dates]; K=[sect[d][0] for d in dates]
    Sh=[px[d][1] for d in dates]; Sl=[px[d][2] for d in dates]
    Ph=[spy[d][1] for d in dates]; Pl=[spy[d][2] for d in dates]
    ap=atr_pct(S,Sh,Sl); mp=atr_pct(P,Ph,Pl)

    print(f"====== RS 龙头评分 · {TICK}  (板块基准 {SECT}) ======")
    print(f"窗口 {dates[0]} ~ {dates[-1]}  ({len(dates)} 交易日)")
    print(f"区间涨幅 {TICK} {(S[-1]/S[0]-1)*100:+.1f}%  |  SPY {(P[-1]/P[0]-1)*100:+.1f}%  |  {SECT} {(K[-1]/K[0]-1)*100:+.1f}%")
    print(f"{TICK} ATR ~ {ap*100:.1f}%   (波动越高，下方阈值/捕获越要谨慎解读)")

    # --- pivots: 3 lowest lows + 3 highest highs ---
    pv=get_pivots(S,ap)
    lows=sorted([x for x in pv if x[2]=='L'],key=lambda x:x[1])[:3]
    highs=sorted([x for x in pv if x[2]=='H'],key=lambda x:-x[1])[:3]
    lt=sorted(lows,key=lambda x:x[0]); ht=sorted(highs,key=lambda x:x[0])
    lp=[x[1] for x in lt]; hp=[x[1] for x in ht]
    hl_b=len(lp)>=2 and all(lp[i]<lp[i+1] for i in range(len(lp)-1))
    hh_b=len(hp)>=2 and all(hp[i]<hp[i+1] for i in range(len(hp)-1))
    print("\n--- ① 结构 (低点/高点识别) ---")
    print("三个最低低点:", "  ".join(f"{dates[i]}=${p:.2f}" for i,p,_ in lt))
    print("三个最高高点:", "  ".join(f"{dates[i]}=${p:.2f}" for i,p,_ in ht))
    print(f"低点抬高? {'是 (higher lows)' if hl_b else '否/部分'}   |   高点抬高? {'是 (higher highs)' if hh_b else '否/部分'}")

    # --- capture on meaningful up/down days ---
    rS=rets(S); rP=rets(P); thr=0.5*mp
    dn=[i for i,r in enumerate(rP) if r<-thr]; up=[i for i,r in enumerate(rP) if r>thr]
    if len(dn)<3 or len(up)<3:
        print(f"\n[警告] 像样涨跌日样本不足 (跌{len(dn)}/涨{len(up)})，捕获率不稳健。")
    dcap=(sum(rS[i] for i in dn)/len(dn))/(sum(rP[i] for i in dn)/len(dn)) if dn else float('nan')
    ucap=(sum(rS[i] for i in up)/len(up))/(sum(rP[i] for i in up)/len(up)) if up else float('nan')
    green=sum(1 for i in dn if rS[i]>=0)/len(dn) if dn else 0
    win=sum(1 for i in up if rS[i]>rP[i])/len(up) if up else 0
    wi=min(range(len(rP)),key=lambda i:rP[i])
    print(f"\n--- ② 抗跌 (大盘下跌日, 门槛 ±{thr*100:.2f}%) ---")
    print(f"下行捕获率 = {dcap:.2f}  (越低越好, 负数=大盘跌它反涨)")
    print(f"红天翻绿率 = {green*100:.0f}%   |   下跌日样本 n={len(dn)}")
    print(f"最差日 {dates[wi+1]}: 大盘 {rP[wi]*100:+.1f}%  {TICK} {rS[wi]*100:+.1f}%")

    print(f"\n--- ③ 领涨 (大盘上涨日 + RS 线) ---")
    print(f"上行捕获率 = {ucap:.2f}   |   领涨率 = {win*100:.0f}%   |   上涨日样本 n={len(up)}")
    rs_m=[S[i]/P[i] for i in range(len(S))]; rs_k=[S[i]/K[i] for i in range(len(S))]
    rs_spy_nh=rs_m[-1]>=max(rs_m)*0.99; rs_sect_nh=rs_k[-1]>=max(rs_k)*0.99
    print(f"RS 线 vs 大盘(SPY):  {'创新高 ✓' if rs_spy_nh else '未创新高 ✗'}  (峰值 {dates[max(range(len(rs_m)),key=lambda i:rs_m[i])]})")
    print(f"RS 线 vs 板块({SECT}): {'创新高 ✓' if rs_sect_nh else '未创新高 ✗'}  (峰值 {dates[max(range(len(rs_k)),key=lambda i:rs_k[i])]})")

    # --- scoring ---
    s1=95 if (hl_b and hh_b) else (60 if (hl_b or hh_b) else 20)
    cap_s=lin(dcap,[(-0.5,100),(0,90),(0.5,62),(0.8,45),(1.0,30),(1.5,10),(2.5,0)]) if dcap==dcap else 50
    grn_s=lin(green,[(0,0),(0.3,40),(0.5,72),(0.7,95),(1.0,100)])
    s2=0.7*cap_s+0.3*grn_s
    rs_s=100 if (rs_spy_nh and rs_sect_nh) else (60 if (rs_spy_nh or rs_sect_nh) else 25)
    uc_s=lin(ucap,[(0,25),(0.5,45),(1.0,60),(1.5,80),(2.0,92),(3.0,100)]) if ucap==ucap else 50
    win_s=lin(win,[(0,0),(0.3,40),(0.5,65),(0.7,90),(1.0,100)])
    s3=0.45*rs_s+0.30*uc_s+0.25*win_s
    total=0.25*s1+0.35*s2+0.40*s3
    grade="A" if total>=75 else ("B" if total>=60 else ("C" if total>=45 else "F"))
    act={"A":"满仓资格 (结构/抗跌/领涨齐备)","B":"标准仓 (有小短板, 见下)","C":"试单/观望 (硬伤明显)","F":"放弃/离场 (趋势或抗跌已破)"}[grade]

    print(f"\n====== 总分 ======")
    print(f"① 结构 {s1:.0f}/100 (25%)   ② 抗跌 {s2:.0f}/100 (35%)   ③ 领涨 {s3:.0f}/100 (40%)")
    print(f"   [抗跌拆解] 下行捕获分 {cap_s:.0f} · 红天翻绿分 {grn_s:.0f}")
    print(f"   [领涨拆解] RS创新高分 {rs_s:.0f} · 上行捕获分 {uc_s:.0f} · 领涨率分 {win_s:.0f}")
    print(f"\n>>> 总分 {total:.0f}/100   等级 {grade}   →  {act}")

    # --- 掉级/离场 早警 ---
    warns=[]
    if not (rs_spy_nh or rs_sect_nh): warns.append("RS 线双双掉头 (领涨基因熄火) — 皇冠指标示警")
    if dcap==dcap and dcap>1.0: warns.append(f"下行捕获 {dcap:.2f}>1.0 (抗跌变质, 已比大盘更脆)")
    if not hl_b and not hh_b: warns.append("低点+高点均走低 (结构破位, 第四阶段)")
    print("\n--- 离场/降级早警 ---")
    print("  ⚠ "+"\n  ⚠ ".join(warns) if warns else "  暂无 (强势状态健康)")
    print("\n免责: 基于历史价量的客观规则, 仅供研究, 非投资建议. 强势有有效期, 请滚动复评.")

if __name__=="__main__":
    main()
