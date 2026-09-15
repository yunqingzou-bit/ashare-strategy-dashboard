"""Dated A-share vendor financials, cached independently of the old strategy."""
import argparse, concurrent.futures as cf, datetime as dt, json, os, threading, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data/garp-cache'
URL = 'https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022'
LOCAL = threading.local()

def session():
    if not hasattr(LOCAL, 's'):
        LOCAL.s = requests.Session(); LOCAL.s.trust_env = False
        LOCAL.s.headers['User-Agent'] = 'Mozilla/5.0'
    return LOCAL.s

def symbol(code):
    return ('sh' if code.startswith('6') else 'sz' if code[0] in '03' else 'bj') + code

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    tmp.replace(path)

def fetch(code, source, refresh=False):
    path = CACHE / source / (code+'.json')
    if path.exists() and (not refresh or time.time()-path.stat().st_mtime < 86400):
        return json.loads(path.read_text(encoding='utf-8'))
    for attempt in range(3):
        try:
            r=session().get(URL, params=dict(paperCode=symbol(code), source=source, type=0, page=1, num=16), timeout=22)
            r.raise_for_status(); data=r.json()['result']['data']
            if not data.get('report_list'): raise ValueError('empty report_list')
            out={'code':code,'source':source,'url':r.url,'retrieved_at':dt.datetime.now(dt.timezone.utc).isoformat(),'data':data}
            save(path,out); return out
        except Exception as e:
            error=type(e).__name__+': '+str(e)[:100];time.sleep(.3*(attempt+1))
    return {'code':code,'source':source,'error':error}

def values(report):
    out={}
    for row in report.get('data',[]):
        try: out[row['item_title']]=float(row['item_value'])
        except (ValueError,TypeError): pass
    return out

def growth(a,b):
    return (a/b-1)*100 if a is not None and b is not None and b>0 else None

def needs_cashflow(packet, start):
    reports=packet.get('data',{}).get('report_list',{})
    for period,report in reports.items():
        if period < str(int(start[:4])-1)+'1231': continue
        v=values(report); prev=values(reports.get(str(int(period[:4])-1)+period[4:],{}))
        eg=growth(v.get('稀释每股收益'),prev.get('稀释每股收益'))
        rg=growth(v.get('营业总收入'),prev.get('营业总收入'))
        if eg is not None and eg>=10 and rg is not None and rg>=0:
            return True
    return False

def fetch_price(code, refresh=False, want=None):
    path=CACHE/'prices'/(code+'.json')
    if path.exists():
        cached=json.loads(path.read_text(encoding='utf-8'))
        last=max(cached.get('prices') or {'':''})
        if not refresh or (want and last>=want):
            return cached
    url='https://d.10jqka.com.cn/v6/line/hs_'+code+'/00/last.js'
    for attempt in range(3):
        try:
            r=session().get(url,timeout=22,headers={'Referer':'https://stockpage.10jqka.com.cn/'});r.raise_for_status()
            body=r.text;j=json.loads(body[body.find('(')+1:body.rfind(')')]);prices={}
            for row in j['data'].split(';'):
                a=row.split(',')
                if len(a)>=7 and len(a[0])==8:
                    prices[a[0][:4]+'-'+a[0][4:6]+'-'+a[0][6:]]=float(a[4])
            if not prices: raise ValueError('empty prices')
            out={'code':code,'url':url,'retrieved_at':dt.datetime.now(dt.timezone.utc).isoformat(),'prices':prices}
            save(path,out);return out
        except Exception as e:
            error=type(e).__name__+': '+str(e)[:100];time.sleep(.3*(attempt+1))
    return {'code':code,'error':error}

def prices(codes, refresh, workers, want=None):
    failures=[]
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        for i,p in enumerate(pool.map(lambda c:fetch_price(c,refresh,want),codes)):
            if 'error' in p: failures.append(p)
            if (i+1)%250==0: print('raw prices',i+1,'/',len(codes),flush=True)
    return {'attempted':len(codes),'resolved':len(codes)-len(failures),'failed':failures}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--refresh',action='store_true');ap.add_argument('--workers',type=int,default=8);ap.add_argument('--prices-only',action='store_true')
    args=ap.parse_args()
    if args.prices_only:
        audit=json.loads((ROOT/'data/garp-acquisition.json').read_text(encoding='utf-8'))
        bars=json.loads((ROOT/'data/bars.json').read_text(encoding='utf-8'))
        want=max(v[-1][0] for v in bars['bars'].values())
        audit['sources']['raw_prices']=prices(audit['candidate_codes'],args.refresh,args.workers,want)
        save(ROOT/'data/garp-acquisition.json',audit);return
    b=json.loads((ROOT/'data/bars.json').read_text(encoding='utf-8'))
    codes=sorted(b['bars']);end=max(v[-1][0] for v in b['bars'].values());start=str(int(end[:4])-1)+end[4:]
    audit={'started_at':dt.datetime.now(dt.timezone.utc).isoformat(),'price_end':end,'listing_count':len(b['names']),'bar_count':len(codes),'sources':{},'candidate_codes':[]}
    packets={}
    for source in ('gjzb','llb','fzb'):
        targets=codes if source=='gjzb' else audit['candidate_codes']
        good=0;fail=[];t0=time.time()
        with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
            for i,p in enumerate(pool.map(lambda c:fetch(c,source,args.refresh),targets)):
                if 'error' in p: fail.append({'code':p['code'],'reason':p['error']})
                else:
                    good+=1
                    if source=='gjzb': packets[p['code']]=p
                if (i+1)%250==0: print(source,i+1,'/',len(targets),'ok',good,'seconds',round(time.time()-t0),flush=True)
        audit['sources'][source]={'attempted':len(targets),'resolved':good,'failed':fail}
        if source=='gjzb': audit['candidate_codes']=[c for c,p in packets.items() if needs_cashflow(p,start)]
        save(ROOT/'data/garp-acquisition.json',audit)
        print(source,'done',good,'failed',len(fail),'cashflow candidates',len(audit['candidate_codes']),flush=True)
    audit['sources']['raw_prices']=prices(audit['candidate_codes'],args.refresh,args.workers)
    audit['finished_at']=dt.datetime.now(dt.timezone.utc).isoformat();save(ROOT/'data/garp-acquisition.json',audit)
    if not packets: raise SystemExit('No financial data: keep prior published page')

if __name__=='__main__': main()
