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
sina = load('data/industry.json')
s2b = {}
for bd, cs in sina.items():
    for c in cs: s2b.setdefault(c, bd)
ev = None
if os.path.exists('data/events.json'):
    ev = load('data/events.json')
print('stocks', len(bars), 'boards', len(sina), 'mapped', len(s2b), 'events', ev is not None, flush=True)
def is_st(n): return ('ST' in (n or '').upper()) or ('退' in (n or ''))
def limit_th(c):
    if c.startswith(('300','301','688','689')): return 19.5
    if c[0] in '489': return 29.0
    return 9.8
CAL = sorted({r[0] for v in bars.values() for r in v})
NDAYS = int(os.environ.get("WINDOW_DAYS", "45"))
WINDOW = CAL[-NDAYS:] if len(CAL) > NDAYS else CAL[:]
SB = {}
for c, v in bars.items(): SB[c] = {r[0]: i for i, r in enumerate(v)}
def mean(a): return sum(a)/len(a) if a else None
def rsi14(cl, i):
    if i < 15: return None
    g = l = 0.0
    for k in range(i-14, i):
        d = cl[k+1]-cl[k]
        if d > 0: g += d
        else: l -= d
    if l == 0: return 100.0
    return 100 - 100/(1 + (g/14)/(l/14))
def atr14(v, i):
    if i < 15: return None
    tr = []
    for k in range(i-14, i):
        tr.append(max(v[k][3]-v[k][4], abs(v[k][3]-v[k-1][2]), abs(v[k][4]-v[k-1][2])))
    return mean(tr)
def metrics(c, i):
    v = bars[c]
    if i < 60: return None
    cl = [v[k][2] for k in range(i-59, i+1)]
    hi = [v[k][3] for k in range(i-59, i+1)]
    vo = [v[k][5] for k in range(i-59, i+1)]
    r = v[i]; m = {}
    m['close'] = r[2]; m['pct'] = (r[2]/v[i-1][2]-1)*100
    m['ma5'] = mean(cl[-5:]); m['ma10'] = mean(cl[-10:]); m['ma20'] = mean(cl[-20:]); m['ma60'] = mean(cl)
    m['ma_bull'] = m['ma5'] > m['ma10'] > m['ma20']; m['above_ma20'] = r[2] > m['ma20']
    m['dev20'] = (r[2]/m['ma20']-1)*100; m['dev60'] = (r[2]/m['ma60']-1)*100
    for n in (5,10,20,60): m['ret'+str(n)] = (r[2]/cl[-1-n]-1)*100 if len(cl) > n else None
    m['high20'] = max(hi[-20:]); m['high60'] = max(hi)
    m['is_new20'] = r[2] >= m['high20']-1e-9; m['is_new60'] = r[2] >= m['high60']-1e-9
    m['dist_high60'] = (r[2]/m['high60']-1)*100
    m['vol5'] = mean(vo[-5:]); m['vr5'] = vo[-1]/m['vol5'] if m['vol5'] else None
    m['vr10'] = vo[-1]/mean(vo[-10:])
    m['rsi14'] = rsi14([v[k][2] for k in range(0, i+1)], i)
    a = atr14(v, i); m['atr'] = a; m['atr_pct'] = a/r[2]*100 if a else None
    m['macd_dif'] = cl[-1] - mean(cl[-26:]) if len(cl) >= 26 else None
    m['to'] = r[7]; m['amount'] = r[6]
    sc = None
    if r[7] and r[7] > 0:
        try: sc = r[2]*(r[5]/(r[7]/100.0))/1e8
        except Exception: sc = None
    m['float_cap'] = sc
    return m
def zt_count(c, i):
    th = limit_th(c); v = bars[c]; n = 0; k = i
    while k >= 1 and (v[k][2]/v[k-1][2]-1)*100 >= th - 0.35:
        n += 1; k -= 1
        if n > 12: break
    return n
LEDGER_PATH = 'docs/pick-ledger.json'
def load_ledger():
    if os.path.exists(LEDGER_PATH):
        try:
            return json.load(open(LEDGER_PATH, encoding='utf-8'))
        except Exception:
            return {}
    return {}
