# -*- coding: utf-8 -*-
'''Fetch all-market qfq bars (THS) + per-day pools/LHB/notices (Eastmoney, cached).'''
import argparse, datetime, json, os, sys, time
import requests
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
CACHE = os.path.join(DATA, 'events')
SNAPSHOT = os.path.join(DATA, 'snapshot.json')
S = requests.Session()
S.trust_env = False
S.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36',
                  'Referer': 'https://stockpage.10jqka.com.cn/'})
def log(*a): print(*a, flush=True)
def snapshot_window(stamp, date_cn=None):
    try:
        t = datetime.datetime.strptime(stamp, '%Y-%m-%d %H:%M:%S')
    except (TypeError, ValueError):
        return None
    if t.weekday() >= 5 or not date_cn:
        return None
    now_cn = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).replace(tzinfo=None)
    if t.date().isoformat() != date_cn or t.date() != now_cn.date():
        return None
    hm = t.hour * 60 + t.minute
    if hm < 570 or hm > 1439:
        return None
    return 'intraday' if hm < 900 else 'after_close'
def day_is_final(fetched_at, d):
    if not fetched_at:
        return True
    try:
        stamp = datetime.datetime.fromisoformat(fetched_at)
    except ValueError:
        return True
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=datetime.timezone.utc)
    close = datetime.datetime.strptime(d, '%Y-%m-%d').replace(hour=7, minute=10, tzinfo=datetime.timezone.utc)
    return stamp >= close
def apply_snapshot(bars, snap=None):
    if snap is None:
        if not os.path.exists(SNAPSHOT):
            return {'applied': False, 'reason': 'no_snapshot'}
        try:
            snap = json.load(open(SNAPSHOT, encoding='utf-8'))
        except Exception as e:
            return {'applied': False, 'reason': 'snapshot_unreadable ' + type(e).__name__}
    capture = snapshot_window(snap.get('retrieved_at_cn', ''), snap.get('date_cn'))
    if not capture:
        return {'applied': False, 'reason': 'outside_session', 'snapshot_at': snap.get('retrieved_at_cn'),
                'source': snap.get('source')}
    date_cn = snap.get('date_cn'); injected = 0; matched = 0; rejected = 0
    for code, s in (snap.get('rows') or {}).items():
        v = bars.get(code); price = s.get('price')
        if not v or not price:
            continue
        matched += 1
        o = s.get('open') or price; h = s.get('high') or price; l = s.get('low') or price
        if not (l <= price <= h):
            rejected += 1
            continue
        if v[-1][0] > date_cn:
            continue
        bar = [date_cn, o, price, h, l, s.get('volume_shares') or 0, s.get('amount') or 0, s.get('turnover')]
        if v[-1][0] == date_cn:
            v[-1] = bar
        else:
            v.append(bar)
        injected += 1
    return {'applied': bool(injected), 'date': date_cn if injected else None, 'injected': injected,
            'matched': matched, 'rejected': rejected, 'universe': len(bars),
            'snapshot_at': snap.get('retrieved_at_cn'), 'source': snap.get('source'),
            'quote_time': snap.get('quote_time'), 'capture': capture}
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
        rows = None
        for attempt in range(3):
            try:
                txt = S.get(url, params={"page": page, "num": 100, "sort": "symbol", "asc": 1, "node": "hs_a", "symbol": "", "_s_r_a": "page"}, headers=H, timeout=25).text.strip()
                if txt.startswith("["):
                    rows = json.loads(txt)
                    break
            except Exception:
                pass
            time.sleep(0.5 * (attempt + 1))
        if rows is None:
            log("universe page", page, "unreadable after retries; stopping")
            break
        if not rows:
            break
        for r in rows:
            c = str(r.get("code") or "").zfill(6)
            if len(c) == 6:
                names[c] = str(r.get("name") or "")
    return names
def refresh_bars():
    names = universe()
    log("universe from sina", len(names))
    if len(names) < 5000:
        try:
            import akshare as ak
            df = ak.stock_info_a_code_name()
            alt = {str(r["code"]).zfill(6): str(r["name"]) for _, r in df.iterrows()}
            if len(alt) > len(names):
                names = alt
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
    return names, bars
def fetch_day(ak, d):
    ds = d.replace('-', '')
    p = os.path.join(CACHE, ds + '.json')
    if os.path.exists(p):
        try:
            cached = json.load(open(p, encoding='utf-8'))
        except Exception:
            cached = {}
        if day_is_final(cached.get('fetched_at'), d):
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
    o['fetched_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
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
        loaded = json.load(open(os.path.join(DATA, 'bars.json'), encoding='utf-8'))
        names = loaded['names']; bars = loaded['bars']
    else:
        names, bars = refresh_bars()
    snap = None
    try:
        import snapshot as snapmod
        snap = snapmod.fetch(codes=sorted(bars), log=log)
    except Exception as e:
        log('snapshot fetch failed', type(e).__name__, str(e)[:140])
    prov = apply_snapshot(bars, snap)
    log('snapshot', json.dumps(prov, ensure_ascii=False, default=str))
    json.dump({'names': names, 'bars': bars, 'provisional': prov},
              open(os.path.join(DATA, 'bars.json'), 'w', encoding='utf-8'), ensure_ascii=False)
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
