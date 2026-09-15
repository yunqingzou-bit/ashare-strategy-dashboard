# -*- coding: utf-8 -*-
'''Table-only version (one row per stock) with header dropdown filters -> docs/tables.html'''
import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')
F = json.load(open('data/final.json', encoding='utf-8'))
R = json.load(open('data/result.json', encoding='utf-8'))
picks = F['picks']; base = F['base']; stats = R['stats']
CN = {'zt_first': '首板', 'zt_multi': '连板', 'trend': '趋势', 'breakout': '突破', 'other': '其他'}
NM = {'all': '全部选出', 'zt_first': '首板涨停', 'zt_multi': '连板涨停', 'breakout': '放量突破', 'trend': '趋势多头',
      'other': '其他', '2026-07': '2026年7月', '2026-08': '2026年8月', '2026-09': '2026年9月'}
def pct(x, na='未满'):
    return na if x is None else (('+' if x >= 0 else '') + format(float(x), '.2f') + '%')
def pc(x):
    return '' if x is None else ('pos' if x >= 0 else 'neg')
def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
def q(s): return str(s).replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;')
def n1(x): return format(float(x), '.1f')
def n2(x): return format(float(x), '.2f')
def flags(p):
    out = set()
    for e in p['events']:
        if '龙虎榜' in e: out.add('龙虎榜')
        elif ':' in e: out.add('公告')
        elif '涨停' in e: out.add('涨停')
        elif '跌停' in e: out.add('跌停')
        elif '异动' in e: out.add('异动')
    return ';'.join(sorted(out))
dates = sorted({p['date'] for p in picks})
rng = R['window'][0] + ' ~ ' + R['window'][1]
OPT = '<option value="">全部</option>'
def sel(k, opts):
    return '<select class="flt" data-k="' + k + '">' + OPT + ''.join('<option value="' + v + '">' + t + '</option>' for v, t in opts) + '</select>'
UP = [('up', '上涨'), ('down', '下跌'), ('zt', '涨停≥9.5%'), ('dt', '跌停≤-9.5%'), ('na', '未满')]
CU = [('up', '上涨'), ('down', '下跌'), ('gt10', '>10%'), ('lt1', '<-10%'), ('na', '未满')]
PC = [('zt', '涨停≥9.5%'), ('ge5', '≥5%'), ('b05', '0~5%'), ('down', '下跌')]
EV = [('has', '有事件'), ('none', '无事件'), ('龙虎榜', '龙虎榜'), ('公告', '公告'), ('涨停', '涨停'), ('跌停', '跌停'), ('异动', '异动')]
WR = [('c100', '100%'), ('ge80', '≥80%'), ('ge60', '≥60%'), ('le40', '≤40%'), ('c0', '0%'), ('na', '未满')]
CL = [(k, v) for k, v in CN.items()]
main_rows = []
for p in reversed(picks):
    ps = list(p['paths'])
    cells = ''
    attrs = ''
    for i in range(5):
        v = ps[i] if i < len(ps) else None
        cells += '<td class="n ' + pc(v) + '">' + (pct(v, '-') if v is not None else '-') + '</td>'
        attrs += ' data-d' + str(i + 1) + '="' + (format(float(v), '.4f') if v is not None else '') + '"'
    up = sum(1 for x in ps if x > 0)
    tot = len(ps)
    if tot:
        wrp = up / tot * 100
        wr = str(up) + '/' + str(tot) + ' (' + format(wrp, '.0f') + '%)'
        wrcls = ' pos' if wrp >= 60 else (' neg' if wrp <= 40 else '')
    else:
        wr = '-'; wrcls = ''
    evtxt = ' ; '.join(p['events'])
    ev = esc(evtxt) if evtxt else '-'
    dpct = p['pct']
    stock = '<b>' + p['code'] + '</b> ' + esc(p['name']) + ' <span class="tag">' + CN.get(p['cls'], p['cls']) + '</span>'
    main_rows.append('<tr data-date="' + p['date'][5:] + '" data-stock="' + q(p['code'] + ' ' + str(p['name'])) + '" data-cls="' + p['cls']
                     + '" data-pct="' + format(float(dpct), '.4f') + '" data-cum="' + (format(float(p['cum']), '.4f') if p['cum'] is not None else '')
                     + '" data-ev="' + q(flags(p)) + '" data-wr="' + (format(wrp, '.4f') if tot else '') + '"' + attrs + '>'
                     + '<td>' + p['date'][5:] + '</td><td class="stk">' + stock + '</td><td class="n ' + pc(dpct) + '">' + pct(dpct) + '</td>'
                     + cells
                     + '<td class="n ' + pc(p['cum']) + '">' + (pct(p['cum']) if p['cum'] is not None else '未满') + '</td>'
                     + '<td class="ev">' + ev + '</td><td class="n' + wrcls + '">' + wr + '</td></tr>')
