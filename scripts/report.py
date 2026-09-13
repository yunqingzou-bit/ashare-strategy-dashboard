# -*- coding: utf-8 -*-
import json, os, sys, statistics as st
sys.stdout.reconfigure(encoding='utf-8')
def load(p): return json.load(open(p, encoding='utf-8'))
def fmt(x, n=2, na='-'):
    try:
        return format(float(x), '.' + str(n) + 'f')
    except Exception:
        return na
B = load('data/bars.json')
bars, names = B['bars'], B['names']
R = load('data/result.json')
picks = R['picks']
EV = load('data/events.json')
lhb, notices = EV.get('lhb', {}), EV.get('notices', {})
print('picks', len(picks), 'lhb days', len(lhb), 'notice days', len(notices), flush=True)
POS = {c: {r[0]: i for i, r in enumerate(v)} for c, v in bars.items()}
def col(rows, keys):
    for k in keys:
        if rows and k in rows[0]: return k
    return None
LH = {}
for d, rows in lhb.items():
    if not rows: continue
    kc = col(rows, ['代码', '股票代码'])
    kn = col(rows, ['龙虎榜净买额', '净买额'])
    ki = col(rows, ['解读', '上榜原因'])
    for r in rows:
        c = str(r.get(kc) or '').zfill(6)
        try: net = float(r.get(kn) or 0)
        except Exception: net = 0.0
        LH.setdefault(c, {})[d.replace('-', '')] = (net, str(r.get(ki) or '')[:20])
NOT = {}
KW = ['业绩预告','业绩快报','中标','合同','收购','重组','增持','减持','回购','问询','立案',
      '停牌','风险提示','异动','分红','解禁','定增','激励','对外投资','重大','终止','诉讼']
for d, rows in notices.items():
    if not rows: continue
    kc = col(rows, ['代码', '股票代码'])
    kt = col(rows, ['公告标题', '标题'])
    kty = col(rows, ['公告类型', '类型'])
    kd = col(rows, ['公告日期', '日期'])
    for r in rows:
        c = str(r.get(kc) or '').zfill(6)
        t = str(r.get(kt) or '')
        ty = str(r.get(kty) or '')
        dd = ''.join(_c2 for _c2 in str(r.get(kd) or d) if _c2.isdigit())[:8]
        if not any(k in t or k in ty for k in KW): continue
        NOT.setdefault(c, {}).setdefault(dd, []).append((ty, t[:44]))
def evts(row):
    c = row['code']; v = bars[c]; p = POS[c][row['date']]
    out = []
    for k in range(1, 6):
        if p+k >= len(v): break
        dd = v[p+k][0].replace('-', '')
        pc = (v[p+k][2]/v[p+k-1][2]-1)*100
        if dd in LH.get(c, {}):
            out.append('D+' + str(k) + ' 龙虎榜净买' + fmt(LH[c][dd][0]/1e8) + '亿 ' + LH[c][dd][1])
        for ty, t in (NOT.get(c, {}).get(dd) or [])[:1]:
            out.append('D+' + str(k) + ' ' + (ty or '公告') + ':' + t)
        if pc >= 9.7: out.append('D+' + str(k) + ' 涨停')
        elif pc <= -9.7: out.append('D+' + str(k) + ' 跌停')
        elif abs(pc) >= 7 and not any(x.startswith('D+' + str(k)) for x in out):
            out.append('D+' + str(k) + ' 异动' + fmt(pc) + '%')
    return out
for r in picks: r['events'] = evts(r)
W = R['window']
alld = sorted({x[0] for vv in bars.values() for x in vv})
WD = [d for d in alld if W[0] <= d <= W[1]]
b5 = []; b1 = []
for c, v in bars.items():
    for i, x in enumerate(v):
        if x[0] not in WD or i < 60: continue
        if i+1 < len(v): b1.append((v[i+1][2]/v[i][2]-1)*100)
        if i+5 < len(v): b5.append((v[i+5][2]/v[i][2]-1)*100)
base = {'n1': len(b1), 'p1_up': sum(1 for x in b1 if x > 0)/len(b1), 'm1': sum(b1)/len(b1),
        'n5': len(b5), 'p5_up': sum(1 for x in b5 if x > 0)/len(b5), 'm5': sum(b5)/len(b5),
        'med5': st.median(b5)}
