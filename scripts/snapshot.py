"""Whole-market snapshot for the current session. East Money first, Tencent fallback.

fetch() is called by fetch.py after the bar universe is known, so the snapshot always
covers exactly the codes we screen. Coverage below MIN_COVERAGE is refused so a partial
snapshot can never be published as if it were the whole market.
"""
import argparse, datetime as dt, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'snapshot.json'
BARS = ROOT / 'data' / 'bars.json'
CN = dt.timezone(dt.timedelta(hours=8))
EM_URL = 'https://push2.eastmoney.com/api/qt/clist/get'
EM_FS = 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048'
EM_FIELDS = 'f2,f3,f5,f6,f8,f9,f10,f12,f14,f15,f16,f17,f18,f20,f21,f23'
GT_URL = 'https://qt.gtimg.cn/q='
MIN_UNIVERSE = 5000
MIN_COVERAGE = 0.6
LOCAL = {}

def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

def session():
    if 's' not in LOCAL:
        LOCAL['s'] = requests.Session(); LOCAL['s'].trust_env = False
        LOCAL['s'].headers.update({'User-Agent': 'Mozilla/5.0'})
    return LOCAL['s']

def sina_universe(retries=3, pages=95):
    names = {}
    s = session(); s.headers['Referer'] = 'https://finance.sina.com.cn/'
    url = 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData'
    for page in range(1, pages):
        rows = None
        for attempt in range(retries):
            try:
                txt = s.get(url, params={'page': page, 'num': 100, 'sort': 'symbol', 'asc': 1,
                                         'node': 'hs_a', 'symbol': '', '_s_r_a': 'page'}, timeout=25).text.strip()
                if txt.startswith('['):
                    rows = json.loads(txt)
                    break
            except Exception:
                pass
            time.sleep(0.5 * (attempt + 1))
        if rows is None:
            print('sina page %d unreadable after retries; stopping' % page, file=sys.stderr)
            break
        if not rows:
            break
        for r in rows:
            code = str(r.get('code') or '').zfill(6)
            if len(code) == 6:
                names[code] = 1
    if len(names) < MIN_UNIVERSE:
        try:
            import akshare as ak
            df = ak.stock_info_a_code_name()
            alt = {str(r['code']).zfill(6): 1 for _, r in df.iterrows()}
            if len(alt) > len(names):
                print('universe: sina %d -> akshare %d' % (len(names), len(alt)), file=sys.stderr)
                names = alt
        except Exception as e:
            print('universe: akshare fallback failed %s' % type(e).__name__, file=sys.stderr)
    return sorted(names)

def universe(codes=None):
    if codes:
        return sorted(codes)
    if BARS.exists():
        try:
            got = sorted(json.loads(BARS.read_text(encoding='utf-8')).get('bars') or {})
            if len(got) >= MIN_UNIVERSE:
                return got
        except Exception:
            pass
    return sina_universe()

def eastmoney(pz, pause):
    rows = {}; page = 1; total = None
    while True:
        params = {'po': 1, 'np': 1, 'fltt': 2, 'invt': 2, 'fid': 'f3', 'fs': EM_FS,
                  'fields': EM_FIELDS, 'pz': pz, 'pn': page}
        d = None
        for attempt in range(3):
            try:
                d = session().get(EM_URL, params=params, timeout=30,
                                  headers={'Referer': 'https://quote.eastmoney.com/'}).json().get('data')
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 + 2 * attempt)
        if not d or not d.get('diff'):
            break
        total = d['total']
        for r in d['diff']:
            code = str(r.get('f12') or ''); price = num(r.get('f2')); prev = num(r.get('f18'))
            if len(code) != 6 or not price or not prev:
                continue
            rows[code] = {'name': r.get('f14'), 'price': price, 'pct': num(r.get('f3')), 'prev_close': prev,
                          'open': num(r.get('f17')), 'high': num(r.get('f15')), 'low': num(r.get('f16')),
                          'volume_shares': (num(r.get('f5')) or 0.0) * 100.0, 'amount': num(r.get('f6')),
                          'turnover': num(r.get('f8')), 'pe': num(r.get('f9')), 'vol_ratio': num(r.get('f10')),
                          'total_mv': num(r.get('f20')), 'float_mv': num(r.get('f21')), 'pb': num(r.get('f23'))}
        if page * pz >= total:
            break
        page += 1
        if pause:
            time.sleep(pause)
    return rows, total