stocks = sorted({p['code'] + ' ' + str(p['name']) for p in picks})
dl = '<datalist id="stklist">' + ''.join('<option value="' + q(s) + '"></option>' for s in stocks) + '</datalist>'
h_main = ('<tr>'
          + '<th>日期' + sel('date', [(d[5:], d) for d in dates]) + '</th>'
          + '<th>股票<input class="flt" data-k="stock" list="stklist" placeholder="输入或选择">' + sel('cls', CL) + '</th>'
          + '<th>当日涨幅' + sel('pct', PC) + '</th>'
          + '<th>D+1涨幅' + sel('d1', UP) + '</th><th>D+2涨幅' + sel('d2', UP) + '</th><th>D+3涨幅' + sel('d3', UP) + '</th>'
          + '<th>D+4涨幅' + sel('d4', UP) + '</th><th>D+5涨幅' + sel('d5', UP) + '</th>'
          + '<th>5日累计' + sel('cum', CU) + '</th><th>大事件' + sel('ev', EV) + '</th><th>胜率' + sel('wr', WR) + '</th>'
          + '</tr>')
day_rows = []
for d in reversed(dates):
    rs = [p for p in picks if p['date'] == d]
    d1 = [p['paths'][0] for p in rs if p['paths']]
    m5 = [p['cum'] for p in rs if p['cum'] is not None]
    v1 = (sum(d1)/len(d1)) if d1 else None
    v5 = (sum(m5)/len(m5)) if m5 else None
    w5 = (round(sum(1 for x in m5 if x > 0)/len(m5)*100) if m5 else None)
    codes = ' / '.join(p['code'] + ' ' + str(p['name']) for p in rs)
    day_rows.append('<tr><td>' + d + '</td><td class="stk">' + codes + '</td><td class="n ' + pc(v1) + '">' + pct(v1)
                    + '</td><td class="n ' + pc(v5) + '">' + pct(v5) + '</td><td class="n">' + (str(w5) + '%' if w5 is not None else '-') + '</td></tr>')
ev_rows = []
for p in sorted([x for x in picks if x['events']], key=lambda x: x['date']):
    cells = ''.join('<span class="' + pc(v) + '">' + pct(v, '-') + '</span> ' for v in p['paths'])
    ev_rows.append('<tr data-date="' + p['date'][5:] + '" data-ev="' + q(flags(p)) + '"><td>' + p['date'][5:] + '</td><td class="stk"><b>' + p['code'] + '</b> '
                   + esc(p['name']) + '</td><td class="ev">' + esc(' ; '.join(p['events'])) + '</td><td>' + cells + '</td><td class="n '
                   + pc(p['cum']) + '">' + pct(p['cum']) + '</td></tr>')
ev_dates = sorted({p['date'] for p in picks if p['events']})
h_ev = ('<tr><th>日期' + sel('date', [(d[5:], d) for d in ev_dates]) + '</th><th>股票</th><th>大事件' + sel('ev', [x for x in EV if x[0] != 'none']) + '</th><th>D+1..D+5</th><th>5日累计</th></tr>')
order = ['all', 'zt_first', 'zt_multi', 'breakout', 'trend', 'other', '2026-07', '2026-08', '2026-09']
t41 = []
for k in order:
    s = stats.get(k)
    if not s: continue
    t41.append('<tr><td>' + NM[k] + '</td><td class="n">' + str(s['n']) + '</td><td class="n">' + n1(s['p_d1_up']*100) + '%</td><td class="n ' + pc(s['m_d1']) + '">' + pct(s['m_d1'])
               + '</td><td class="n">' + n1(s['d1_zt_rate']*100) + '%</td><td class="n">' + n1(s['p5_up']*100) + '%</td><td class="n ' + pc(s['m5']) + '">' + pct(s['m5'])
               + '</td><td class="n ' + pc(s['med5']) + '">' + pct(s['med5']) + '</td><td class="n">' + pct(s['best5']) + ' / ' + pct(s['worst5']) + '</td></tr>')
t41.append('<tr class="hl"><td>全市场基准（同期全部个股）</td><td class="n">' + str(base['n5']) + '</td><td class="n">' + n1(base['p1_up']*100) + '%</td><td class="n ' + pc(base['m1'])
           + '">' + pct(base['m1']) + '</td><td class="n">-</td><td class="n">' + n1(base['p5_up']*100) + '%</td><td class="n ' + pc(base['m5']) + '">' + pct(base['m5']) + '</td><td class="n">-</td><td class="n">-</td></tr>')