json.dump({'base': base, 'picks': picks}, open('data/final.json','w',encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('BASE', json.dumps(base, ensure_ascii=False))
L1 = ['| 序号 | 日期 | 选出的股票(代码 名称 评分 形态) | 组合D+1均值 | 组合5日均值 | 5日胜率 |',
      '|---|---|---|---|---|---|']
n = 0
for d in WD:
    rs = [r for r in picks if r['date'] == d]
    if not rs: continue
    n += 1
    nm = ' / '.join(r['code'] + ' ' + str(r['name']) + ' ' + fmt(r['score'],1) + ' ' + r['cls'] for r in rs)
    d1 = [r['paths'][0] for r in rs if r['paths']]
    m5 = [r['cum'] for r in rs if r['cum'] is not None]
    w5 = (sum(1 for x in m5 if x > 0)/len(m5)*100) if m5 else None
    L1.append('| ' + str(n) + ' | ' + d + ' | ' + nm + ' | ' + fmt(sum(d1)/len(d1) if d1 else None) + '% | '
              + fmt(sum(m5)/len(m5) if m5 else None) + '% | ' + (fmt(w5,0) + '%' if w5 is not None else '-') + ' |')
L2 = ['| 日期 | 代码 | 名称 | 评分 | 形态 | D+1 | D+2 | D+3 | D+4 | D+5 | 5日累计 | 5日内关键事件 |',
      '|---|---|---|---|---|---|---|---|---|---|---|---|']
for r in picks:
    ps = list(r['paths']) + ['-']*(5-len(r['paths']))
    ev = ' ; '.join(r['events'])[:130] if r['events'] else '-'
    L2.append('| ' + r['date'] + ' | ' + r['code'] + ' | ' + str(r['name']) + ' | ' + fmt(r['score'],1)
              + ' | ' + r['cls'] + ' | ' + ' | '.join(fmt(x) + '%' for x in ps) + ' | ' + fmt(r['cum'])
              + '% | ' + ev + ' |')
stt = R['stats']
L3 = ['| 分组 | 样本(只) | 次日上涨率 | 次日平均 | 次日再涨停率 | 5日累计上涨率 | 5日平均 | 5日中位数 | 5日最好/最差 |',
      '|---|---|---|---|---|---|---|---|---|']
for k in ('all','zt_first','zt_multi','breakout','trend','other','2026-07','2026-08','2026-09'):
    s = stt.get(k)
    if not s: continue
    L3.append('| ' + k + ' | ' + str(s['n']) + ' | ' + fmt((s['p_d1_up'] or 0)*100,1) + '% | ' + fmt(s['m_d1']) + '% | '
              + fmt((s['d1_zt_rate'] or 0)*100,1) + '% | ' + fmt((s['p5_up'] or 0)*100,1) + '% | ' + fmt(s['m5'])
              + '% | ' + fmt(s['med5']) + '% | ' + fmt(s['best5']) + '% / ' + fmt(s['worst5']) + '% |')
L3.append('| 全市场基准 | ' + str(base['n5']) + ' | ' + fmt(base['p1_up']*100,1) + '% | ' + fmt(base['m1']) + '% | - | '
          + fmt(base['p5_up']*100,1) + '% | ' + fmt(base['m5']) + '% | ' + fmt(base['med5']) + '% | - |')
buckets = [(-100,-10),(-10,-5),(-5,0),(0,5),(5,10),(10,100)]
L4 = ['| 5日累计区间 | 只数 | 占比 |', '|---|---|---|']
c5 = [r['cum'] for r in picks if r['cum'] is not None]
for lo, hi in buckets:
    k = sum(1 for x in c5 if lo <= x < hi)
    L4.append('| ' + str(lo) + '% ~ ' + str(hi) + '% | ' + str(k) + ' | ' + fmt(k/len(c5)*100,1) + '% |')
md = '\n'.join(L1) + '\n\n' + '\n'.join(L2) + '\n\n' + '\n'.join(L3) + '\n\n' + '\n'.join(L4)
open('data/tables.md','w',encoding='utf-8').write(md)
print('=== T1 ===')
print('\n'.join(L1))
print('=== T3 ===')
print('\n'.join(L3))
print('=== T4 ===')
print('\n'.join(L4))
print('=== T2 rows ' + str(len(L2)-2) + ' in data/tables.md ===')
