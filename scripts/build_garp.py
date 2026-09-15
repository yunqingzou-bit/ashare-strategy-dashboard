"""A-share historical GARP adaptation. Never labels vendor-only results Skill-eligible."""
import calendar, collections, csv, datetime as dt, html, io, json, math, statistics
from garp_data import ROOT, CACHE, values, growth, save

HEADERS=['日期','代码','名称','形态','当日涨幅',*[f'T+{i}涨幅' for i in range(1,6)],'5日累计涨幅','五日胜率']
FIELDS=['date','code','name','shape','pct','t1','t2','t3','t4','t5','cum','win']
RUNTIME={'skill_version':'3.6.1','schema_version':3,'contract_revision':'3.5','runtime_fingerprint':'ug-v3.6.1-claude-code-direct-fmp-20260830'}
RULES=[
 ('范围','现存A股日线覆盖池。“入选”定义为该股连续符合条件期间的首个交易日，掉出后再次符合才重新入表，因此同一只股票在三个月内可能多次出现。现存名单存在幸存者偏差。'),
 ('A股本地门槛','股价≥5元；总市值36–1440亿元；20个交易日平均成交额≥720万元；至少60根历史日线。市值/成交额使用固定7.2换算尺度，5元为本地门槛，并非5美元的等值换算。'),
 ('成长初筛','最新已公告季度/年度稀释EPS同比≥15%；营收同比≥0%。报告日期严格早于筛选日。'),
 ('估值初筛','TTM市盈率≤20倍；EPS同比≥20%时放宽到30倍。采用当日不复权收盘价×最新已公布报表股本÷归母净利润TTM。'),
 ('现金流初筛','标准FCF＝经营活动现金净额−购建长期资产现金支出；TTM＝上年全年＋本年累计−上年同期；FCF收益率≥3%。未扣SBC。'),
 ('质量初筛','最近已公布年度的供应商ROIC≥8%；最新资产负债率≤60%。资产负债率不是净债务/EBITDA，未据此宣称通过原Skill杠杆门。'),
 ('历史时点','使用供应商公告日期，并从公告后交易日启用；最新修订版财报、报表间股本变化、历史ST/退市名单仍可能引入偏差，不是严格点时数据库回测。'),
 ('更新时点','每个交易日北京时间14:20运行，用全市场实时快照生成当日盘中数据，供尾盘买入参考。当日行标记为盘中快照，未收盘，次日不会改写已发布的入选记录。'),
 ('盘中快照口径','当日价格与成交数据来自实时快照源，与历史序列源不同；实测两源在历史收盘上完全一致，当日价格存在约1%的中位差异。T+1以快照价为基准，T+2至T+5为收盘对收盘，五日累计仍等于逐日复合。'),
 ('记录不可改写','已发布的入选记录按日期与代码冻结：后续运行只更新其T+1至T+5结果，不改变入选名单、入场价与当日涨幅，因此历史胜率可复核。'),
 ('未完成的原Skill验证','缺少历史一致预期、独立2–3年预测、SBC调整、摊薄股本CAGR、净债务/EBITDA及逐家公司一手核验。所有适配候选均为review_required；严格版已核验入选数为0，不等于市场没有合格股票。'),
 ('形态标签','按入选日量价结构标注：放量突破（收盘创20日新高且量能≥前20日均量1.5倍）、趋势多头（5>10>20>60日均线且价在均线上）、重回20日线（收盘上穿20日均线）、均线上方、整理/回撤。仅描述结构，用于解释选股背景。'),
 ('涨幅口径','T+n为筛选日后第n个市场交易日相对前收盘的前复权涨幅；5日累计＝T+5收盘/筛选日收盘−1；停牌缺值不顺延，未完成或缺值不参与五日统计。'),
 ('胜率口径','五日胜率＝五个交易日中涨幅>0的天数/5，平盘不计上涨。它不是未来上涨概率。汇总另列5日累计为正的样本比例。'),
 ('交易限制','收盘到收盘只是观察收益，未包含次日进场价、佣金、印花税、滑点、涨停不可买及A股T+1约束。原Skill是中长期策略，5天只作跟踪。')]

def load(path): return json.loads(path.read_text(encoding='utf-8'))
def cached(code,source):
    p=(CACHE/source if source=='prices' else CACHE/'em'/source)/(code+'.json')
    return load(p) if p.exists() else {}
def reports(packet): return packet.get('data',{}).get('report_list',{})
def published(report,date):
    pub=str(report.get('publish_date','')).replace('-','')[:8]
    return len(pub)==8 and pub.isdigit() and '19900101'<=pub<date.replace('-','')
def period_values(packet,period,date):
    r=reports(packet).get(period,{})
    return values(r) if published(r,date) else None
