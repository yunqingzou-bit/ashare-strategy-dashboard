# -*- coding: utf-8 -*-
'''Fetch all-market qfq bars (THS) + per-day pools/LHB/notices (Eastmoney, cached).'''
import argparse, json, os, sys, time
import requests
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
CACHE = os.path.join(DATA, 'events')
S = requests.Session()
S.trust_env = False
S.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36',
                  'Referer': 'https://stockpage.10jqka.com.cn/'})
def log(*a): print(*a, flush=True)
def ths_line(code):
    for fq in ('01', '00'):
        url = 'https://d.10jqka.com.cn/v6/line/hs_' + code + '/' + fq + '/last.js'
        for att in range(3):
            try:
                t = S.get(url, timeout=20).text.strip()
                i = t.find('('); j = t.rfind(')')
                if i < 0 or j <= i: break
                jj = json.loads(t[i+1:j])
                out = []
                for rec in (jj.get('data') or '').split(';'):
                    p = rec.split(',')
                    if len(p) < 7 or len(p[0]) != 8: continue
                    try:
                        out.append([p[0][:4] + '-' + p[0][4:6] + '-' + p[0][6:8], float(p[1]), float(p[4]),
                                    float(p[2]), float(p[3]), float(p[5]), float(p[6]),
                                    float(p[7]) if len(p) > 7 and p[7] else None])
                    except ValueError:
                        pass
                if out: return out
            except Exception:
                time.sleep(0.2 * (att + 1))
    return None
def universe():
    H = {"Referer": "https://finance.sina.com.cn/"}
    names = {}
    url = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
    for page in range(1, 90):
        try:
            txt = S.get(url, params={"page": page, "num": 100, "sort": "symbol", "asc": 1, "node": "hs_a", "symbol": "", "_s_r_a": "page"}, headers=H, timeout=25).text.strip()
            if not txt.startswith("["):
                break
            rows = json.loads(txt)
            if not rows:
                break
            for r in rows:
                c = str(r.get("code") or "").zfill(6)
                if len(c) == 6:
                    names[c] = str(r.get("name") or "")
        except Exception as e:
            log("universe page", page, "failed", type(e).__name__)
            break
        if len(names) == 0 and page >= 3:
            break
    return names
def refresh_bars():
    names = universe()
    log("universe from sina", len(names))
    if len(names) < 3000:
        try:
            import akshare as ak
            df = ak.stock_info_a_code_name()
            names = {str(r["code"]).zfill(6): str(r["name"]) for _, r in df.iterrows()}
            log("universe fallback akshare", len(names))
        except Exception as e:
            log("universe fallback failed", type(e).__name__)
    codes = sorted(names)
    log('universe', len(codes))
    t0 = time.time(); bars = {}; fail = []
    def one(c): return c, ths_line(c)
    with ThreadPoolExecutor(max_workers=12) as ex:
        for i, (c, b) in enumerate(ex.map(one, codes)):
            if b: bars[c] = b
            else: fail.append(c)
            if (i + 1) % 1000 == 0: log('  bars %d/%d ok=%d %.0fs' % (i + 1, len(codes), len(bars), time.time() - t0))
    json.dump({'names': names, 'bars': bars, 'failed': fail},
              open(os.path.join(DATA, 'bars.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    log('bars ok', len(bars), 'fail', len(fail))
    return bars
def fetch_day(ak, d):
    ds = d.replace('-', '')
    p = os.path.join(CACHE, ds + '.json')
    if os.path.exists(p):
        return False
    def rows(fn, **kw):
        try:
            df = fn(**kw); df.columns = [str(c) for c in df.columns]
            return json.loads(df.to_json(orient='records', force_ascii=False))
        except Exception:
            return []
    o = {'date': d,
         'zt': rows(ak.stock_zt_pool_em, date=ds),
         'zb': rows(ak.stock_zt_pool_zbgc_em, date=ds),
         'strong': rows(ak.stock_zt_pool_strong_em, date=ds),
         'lhb': rows(ak.stock_lhb_detail_em, start_date=ds, end_date=ds),
         'notices': rows(ak.stock_notice_report, symbol='全部', date=ds)}
    json.dump(o, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
    return True
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=int(os.environ.get('WINDOW_DAYS', '45')))
    ap.add_argument('--skip-bars', action='store_true')
    ap.add_argument('--skip-events', action='store_true')
    a = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)
    if a.skip_bars:
        bars = json.load(open(os.path.join(DATA, 'bars.json'), encoding='utf-8'))['bars']
    else:
        bars = refresh_bars()
    cal = sorted({r[0] for v in bars.values() for r in v})
    win = cal[-a.days:] if len(cal) > a.days else cal[:]
    log('window', win[0], '->', win[-1], len(win), 'days')
    if a.skip_events:
        return
    import akshare as ak
    t0 = time.time(); new = 0
    for d in win:
        if fetch_day(ak, d):
            new += 1
            log('  new day', d, '%.0fs' % (time.time() - t0))
    log('new days fetched:', new, 'cached:', len(win) - new)
    pools = {}; lhb = {}; notices = {}
    for d in win:
        ds = d.replace('-', '')
        o = json.load(open(os.path.join(CACHE, ds + '.json'), encoding='utf-8'))
        for k in ('zt', 'zb', 'strong'):
            pools[k + '_' + ds] = o.get(k) or []
        lhb[ds] = o.get('lhb') or []
        notices[ds] = o.get('notices') or []
    json.dump({'pools': pools, 'lhb': lhb, 'notices': notices},
              open(os.path.join(DATA, 'events.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    log('events.json written')
main()