def tencent(codes, batch, workers):
    rows = {}; times = []

    def one(chunk):
        q = ','.join(('sh' if c[0] == '6' else 'sz' if c[0] in '03' else 'bj') + c for c in chunk)
        for attempt in range(3):
            try:
                return session().get(GT_URL + q, timeout=25, headers={'Referer': 'https://gu.qq.com/'}).content.decode('gbk', 'replace')
            except Exception:
                if attempt == 2:
                    return ''
                time.sleep(1 + attempt)

    chunks = [codes[i:i + batch] for i in range(0, len(codes), batch)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for text in pool.map(one, chunks):
            for line in text.split(';'):
                if '=' not in line:
                    continue
                f = line.split('=', 1)[1].strip().strip('"').split('~')
                if len(f) < 50 or len(f[2]) != 6:
                    continue
                price = num(f[3]); prev = num(f[4])
                if not price or not prev:
                    continue
                times.append(f[30])
                rows[f[2]] = {'name': f[1], 'price': price, 'pct': num(f[32]), 'prev_close': prev,
                              'open': num(f[5]), 'high': num(f[33]), 'low': num(f[34]),
                              'volume_shares': (num(f[6]) or 0.0) * 100.0,
                              'amount': (num(f[37]) or 0.0) * 10000.0, 'turnover': num(f[38]),
                              'pe': num(f[39]), 'vol_ratio': num(f[49]),
                              'total_mv': (num(f[45]) or 0.0) * 1e8, 'float_mv': (num(f[44]) or 0.0) * 1e8,
                              'pb': num(f[46])}
    return rows, (sorted(times)[len(times) // 2] if times else None)

def fetch(codes=None, pz=100, pause=0.2, batch=50, workers=8, log=print):
    codes = universe(codes)
    now = dt.datetime.now(dt.timezone.utc)
    rows = {}; total = None; quote_time = None; source = None; note = None
    try:
        got, total = eastmoney(pz, pause)
        if len(got) >= 3000:
            rows = got; source = 'eastmoney push2 qt/clist/get'
        else:
            note = 'eastmoney rows too few (%d)' % len(got)
    except Exception as e:
        note = 'eastmoney failed: ' + type(e).__name__
    if not rows:
        rows, quote_time = tencent(codes, batch, workers)
        source = 'tencent qt.gtimg.cn'
    cover = (len(rows) / len(codes)) if codes else 0.0
    if cover < MIN_COVERAGE:
        log(json.dumps({'source': source, 'note': note, 'count': len(rows), 'universe': len(codes),
                        'coverage': round(cover, 3), 'rejected': 'coverage_below_minimum'}, ensure_ascii=False))
        return None
    out = {'source': source, 'note': note, 'retrieved_at': now.isoformat(),
           'retrieved_at_cn': now.astimezone(CN).strftime('%Y-%m-%d %H:%M:%S'),
           'date_cn': now.astimezone(CN).strftime('%Y-%m-%d'), 'quote_time': quote_time,
           'provider_total': total, 'universe': len(codes), 'count': len(rows), 'rows': rows}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    log(json.dumps({'source': source, 'note': note, 'count': len(rows), 'universe': len(codes),
                    'quote_time': quote_time, 'at': out['retrieved_at_cn']}, ensure_ascii=False))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pz', type=int, default=100)
    ap.add_argument('--pause', type=float, default=0.2)
    ap.add_argument('--batch', type=int, default=50)
    ap.add_argument('--workers', type=int, default=8)
    a = ap.parse_args()
    for k in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy'):
        os.environ.pop(k, None)
    if fetch(pz=a.pz, pause=a.pause, batch=a.batch, workers=a.workers) is None:
        raise SystemExit('snapshot rejected: coverage too low')

if __name__ == '__main__':
    main()
