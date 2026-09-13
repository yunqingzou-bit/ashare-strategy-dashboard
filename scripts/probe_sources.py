# -*- coding: utf-8 -*-
'''Probe which Chinese market-data endpoints are reachable from a GitHub-hosted runner.'''
import json, ssl, sys, urllib.request
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36'}
TARGETS = [
    ('szse(akshare\u540d\u5355)', 'https://www.szse.cn/api/report/ShowReport/data?SHOWTYPE=JSON&CATALOGID=1110&TABKEY=tab1&PAGENO=1'),
    ('sina_universe', 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=5&sort=symbol&asc=1&node=hs_a'),
    ('sina_kline', 'https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData?symbol=sz000993&scale=240&ma=no&datalen=10'),
    ('tx_kline', 'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sz000993,day,2026-08-01,2026-09-11,30,qfq'),
    ('tx_qt', 'https://qt.gtimg.cn/q=sz000993'),
    ('ths_kline', 'https://d.10jqka.com.cn/v6/line/hs_000993/01/last.js'),
    ('em_ztpool', 'https://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt&Pageindex=0&pagesize=10&sort=fbt%3Aasc&date=20260911'),
    ('em_clist', 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:6&fields=f12,f14'),
    ('em_datacenter', 'https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_DAILYBILLBOARD_DETAILSNEW&columns=ALL&pageNumber=1&pageSize=5&sortColumns=SECURITY_CODE&sortTypes=1&source=WEB&client=WEB'),
    ('em_notice', 'https://np-anotice-stock.eastmoney.com/api/security/ann?sr=-1&page_size=5&page_index=1&ann_type=A&client_source=web&f_node=0&s_node=0'),
]
ctx = ssl.create_default_context()
for name, url in TARGETS:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            body = r.read()
        print('OK   ' + name.ljust(16) + ' status=' + str(r.status) + ' bytes=' + str(len(body)) + ' head=' + repr(body[:60]))
    except Exception as e:
        print('FAIL ' + name.ljust(16) + ' ' + type(e).__name__ + ': ' + str(e)[:110])
    sys.stdout.flush()
print('done')