LEDGER = load_ledger(); ledger_missing = 0
def rebuild(c, D):
    p = SB.get(c, {}).get(D)
    if p is None or p < 60 or c not in bars:
        return None
    m = metrics(c, p)
    if not m:
        return None
    return {'code': c, 'name': names.get(c), 'score': 0.0, 'cls': 'other', 'lb': 0,
            'close': m['close'], 'pct': m['pct'], 'board': s2b.get(c), 'vr': m['vr5'], 'to': m['to'],
            'cap': m['float_cap'], 'rsi': m['rsi14'], 'ret20': m['ret20'], 'sub': [0, 0, 0, 0, 0, 0], 'p': p}
picks = []; rets = {k: [] for k in range(1,6)}; sector_cache = {}
def board_pct(D):
    if D in sector_cache: return sector_cache[D]
    bp = {}
    for bd, cs in sina.items():
        vals = []
        for c in cs:
            p = SB.get(c, {}).get(D)
            if p is None or p < 1: continue
            v = bars[c]; vals.append((v[p][2]/v[p-1][2]-1)*100)
        if len(vals) >= 3: bp[bd] = st.median(vals)
    sector_cache[D] = bp; return bp
for D in WINDOW:
    bp = board_pct(D)
    order = sorted(bp.items(), key=lambda kv: -kv[1])
    brank = {bd: (i+1, len(order)) for i, (bd, _) in enumerate(order)}
    allrow = []
    for c, v in bars.items():
        p = SB[c].get(D)
        if p is None or p < 60: continue
        nm = names.get(c, '')
        if is_st(nm): continue
        m = metrics(c, p)
        if m: allrow.append((c, p, m))
    cand = []
    for c, p, m in allrow:
        is_zt = m['pct'] >= limit_th(c) - 0.35
        if not (m['pct'] >= 4.5 or (m['amount'] or 0) >= 3e8 or ((m['to'] or 0) >= 15 and m['pct'] > 0) or is_zt): continue
        cand.append((c, p, m, is_zt))
    if len(cand) > 900: cand = sorted(cand, key=lambda x: -(x[2]['amount'] or 0))[:900]
    r20 = sorted([x[2]['ret20'] for x in cand if x[2].get('ret20') is not None])
    scored = []
    for c, p, m, is_zt in cand:
        bd = s2b.get(c)
        s_sec = 20*(1-(brank[bd][0]-1)/max(1, brank[bd][1]-1)) if bd in brank else 8
        s_t = (6 if m['ma_bull'] else 0)+(4 if m['above_ma20'] else 0)+(4 if m['is_new20'] else 0)
        s_t += (3 if m['is_new60'] else 0)+(3 if (m['dist_high60'] or -99) > -3 else 0); s_t = min(20, s_t)
        vr = m['vr5'] or 0; to = m['to'] or 0
        s_v = (8 if 1.2 <= vr <= 3.0 else (4 if (1.0 <= vr < 1.2 or 3.0 < vr <= 4.5) else 1))
        s_v += (4 if 3 <= to <= 25 else (2 if (1 <= to < 3 or 25 < to <= 40) else 0))
        s_v += (3 if vr <= 4.5 else 0); s_v = min(15, s_v)
        s_q = 0; lb = 0
        if is_zt:
            lb = zt_count(c, p)
            s_q += (6 if lb == 1 else (8 if lb == 2 else 6))
            r = bars[c][p]
            s_q += (4 if r[2] >= r[3]-1e-9 else 2)
            s_q += (2 if to <= 15 else 0)
        else:
            s_q += (6 if m['is_new20'] else 3)
        s_q = min(15, s_q)
        pr = 0.5 if not r20 else sum(1 for x in r20 if x <= (m['ret20'] or 0))/len(r20)
        s_m = 8*pr; rr = m['rsi14']
        s_m += (4 if (rr is not None and 50 <= rr <= 78) else (2 if (rr is not None and 40 <= rr < 50) else 0))
        s_m += (3 if (m['macd_dif'] or 0) > 0 else 0); s_m = min(15, s_m)
        s_r = (5 if (m['atr_pct'] or 99) <= 6 else (2 if (m['atr_pct'] or 99) <= 9 else 0))
        s_r += (5 if (m['float_cap'] or 0) >= 50 else (3 if (m['float_cap'] or 0) >= 20 else 0))
        s_r += (5 if (m['dev20'] or 99) <= 15 else (2 if (m['dev20'] or 99) <= 25 else 0))
        if is_zt and lb >= 4: s_r = max(0, s_r-3)
        tot = s_sec+s_t+s_v+s_q+s_m+s_r
        if is_zt: cls = 'zt_first' if lb == 1 else 'zt_multi'
        elif m['pct'] >= 5 and m['is_new20'] and vr >= 1.5: cls = 'breakout'
        elif m['ma_bull'] and m['above_ma20'] and 1 <= vr <= 2.5 and (m['dev20'] or 0) <= 12: cls = 'trend'
        else: cls = 'other'
        scored.append({'code': c, 'name': names.get(c), 'score': round(tot,2), 'cls': cls, 'lb': lb,
                       'close': m['close'], 'pct': m['pct'], 'p': p, 'board': bd, 'vr': vr, 'to': to,
                       'cap': m['float_cap'], 'rsi': m['rsi14'], 'ret20': m['ret20'],
                       'sub': [round(s_sec,1), round(s_t,1), round(s_v,1), round(s_q,1), round(s_m,1), round(s_r,1)]})
    scored.sort(key=lambda x: -x['score'])
    bycode = {t['code']: t for t in scored}
    frozen = LEDGER.get(D)
    if frozen:
        chosen = []
        for c in frozen:
            t = bycode.get(c)
            if t is None:
                t = rebuild(c, D); ledger_missing += 1
            if t is not None:
                chosen.append(t)
    else:
        chosen = scored[:5]
        LEDGER[D] = [t['code'] for t in chosen]
    for t in chosen:
        c = t['code']; v = bars[c]; p = t['p']
        row = dict(t); row.pop('p', None); row['date'] = D
        row['paths'] = []; row['n5'] = 0; row['cum'] = None
        for k in range(1, 6):
            if p+k < len(v):
                row['paths'].append((v[p+k][2]/v[p+k-1][2]-1)*100); row['n5'] += 1
        if p+5 < len(v): row['cum'] = (v[p+5][2]/v[p][2]-1)*100
        row['d1_zt'] = bool(p+1 < len(v) and (v[p+1][2]/v[p+1-1][2]-1)*100 >= limit_th(c)-0.35)
        picks.append(row)
    for c, p, m in allrow:
        v = bars[c]
        for k in range(1, 6):
            if p+k < len(v): rets[k].append((v[p+k][2]/v[p+k-1][2]-1)*100)
