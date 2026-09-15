"""Batch vendor financial statements. Abort on partial pagination; preserve raw provenance."""
import argparse, concurrent.futures as cf, datetime as dt, json, time
from collections import defaultdict
from garp_data import ROOT,CACHE,session,save,needs_cashflow,prices

URL='https://datacenter-web.eastmoney.com/api/data/v1/get'
SOURCES={
 'gjzb':('RPT_F10_FINANCE_MAINFINADATA',{'EPSXS':'稀释每股收益','TOTALOPERATEREVE':'营业总收入','PARENTNETPROFIT':'归母净利润','ROIC':'投入资本回报率','ZCFZL':'资产负债率','NETCASH_OPERATE_PK':'经营现金流量净额'}),
 'llb':('RPT_DMSK_FN_CASHFLOW',{'NETCASH_OPERATE':'经营活动产生的现金流量净额','CONSTRUCT_LONG_ASSET':'购建固定资产、无形资产和其他长期资产所支付的现金'}),
 'fzb':('RPT_F10_FINANCE_GBALANCE',{'SHARE_CAPITAL':'实收资本(或股本)'})}

def get_page(source,period,page,refresh):
    path=CACHE/'em-pages'/source/(period+'-'+str(page)+'.json')
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding='utf-8'))
    name,mapping=SOURCES[source]
    columns=','.join(['SECURITY_CODE','REPORT_DATE','NOTICE_DATE',*mapping])
    date=period[:4]+'-'+period[4:6]+'-'+period[6:]
    for attempt in range(3):
        try:
            r=session().get(URL,params=dict(reportName=name,columns=columns,filter=f'(REPORT_DATE=\'{date}\')',pageSize=500,pageNumber=page,sortColumns='SECURITY_CODE',sortTypes='1'),timeout=30)
            r.raise_for_status();j=r.json()
            if not j.get('result'):raise ValueError(j.get('message'))
            out={'url':r.url,'retrieved_at':dt.datetime.now(dt.timezone.utc).isoformat(),'result':j['result']}
            save(path,out);time.sleep(.15);return out
        except requests.HTTPError as e:
            if e.response.status_code in (403,429,456):raise
            if attempt==2:raise
            time.sleep(1+attempt)
        except Exception:
            if attempt==2:raise
            time.sleep(1+attempt)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--refresh',action='store_true');a=ap.parse_args()
    b=json.loads((ROOT/'data/bars.json').read_text(encoding='utf-8'));end=max(v[-1][0] for v in b['bars'].values());year=int(end[:4])
    periods=[str(year-2)+'1231']+[str(y)+q for y in (year-1,year) for q in ('0331','0630','0930','1231') if str(y)+q<=end.replace('-','')]
    audit={'provider':'Eastmoney bulk statements','started_at':dt.datetime.now(dt.timezone.utc).isoformat(),'price_end':end,'listing_count':len(b['names']),'bar_count':len(b['bars']),'sources':{},'pagination':[],'candidate_codes':[]}
    for source,(name,mapping) in SOURCES.items():
        companies=defaultdict(lambda:{'data':{'report_list':{}},'source':source,'provider':'Eastmoney'})
        for p in periods:
            first=get_page(source,p,1,a.refresh);pages=[first]
            with cf.ThreadPoolExecutor(max_workers=3) as pool:
                pages+=list(pool.map(lambda n:get_page(source,p,n,a.refresh),range(2,first['result']['pages']+1)))
            count=sum(len(v['result']['data']) for v in pages)
            if count!=first['result']['count']:raise ValueError(f'Partial pagination {source}/{p}: {count}')
            unique=set()
            for packet in pages:
                for row in packet['result']['data']:
                    code=row['SECURITY_CODE'];unique.add(code)
                    if code not in b['bars']:continue
                    rec=companies[code];rec['code']=code;rec['url']=URL+'?reportName='+name+'&columns=ALL&filter=(SECURITY_CODE="'+code+'")';rec['retrieved_at']=packet['retrieved_at']
                    pub=row['NOTICE_DATE'][:10].replace('-','') if row.get('NOTICE_DATE') else ''
                    report={'publish_date':pub,'data':[{'item_title':v,'item_value':row.get(k)} for k,v in mapping.items()],'source_url':packet['url'],'retrieved_at':packet['retrieved_at']}
                    old=rec['data']['report_list'].get(p)
                    if old is None or pub>old['publish_date']:rec['data']['report_list'][p]=report
            audit['pagination'].append({'source':source,'period':p,'rows':count,'unique_codes':len(unique),'provider_count':first['result']['count'],'pages':len(pages),'complete':True,'url':first['url']})
            print(source,p,'rows',count,'companies',len(companies),flush=True)
        for c,packet in companies.items():save(CACHE/'em'/source/(c+'.json'),packet)
        audit['sources'][source]={'attempted':len(b['bars']),'resolved':len(companies),'failed':[{'code':c,'reason':'No vendor financial rows in requested periods'} for c in b['bars'] if c not in companies]}
        if source=='gjzb':audit['candidate_codes']=sorted(c for c,p in companies.items() if needs_cashflow(p,end))
        save(ROOT/'data/garp-acquisition.json',audit)
    audit['sources']['raw_prices']=prices(audit['candidate_codes'],a.refresh,4,end)
    audit['finished_at']=dt.datetime.now(dt.timezone.utc).isoformat();save(ROOT/'data/garp-acquisition.json',audit)
    print('acquisition complete',len(audit['candidate_codes']),'candidate packets',flush=True)

if __name__=='__main__':
    import requests
    main()