cum = [p['cum'] for p in picks if p['cum'] is not None]
t42 = []
for lo, hi in [(-100, -10), (-10, -5), (-5, 0), (0, 5), (5, 10), (10, 100)]:
    c = sum(1 for x in cum if lo <= x < hi)
    t42.append('<tr><td>' + str(lo) + '% ~ ' + str(hi) + '%</td><td class="n">' + str(c) + '</td><td class="n">' + n1(c/len(cum)*100) + '%</td></tr>')
pf = []
for d in dates:
    m5 = [p['cum'] for p in picks if p['date'] == d and p['cum'] is not None]
    if len(m5) == 5: pf.append(sum(m5)/5)
pw = sum(1 for x in pf if x > 0)
pavg = sum(pf)/len(pf)
t43 = ['<tr><td>有效样本天数</td><td class="n">' + str(len(pf)) + ' 个交易日</td></tr>',
       '<tr><td>组合5日为正的天数占比</td><td class="n">' + n1(pw/len(pf)*100) + '%（' + str(pw) + '/' + str(len(pf)) + '）</td></tr>',
       '<tr><td>组合5日平均收益</td><td class="n ' + pc(pavg) + '">' + pct(pavg) + '</td></tr>',
       '<tr><td>组合最好 / 最差</td><td class="n">' + pct(max(pf)) + ' / ' + pct(min(pf)) + '</td></tr>']