json.dump(LEDGER, open(LEDGER_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
print('ledger days', len(LEDGER), 'frozen_missing', ledger_missing)
def agg(rows):
    d1 = [r['paths'][0] for r in rows if r['paths']]
    c5 = [r['cum'] for r in rows if r['cum'] is not None]
    return {'n': len(rows), 'p_d1_up': (sum(1 for x in d1 if x > 0)/len(d1)) if d1 else None,
            'm_d1': mean(d1), 'p5_up': (sum(1 for x in c5 if x > 0)/len(c5)) if c5 else None,
            'm5': mean(c5), 'med5': st.median(c5) if c5 else None,
            'worst5': min(c5) if c5 else None, 'best5': max(c5) if c5 else None,
            'd1_zt_rate': (sum(1 for r in rows if r.get('d1_zt'))/len(rows)) if rows else None}
stats = {'all': agg(picks)}
for cl in ('zt_first','zt_multi','breakout','trend','other'):
    sub = [r for r in picks if r['cls'] == cl]
    if sub: stats[cl] = agg(sub)
for mo in ('2026-07','2026-08','2026-09'):
    sub = [r for r in picks if r['date'].startswith(mo)]
    if sub: stats[mo] = agg(sub)
bm = [x for k in (1,2,3,4,5) for x in rets[k]]
base = {'n': len(bm), 'mean_daily': mean(bm), 'p_up_daily': sum(1 for x in bm if x > 0)/len(bm)}
json.dump({'window': [WINDOW[0], WINDOW[-1]], 'n_days': len(WINDOW), 'picks': picks,
           'stats': stats, 'baseline': base, 'provisional': B.get('provisional')},
          open('data/result.json','w',encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('picks', len(picks), 'days', len(WINDOW))
print('STATS', json.dumps(stats, ensure_ascii=False, default=str))
print('BASE', json.dumps(base, ensure_ascii=False))
print('PER DAY:')
for D in WINDOW:
    rs = [r for r in picks if r['date'] == D]
    print(D, ' | '.join(r['code']+' '+str(r['name'])+' '+fmt(r['score'],1)+' '+r['cls'] for r in rs))
print('DETAIL (last 20 picks):')
for r in picks[-20:]:
    print(r['date'], r['code'], r['name'], r['cls'], fmt(r['score'],1),
          ' '.join(fmt(x) for x in r['paths']), 'cum', fmt(r['cum']))