def ttm(packet,period,key,date):
    current=period_values(packet,period,date)
    if current is None or key not in current:return None
    if period.endswith('1231'):return current[key]
    year=str(int(period[:4])-1)
    fy=period_values(packet,year+'1231',date);prior=period_values(packet,year+period[4:],date)
    if fy is None or prior is None or key not in fy or key not in prior:return None
    return fy[key]+current[key]-prior[key]
def finite(x):return isinstance(x,(int,float)) and math.isfinite(x)
def fmt(x):return '待满/缺值' if x is None else f'{x:+.2f}%'
def cell(r,k):
    if k in FIELDS[:4]:return r[k]
    if r[k] is None:return '待满/缺值'
    return f'{r[k]:.0f}%' if k=='win' else fmt(r[k])

def financials(gj,cf,bs,date):
    periods=[p for p,r in reports(gj).items() if published(r,date)]
    if not periods:return None
    p=max(periods);v=period_values(gj,p,date);previous=period_values(gj,str(int(p[:4])-1)+p[4:],date)
    if not previous:return None
    eps=growth(v.get('稀释每股收益'),previous.get('稀释每股收益'))
    revenue=growth(v.get('营业总收入'),previous.get('营业总收入'))
    if eps is None or revenue is None or eps<15 or revenue<0:return None
    annuals=[q for q,r in reports(gj).items() if q.endswith('1231') and published(r,date)]
    if not annuals:return None
    annual=max(annuals);roic=period_values(gj,annual,date).get('投入资本回报率')
    debt=v.get('资产负债率');b=period_values(bs,p,date)
    if not b or roic is None or debt is None or roic<8 or debt>60:return None
    shares=b.get('实收资本(或股本)')
    profit=ttm(gj,p,'归母净利润',date)
    ocf=ttm(cf,p,'经营活动产生的现金流量净额',date)
    capex=ttm(cf,p,'购建固定资产、无形资产和其他长期资产所支付的现金',date)
    if any(x is None for x in (shares,profit,ocf,capex)) or min(shares,profit)<=0 or capex<0:return None
    fcf=ocf-capex
    if fcf<=0:return None
    return dict(period=p,published=reports(gj)[p]['publish_date'],annual=annual,eps_yoy=eps,revenue_yoy=revenue,roic=roic,debt_ratio=debt,shares=shares,profit_ttm=profit,ocf_ttm=ocf,capex_ttm=capex,fcf_ttm=fcf)

def shape(bars,i):
    cl=[r[2] for r in bars[i-59:i+1]];price=cl[-1]
    ma=lambda n:statistics.mean(cl[-n:])
    prev_vol=statistics.mean(r[5] for r in bars[i-20:i])
    if price>max(r[3] for r in bars[i-20:i]) and prev_vol>0 and bars[i][5]/prev_vol>=1.5:return '放量突破'
    if price>ma(5)>ma(10)>ma(20)>ma(60):return '趋势多头'
    if price>ma(20) and bars[i-1][2]<=statistics.mean(r[2] for r in bars[i-20:i]):return '重回20日线'
    return '均线上方' if price>ma(20) else '整理/回撤'

def returns(bars,index,cal,date,entry=None):
    lookup={r[0]:i for i,r in enumerate(bars)};k=cal.index(date);out=[];future=[]
    base0=entry if entry else bars[index][2]
    for n in range(1,6):
        d=cal[k+n] if k+n<len(cal) else None;future.append(d)
        pos=lookup.get(d)
        if pos is None or pos<1 or bars[pos-1][2]<=0:out.append(None)
        else:out.append((bars[pos][2]/(base0 if n==1 else bars[pos-1][2])-1)*100)
    complete=all(finite(v) for v in out)
    cum=(bars[lookup[future[4]]][2]/base0-1)*100 if complete and base0>0 else None
    return out,cum,sum(v>0 for v in out)*20 if complete else None,future

