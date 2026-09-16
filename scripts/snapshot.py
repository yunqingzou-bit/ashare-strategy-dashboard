"""Whole-market snapshot for the current session. Primary source East Money, fallback Tencent."""
import argparse, datetime as dt, json, os, time
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

def universe():
    if BARS.exists():
        try:
            return sorted(json.loads(BARS.read_text(encoding='utf-8')).get('bars') or {})
        except Exception:
            pass
    names = {}
    s = session(); s.headers['Referer'] = 'https://finance.sina.com.cn/'
    url = 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData'
    for page in range(1, 95):
        try:
            txt = s.get(url, params={'page': page, 'num': 100, 'sort': 'symbol', 'asc': 1, 'node': 'hs_a',
                                     'symbol': '', '_s_r_a': 'page'}, timeout=25).text.strip()
            if not txt.startswith('['):
                break
            rows = json.loads(txt)
        except Exception:
            break
        if not rows:
            break
        for r in rows:
            code = str(r.get('code') or '').zfill(6)
            if len(code) == 6:
                names[code] = 1
    return sorted(names)

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

def tencent(batch, workers):
    codes = universe()
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pz', type=int, default=100)
    ap.add_argument('--pause', type=float, default=0.2)
    ap.add_argument('--batch', type=int, default=50)
    ap.add_argument('--workers', type=int, default=8)
    a = ap.parse_args()
    for k in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy'):
        os.environ.pop(k, None)
    now = dt.datetime.now(dt.timezone.utc); source = None; note = None
    rows = {}; total = None; quote_time = None
    try:
        rows, total = eastmoney(a.pz, a.pause)
        if len(rows) >= 3000:
            source = 'eastmoney push2 qt/clist/get'
        else:
            note = 'eastmoney rows too few (%d)' % len(rows); rows = {}
    except Exception as e:
        note = 'eastmoney failed: ' + type(e).__name__
    if not rows:
        rows, quote_time = tencent(a.batch, a.workers)
        source = 'tencent qt.gtimg.cn'
        total = len(rows) if total is None else total
    if not rows:
        raise SystemExit('snapshot empty; keeping previous data')
    out = {'source': source, 'note': note, 'retrieved_at': now.isoformat(),
           'retrieved_at_cn': now.astimezone(CN).strftime('%Y-%m-%d %H:%M:%S'),
           'date_cn': now.astimezone(CN).strftime('%Y-%m-%d'), 'quote_time': quote_time,
           'provider_total': total, 'count': len(rows), 'rows': rows}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    print(json.dumps({'source': source, 'note': note, 'count': len(rows), 'quote_time': quote_time,
                      'at': out['retrieved_at_cn']}, ensure_ascii=False))

if __name__ == '__main__':
    main()