s = stats['all']
css = '''*{box-sizing:border-box}
body{margin:0;background:#f4f6fa;color:#0f172a;font:12.5px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;-webkit-text-size-adjust:100%}
.wrap{max-width:1600px;margin:0 auto;padding:14px 12px 60px}
h1{font-size:19px;margin:0 0 4px}
.meta{color:#64748b;font-size:12px;margin-bottom:10px}
.nav a{display:inline-block;font-size:12px;color:#1d4ed8;text-decoration:none;border:1px solid #93c5fd;background:#eff6ff;padding:4px 10px;border-radius:8px;margin:0 6px 6px 0}
h2{font-size:13.5px;margin:20px 0 8px;padding:8px 10px;background:#0f172a;color:#fff;border-radius:8px}
h2 span{font-weight:400;opacity:.72;font-size:11.5px;margin-left:6px}
.bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:0 0 8px;font-size:12px;color:#475569}
.bar button{font-size:12px;padding:3px 10px;border:1px solid #93c5fd;background:#eff6ff;color:#1d4ed8;border-radius:6px;cursor:pointer}
.scroll{overflow:auto;border-radius:8px;box-shadow:0 1px 3px rgba(15,23,42,.08);background:#fff}
table{border-collapse:collapse;width:100%;background:#fff;font-size:12px}
th,td{border:1px solid #e5eaf0;padding:4px 6px;text-align:left;white-space:nowrap;vertical-align:top}
th{background:#eef2f7;position:sticky;top:0;z-index:3;font-weight:650}
th select.flt,th input.flt{display:block;width:100%;margin-top:3px;font-size:11px;padding:1px 2px;border:1px solid #cbd5e1;border-radius:4px;background:#fff;color:#0f172a;font-weight:400;min-width:96px}
th input.flt{min-width:118px}
tbody tr:nth-child(even){background:#fafcff}
tr.hl{background:#eef2f7;font-weight:650}
td.n{text-align:right;font-variant-numeric:tabular-nums}
td.stk{white-space:normal;min-width:120px}
td.ev{white-space:normal;min-width:230px;color:#475569;font-size:11.5px}
.tag{font-size:10px;padding:0 4px;border-radius:4px;background:#e2e8f0;color:#475569}
.pos{color:#d81e3f}.neg{color:#0a8f5b}
.note{color:#64748b;font-size:11.5px;margin:8px 0 0;line-height:1.85}
footer{color:#64748b;font-size:11.5px;padding:18px 0 40px;line-height:1.8}
@media print{body{background:#fff}.nav,.bar,th select.flt,th input.flt{display:none!important}.scroll{overflow:visible;box-shadow:none}th{position:static}h2{background:#eee;color:#000}table{font-size:9.5px}td.ev{min-width:0}}
'''
js = '''(function(){
  function setup(tbl){
    var rows=[].slice.call(tbl.querySelectorAll('tbody tr'));
    var ctrls=[].slice.call(tbl.querySelectorAll('.flt'));
    function apply(){
      var n=0;
      for(var i=0;i<rows.length;i++){
        var r=rows[i], ok=true;
        for(var j=0;j<ctrls.length;j++){
          var c=ctrls[j], k=c.getAttribute('data-k'), v=(c.value||'').trim();
          if(!v) continue;
          var d=r.getAttribute('data-'+k)||'';
          if(k==='stock'){ if(d.toLowerCase().indexOf(v.toLowerCase())<0) ok=false; }
          else if(k='cls'){ if(d!==v) ok=false; }
          else if(k='date'){ var d5=d.slice(-5), v5=v.slice(-5); if(!(d===v||d5===v5)) ok=false; }
          else if(k==='ev'){
            if(v==='has'){ if(d==='') ok=false; }
            else if(v==='none'){ if(d!=='') ok=false; }
            else if(d.indexOf(v)<0) ok=false;
          }
          else if(k==='wr'){
            var w=(d==='')?NaN:parseFloat(d);
            if(v==='na'){ if(d!=='') ok=false; }
            else if(v==='c100'){ if(w!==100) ok=false; }
            else if(v==='ge80'){ if(!(w>=80)) ok=false; }
            else if(v==='ge60'){ if(!(w>=60)) ok=false; }
            else if(v==='le40'){ if(!(w<=40)) ok=false; }
            else if(v==='c0'){ if(w!==0) ok=false; }
          }
          else {
            var x=(d==='')?NaN:parseFloat(d);
            if(v==='up'){ if(!(x>0)) ok=false; }
            else if(v==='down'){ if(!(x<0)) ok=false; }
            else if(v==='zt'){ if(!(x>=9.5)) ok=false; }
            else if(v==='dt'){ if(!(x<=-9.5)) ok=false; }
            else if(v==='gt10'){ if(!(x>10)) ok=false; }
            else if(v==='lt1'){ if(!(x<-10)) ok=false; }
            else if(v==='ge5'){ if(!(x>=5)) ok=false; }
            else if(v==='b05'){ if(!(x>=0&&x<5)) ok=false; }
            else if(v==='na'){ if(d!=='') ok=false; }
          }
          if(!ok) break;
        }
        r.style.display = ok ? '' : 'none';
        if(ok) n++;
      }
      var id=tbl.getAttribute('data-cnt'), el=id?document.getElementById(id):null;
      if(el) el.textContent='命中 '+n+' / '+rows.length+' 行';
    }
    for(var j=0;j<ctrls.length;j++){ ctrls[j].addEventListener('input',apply); ctrls[j].addEventListener('change',apply); }
    var rid=tbl.getAttribute('data-reset'), rel=rid?document.getElementById(rid):null;
    if(rel) rel.addEventListener('click',function(){ for(var j=0;j<ctrls.length;j++){ctrls[j].value='';} apply(); });
    apply();
  }
  var ts=document.querySelectorAll('table[data-filters]');
  for(var i=0;i<ts.length;i++) setup(ts[i]);
})();'''
H = []
H.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">')
H.append('<meta name="viewport" content="width=device-width,initial-scale=1"><title>表格版 · 选股结果 2026-07-13~09-11</title>')
H.append('<style>' + css + '</style></head><body><div class="wrap">')
_pv = (R.get('provisional') or {})
if _pv.get('applied'):
    H.append('<div class="meta" style="background:#fff4d6;border:1px solid #dfc06a;border-radius:8px;padding:8px 10px;color:#6b4d0d;margin:0 0 8px">14:20 盘中快照（未收盘）· ' + str(_pv.get('date')) + ' · 抓取于 ' + str(_pv.get('snapshot_at')) + ' · 供尾盘买入参考；已发布的选股记录不会因次日收盘数据而改写</div>')