def run():
    b=load(ROOT/'data/bars.json');audit=load(ROOT/'data/garp-acquisition.json')
    prices_audit=audit.get('sources',{}).get('raw_prices',{})
    if not audit.get('finished_at') or prices_audit.get('resolved',0)<0.9*max(1,prices_audit.get('attempted',1)):
        raise SystemExit('Acquisition incomplete; keeping the previously published page.')
    prov=b.get('provisional') or {}
    prev_payload={}
    prev_path=ROOT/'docs/garp.json'
    if prev_path.exists():
        try:prev_payload=load(prev_path)
        except Exception:prev_payload={}
    previous={(r.get('date'),r.get('code')):r for r in (prev_payload.get('rows') or []) if r.get('date') and r.get('code')}
    cal=sorted({r[0] for rows in b['bars'].values() for r in rows})
    end=dt.date.fromisoformat(cal[-1]);month=end.month-3;year=end.year
    if month<1:month+=12;year-=1
    start=dt.date(year,month,min(end.day,calendar.monthrange(year,month)[1]))+dt.timedelta(days=1)
    window=[d for d in cal if start.isoformat()<=d<=end.isoformat()]
    scan_start=cal[max(0,cal.index(window[0])-5)] if window else None
    rows=[];coverage=collections.Counter();source_ledger={};financial_records={}
    for code in audit['candidate_codes']:
        if code not in b['bars']:
            coverage['missing_bars']+=1;continue
        name=b['names'].get(code,code)
        if 'ST' in name.upper() or '退' in name:
            coverage['current_st_excluded']+=1;continue
        gj,cf,bs=[cached(code,s) for s in ('gjzb','llb','fzb')];raw=cached(code,'prices')
        if not all([gj,cf,bs,raw]):coverage['missing_packet']+=1;continue
        coverage['packets_available']+=1;v=b['bars'][code];memo={};hits=[]
        for i,r in enumerate(v):
            date=r[0]
            if not (scan_start<=date<=window[-1]) or i<59 or r[5]<=0:continue
            coverage['stock_days_considered']+=1
            key=tuple(max((p for p,z in reports(packet).items() if published(z,date)),default='') for packet in (gj,cf,bs))
            if key not in memo:memo[key]=financials(gj,cf,bs,date)
            f=memo[key]
            if not f:continue
            price=raw.get('prices',{}).get(date)
            if price is None:coverage['missing_raw_price']+=1;continue
            amount=statistics.mean(t[6] for t in v[i-19:i+1]);cap=price*f['shares'];pe=cap/f['profit_ttm'];fy=f['fcf_ttm']/cap*100
            if price<5 or not 36e8<=cap<=1440e8 or amount<720e4:continue
            if pe>(30 if f['eps_yoy']>=20 else 20) or fy<3:continue
            coverage['criteria_pass_days']+=1
            hits.append((i,date,f,price,cap,amount,pe,fy))
        signals=[]
        for idx,hit in enumerate(hits):
            if idx==0 or hit[0]!=hits[idx-1][0]+1:signals.append([hit])
            else:signals[-1].append(hit)
        for streak in signals:
            i,date,f,price,cap,amount,pe,fy=streak[0]
            if date<window[0]:continue
            prior=previous.get((date,code)) or {}
            entry=prior.get('entry_price') or prior.get('raw_close') or price
            entry_source=prior.get('entry_source') or ('intraday_snapshot' if (prov.get('applied') and prov.get('date')==date) else 'close')
            rr,cum,win,future=returns(v,i,cal,date,entry)
            ref=code+'-'+f['period']
            row=dict(date=date,code=code,name=prior.get('name') or name,shape=prior.get('shape') or shape(v,i),pct=prior.get('pct',(v[i][2]/v[i-1][2]-1)*100),cum=cum,win=win,status='review_required',future_dates=future,streak_days=prior.get('streak_days') or len(streak),financial_ref=prior.get('financial_ref') or ref,pe_ttm=prior.get('pe_ttm',pe),fcf_yield=prior.get('fcf_yield',fy),cap_yi=prior.get('cap_yi',cap/1e8),amount_wan=prior.get('amount_wan',amount/1e4),raw_close=price,entry_price=entry,entry_source=entry_source,eps_yoy=f['eps_yoy'],revenue_yoy=f['revenue_yoy'],roic=f['roic'],debt_ratio=f['debt_ratio'])
            row.update({f't{n+1}':rr[n] for n in range(5)})
            rows.append(row);financial_records[ref]=f;coverage['entry_signals']+=1
            source_ledger[code]={s:{k:packet[k] for k in ('url','retrieved_at')} for s,packet in zip(('indicators','cashflow','balance','raw_price'),(gj,cf,bs,raw))}
    completed=[r for r in rows if r['cum'] is not None]
    seen={(r['date'],r['code']) for r in rows}
    carried=0
    for (date,code),prior in sorted(previous.items()):
        if (date,code) in seen:continue
        v=b['bars'].get(code)
        if not v or date not in cal or not (window[0]<=date<=window[-1]):continue
        idx={r[0]:j for j,r in enumerate(v)}.get(date)
        if not idx:continue
        rr,cum,win,future=returns(v,idx,cal,date,prior.get('entry_price') or prior.get('raw_close'))
        row=dict(prior);row.update({f't{n+1}':rr[n] for n in range(5)})
        row['cum']=cum;row['win']=win;row['future_dates']=future;row['carried_forward']=True
        rows.append(row);carried+=1
    for r in rows:
        ref=r.get('financial_ref')
        if ref and ref not in financial_records and ref in (prev_payload.get('financial_records') or {}):
            financial_records[ref]=prev_payload['financial_records'][ref]
        if r['code'] not in source_ledger and r['code'] in (prev_payload.get('sources') or {}):
            source_ledger[r['code']]=prev_payload['sources'][r['code']]
    coverage['carried_forward']=carried
    nonoverlap=[];last={};ci={d:i for i,d in enumerate(cal)}
    for r in sorted(rows,key=lambda r:(r['date'],r['code'])):
        if r['code'] in last and ci[r['date']]<=last[r['code']]+5:continue
        last[r['code']]=ci[r['date']]
        if r['cum'] is not None:nonoverlap.append(r)
    stat=lambda rs:{'n':len(rs),'positive_pct':(sum(r['cum']>0 for r in rs)/len(rs)*100) if rs else None,'mean_cum':statistics.mean(r['cum'] for r in rs) if rs else None}
    per_stock={}
    for code in sorted({r['code'] for r in rows}):
        rs=[r for r in rows if r['code']==code];done=[r for r in rs if r['cum'] is not None]
        per_stock[code]={'code':code,'name':rs[0]['name'],'first_date':min(r['date'] for r in rs),'last_date':max(r['date'] for r in rs),'signals':len(rs),'positive_pct':(sum(r['cum']>0 for r in done)/len(done)*100) if done else None,'mean_cum':statistics.mean(r['cum'] for r in done) if done else None,'mean_win':statistics.mean(r['win'] for r in done) if done else None}
    checks=[]
    bad_cum=bad_win=0
    for r in completed:
        product=1.0
        for n in range(1,6):product*=(1+r[f't{n}']/100)
        if abs(product*100-100-r['cum'])>1e-6:bad_cum+=1
        if r['win']!=20*sum(r[f't{n}']>0 for n in range(1,6)):bad_win+=1
    checks.append({'check':'5日累计等于逐日复合','rows':len(completed),'mismatch':bad_cum})
    checks.append({'check':'胜率等于五个交易日中上涨天数占比','rows':len(completed),'mismatch':bad_win})
    window_rows=[r for r in rows if window[0]<=r['date']<=window[-1]]
    checks.append({'check':'全部入选日落在统计区间内','rows':len(rows),'mismatch':len(rows)-len(window_rows)})
    validation={'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'kind':'internal_consistency_only','note':'仅验证本页计算口径自洽，不是与独立行情源的交叉比对；行情与财报均来自同一供应商链路。','checks':checks}
    save(ROOT/'docs/garp-validation.json',validation)
    payload={'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'runtime':RUNTIME,'status':'adapted_research_only','strict_verified_eligible':0,'start':window[0],'end':window[-1],'trading_days':len(window),'provisional':prov,'frozen_rows':len(previous),'carried_forward':carried,'headers':HEADERS,'fields':FIELDS,'rules':RULES,'acquisition':audit,'coverage':dict(coverage),'stats':{'records':len(rows),'stocks':len({r['code'] for r in rows}),'completed':stat(completed),'nonoverlap':stat(nonoverlap)},'per_stock':per_stock,'financial_records':financial_records,'sources':source_ledger,'rows':sorted(rows,key=lambda r:(r['date'],r['code']),reverse=True)}
    save(ROOT/'docs/garp.json',payload)
    text=io.StringIO(newline='');writer=csv.writer(text);writer.writerow(HEADERS)
    for r in payload['rows']:writer.writerow([cell(r,k) for k in FIELDS])
    (ROOT/'docs/garp.csv').write_text('\ufeff'+text.getvalue(),encoding='utf-8')
    md=['# A股GARP适配初筛与五日跟踪',f"{window[0]} 至 {window[-1]}。原Skill严格版已核验入选：0；下表仅为适配候选，全部待核验。",'']+[f'- {a}：{z}' for a,z in RULES]
    md+=['','|'+'|'.join(HEADERS)+'|','|'+'|'.join(['---']*len(HEADERS))+'|']
    for r in payload['rows']:md.append('|'+'|'.join(str(cell(r,k)) for k in FIELDS)+'|')
    (ROOT/'docs/garp.md').write_text('\n'.join(md),encoding='utf-8')
    template=(ROOT/'scripts/garp_template.html').read_text(encoding='utf-8')
    fallback=''.join('<tr>'+''.join('<td>'+html.escape(str(cell(r,k)))+'</td>' for k in FIELDS)+'</tr>' for r in payload['rows'])
    page=template.replace('__PAYLOAD__',json.dumps(payload,ensure_ascii=False,allow_nan=False).replace('</','<\\/')).replace('__FALLBACK__',fallback).replace('__HEADERS__',''.join('<th>'+s+'</th>' for s in HEADERS))
    (ROOT/'docs/garp.html').write_text(page,encoding='utf-8')
    print(json.dumps({'range':[window[0],window[-1]],'stats':payload['stats'],'coverage':dict(coverage),'validation':checks},ensure_ascii=False),flush=True)
    return payload

if __name__=='__main__':run()