H.append('<h1>表格版 · A股选股策略回测结果</h1>')
H.append('<div class="meta">' + rng + ' · 全市场5562只 · ' + str(len(picks)) + ' 只标的 · ' + str(len(dates)) + ' 个交易日 · 表头下拉筛选可直接用（无 JS 时显示全部）</div>')
H.append('<div class="nav"><a href="index.html">← 返回看板</a><a href="garp.html">成长价值筛选（新）</a><a href="#m1">主表</a><a href="#m2">每日组合汇总</a><a href="#m3">事件专表</a><a href="#m4">统计评估</a></div>')
H.append('<h2 id="m1">主表 · 每只入选股票单独一行<span>胜率＝5个交易日中的上涨天数占比；「当日涨幅」＝选股当天涨幅</span></h2>')
H.append('<div class="bar"><button id="rst1">重置全部筛选</button><span id="cnt1">命中 ' + str(len(picks)) + ' / ' + str(len(picks)) + ' 行</span></div>')
H.append('<div class="scroll"><table data-filters="1" data-cnt="cnt1" data-reset="rst1"><thead>' + h_main + '</thead><tbody>' + ''.join(main_rows) + '</tbody></table></div>' + dl)
H.append('<h2 id="m2">每日组合汇总<span>' + str(len(day_rows)) + ' 个交易日</span></h2>')
H.append('<div class="scroll"><table><thead><tr><th>日期</th><th>选出的5只</th><th>组合D+1均值</th><th>组合5日均值</th><th>组合5日胜率</th></tr></thead><tbody>' + ''.join(day_rows) + '</tbody></table></div>')
H.append('<h2 id="m3">事件专表 · 持仓5日内出现的关键事件<span>' + str(len(ev_rows)) + ' 条</span></h2>')
H.append('<div class="bar"><button id="rst2">重置筛选</button><span id="cnt2">命中 ' + str(len(ev_rows)) + ' / ' + str(len(ev_rows)) + ' 行</span></div>')
H.append('<div class="scroll"><table data-filters="1" data-cnt="cnt2" data-reset="rst2"><thead>' + h_ev + '</thead><tbody>' + ''.join(ev_rows) + '</tbody></table></div>')
H.append('<h2 id="m4">统计评估</h2>')
H.append('<div class="scroll"><table><thead><tr><th>分组</th><th>样本</th><th>次日上涨率</th><th>次日平均</th><th>次日再涨停率</th><th>5日上涨率</th><th>5日平均</th><th>5日中位数</th><th>5日最好/最差</th></tr></thead><tbody>' + ''.join(t41) + '</tbody></table></div>')
H.append('<h2>5日累计收益分布<span>完整样本 ' + str(len(cum)) + ' 只</span></h2>')
H.append('<div class="scroll"><table style="max-width:460px"><thead><tr><th>5日累计区间</th><th>只数</th><th>占比</th></tr></thead><tbody>' + ''.join(t42) + '</tbody></table></div>')
H.append('<h2>组合层面（每日等权买入5只，持有5个交易日）</h2>')
H.append('<div class="scroll"><table style="max-width:460px"><tbody>' + ''.join(t43) + '</tbody></table></div>')
H.append('<h2>结论</h2><div class="note">')
H.append('1. 这是“1日爆破力”策略：次日上涨率 ' + n1(s['p_d1_up']*100) + '%、次日平均 +' + n2(s['m_d1']) + '%，高于全市场基准（' + n1(base['p1_up']*100) + '% / +' + n2(base['m1']) + '%）；持有到第5日胜率降到 '
         + n1(s['p5_up']*100) + '%、平均 ' + n2(s['m5']) + '%，低于基准（' + n1(base['p5_up']*100) + '% / +' + n2(base['m5']) + '%）。<br>')
H.append('2. 只有连板股能拿5天：连板组5日胜率 ' + n1(stats['zt_multi']['p5_up']*100) + '%、5日平均 ' + pct(stats['zt_multi']['m5']) + '；首板组 ' + n1(stats['zt_first']['p5_up']*100) + '% / ' + pct(stats['zt_first']['m5']) + '。<br>')
H.append('3. 放量突破类几乎无效（样本 ' + str(stats['breakout']['n']) + ' 只，次日胜率 ' + n1(stats['breakout']['p_d1_up']*100) + '%）。<br>')
H.append('4. 尾部风险：' + format(sum(1 for x in cum if x <= -5)/len(cum)*100, '.0f') + '% 的标的5日累计亏5%以上，最差 ' + pct(min(cum)) + '，最好 ' + pct(max(cum)) + '。</div>')
H.append('<footer>口径：①收益为“选股日收盘 → D+k收盘”的前复权持有收益，未扣手续费/印花税/滑点，未处理“次日一字板买不进”；②<b>胜率＝该股持仓5个交易日中的上涨天数占比</b>（例 4/5 = 80%）；<b>当日涨幅＝该股在选股当天的涨跌幅</b>；③板块分项用新浪行业成分股涨跌中位数替代同花顺行业+资金流，板质量分项用价格推导替代封单/首封时间；④全市场基准为同期全部个股（样本 ' + str(base['n5']) + '）等权统计；⑤历史统计，不构成投资建议。</footer>')
H.append('</div><script>' + js + '</script></body></html>')
os.makedirs('docs', exist_ok=True)
open('docs/tables.html', 'w', encoding='utf-8', newline=chr(10)).write(chr(10).join(H))
print('docs/tables.html', os.path.getsize('docs/tables.html'), '| 主表', len(main_rows), '| 每日', len(day_rows), '| 事件', len(ev_rows), '| 控件', h_main.count('class="flt"') + h_ev.count('class="flt"'))
