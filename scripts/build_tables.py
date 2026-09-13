# -*- coding: utf-8 -*-
'''Table-only version of the dashboard -> docs/tables.html (print / copy friendly).'''
import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')
F = json.load(open('data/final.json', encoding='utf-8'))
R = json.load(open('data/result.json', encoding='utf-8'))
picks = F['picks']; base = F['base']; stats = R['stats']
CN = {'zt_first': '首板涨停', 'zt_multi': '连板涨停', 'trend': '趋势多头', 'breakout': '放量突破', 'other': '其他'}
NM = {'all': '全部选出', 'zt_first': '首板涨停', 'zt_multi': '连板涨停', 'breakout': '放量突破',
      'trend': '趋势多头', 'other': '其他', '2026-07': '2026年7月', '2026-08': '2026年8月', '2026-09': '2026年9月'}
def pct(x, na='未满'):
    return na if x is None else (('+' if x >= 0 else '') + format(float(x), '.2f') + '%')
def pc(x):
    return '' if x is None else ('pos' if x >= 0 else 'neg')
def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
def n1(x): return format(float(x), '.1f')
def n2(x): return format(float(x), '.2f')
dates = sorted({p['date'] for p in picks})
rng = R['window'][0] + ' ~ ' + R['window'][1]
# 表1
t1 = []
for d in dates:
    rs = [p for p in picks if p['date'] == d]
    d1 = [p['paths'][0] for p in rs if p['paths']]
    m5 = [p['cum'] for p in rs if p['cum'] is not None]
    v1 = (sum(d1)/len(d1)) if d1 else None
    v5 = (sum(m5)/len(m5)) if m5 else None
    w5 = (round(sum(1 for x in m5 if x > 0)/len(m5)*100) if m5 else None)
    nm = ' / '.join(p['code'] + ' ' + str(p['name']) + ' ' + n1(p['score']) + ' ' + CN.get(p['cls'], p['cls']) for p in rs)
    t1.append('<tr><td>' + d + '</td><td class="n ' + pc(v1) + '">' + pct(v1) + '</td><td class="n ' + pc(v5) + '">' + pct(v5)
              + '</td><td class="n">' + (str(w5) + '%' if w5 is not None else '-') + '</td><td class="ev">' + nm + '</td></tr>')
# 表2
t2 = []
for p in picks:
    ps = list(p['paths']) + [None]*(5 - len(p['paths']))
    cells = ''.join('<td class="n ' + pc(v) + '">' + (pct(v, '-') if v is not None else '-') + '</td>' for v in ps)
    ev = esc(' ; '.join(p['events'])) if p['events'] else '-'
    t2.append('<tr><td>' + p['date'][5:] + '</td><td>' + p['code'] + '</td><td>' + esc(p['name']) + '</td><td class="n">' + n1(p['score'])
              + '</td><td>' + CN.get(p['cls'], p['cls']) + '</td>' + cells + '<td class="n ' + pc(p['cum']) + '">' + pct(p['cum'])
              + '</td><td class="ev">' + ev + '</td></tr>')
# 表3
t3 = []
for p in sorted([x for x in picks if x['events']], key=lambda x: x['date']):
    cells = ''.join('<span class="' + pc(v) + '">' + pct(v, '-') + '</span> ' for v in p['paths'])
    t3.append('<tr><td>' + p['date'][5:] + '</td><td>' + p['code'] + '</td><td>' + esc(p['name']) + '</td><td class="ev">'
              + esc(' ; '.join(p['events'])) + '</td><td>' + cells + '</td><td class="n ' + pc(p['cum']) + '">' + pct(p['cum']) + '</td></tr>')
# 表4.1
order = ['all', 'zt_first', 'zt_multi', 'breakout', 'trend', 'other', '2026-07', '2026-08', '2026-09']
t41 = []
for k in order:
    s = stats.get(k)
    if not s: continue
    t41.append('<tr><td>' + NM[k] + '</td><td class="n">' + str(s['n']) + '</td><td class="n">' + n1(s['p_d1_up']*100) + '%</td><td class="n ' + pc(s['m_d1']) + '">'
               + pct(s['m_d1']) + '</td><td class="n">' + n1(s['d1_zt_rate']*100) + '%</td><td class="n">' + n1(s['p5_up']*100) + '%</td><td class="n '
               + pc(s['m5']) + '">' + pct(s['m5']) + '</td><td class="n ' + pc(s['med5']) + '">' + pct(s['med5']) + '</td><td class="n">' + pct(s['best5']) + ' / ' + pct(s['worst5']) + '</td></tr>')
t41.append('<tr class="hl"><td>全市场基准（同期全部个股）</td><td class="n">' + str(base['n5']) + '</td><td class="n">' + n1(base['p1_up']*100) + '%</td><td class="n '
           + pc(base['m1']) + '">' + pct(base['m1']) + '</td><td class="n">-</td><td class="n">' + n1(base['p5_up']*100) + '%</td><td class="n ' + pc(base['m5'])
           + '">' + pct(base['m5']) + '</td><td class="n">-</td><td class="n">-</td></tr>')
# 表4.2
cum = [p['cum'] for p in picks if p['cum'] is not None]
t42 = []
for lo, hi in [(-100, -10), (-10, -5), (-5, 0), (0, 5), (5, 10), (10, 100)]:
    c = sum(1 for x in cum if lo <= x < hi)
    t42.append('<tr><td>' + str(lo) + '% ~ ' + str(hi) + '%</td><td class="n">' + str(c) + '</td><td class="n">' + n1(c/len(cum)*100) + '%</td></tr>')
# 表4.3
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
.wrap{max-width:1500px;margin:0 auto;padding:14px 12px 60px}
h1{font-size:19px;margin:0 0 4px}
.meta{color:#64748b;font-size:12px;margin-bottom:10px}
.nav a{display:inline-block;font-size:12px;color:#1d4ed8;text-decoration:none;border:1px solid #93c5fd;background:#eff6ff;padding:4px 10px;border-radius:8px;margin-right:6px}
h2{font-size:13.5px;margin:20px 0 8px;padding:8px 10px;background:#0f172a;color:#fff;border-radius:8px}
h2 span{font-weight:400;opacity:.7;font-size:11.5px;margin-left:6px}
.scroll{overflow:auto;border-radius:8px;box-shadow:0 1px 3px rgba(15,23,42,.08);background:#fff}
table{border-collapse:collapse;width:100%;background:#fff;font-size:12px}
th,td{border:1px solid #e5eaf0;padding:4px 6px;text-align:left;white-space:nowrap}
th{background:#eef2f7;position:sticky;top:0;z-index:2;font-weight:650}
tbody tr:nth-child(even){background:#fafcff}
tr.hl{background:#eef2f7;font-weight:650}
td.n{text-align:right;font-variant-numeric:tabular-nums}
td.ev{white-space:normal;min-width:240px;color:#475569;font-size:11.5px}
.pos{color:#d81e3f}.neg{color:#0a8f5b}
.note{color:#64748b;font-size:11.5px;margin:8px 0 0;line-height:1.8}
footer{color:#64748b;font-size:11.5px;padding:18px 0 40px;line-height:1.8}
@media print{body{background:#fff}.nav{display:none}.scroll{overflow:visible;box-shadow:none}th{position:static}h2{background:#eee;color:#000}table{font-size:10px}}
'''
H = []
H.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">')
H.append('<meta name="viewport" content="width=device-width,initial-scale=1"><title>表格版 · A股选股策略回测 2026-07-13~09-11</title>')
H.append('<style>' + css + '</style></head><body><div class="wrap">')
H.append('<h1>表格版 · A股选股策略回测结果</h1>')
H.append('<div class="meta">' + rng + ' · 全市场5562只 · ' + str(len(picks)) + ' 只标的 · ' + str(len(dates)) + ' 个交易日 · 数据源：同花顺前复权 + 东方财富涨停池/龙虎榜/公告</div>')
H.append('<div class="nav"><a href="index.html">← 返回看板</a><a href="#t1">表1 每日选股</a><a href="#t2">表2 逐日明细</a><a href="#t3">表3 大事件</a><a href="#t4">表4 统计评估</a></div>')
H.append('<h2 id="t1">表1 · 每个交易日选出的5只<span>共 ' + str(len(dates)) + ' 个交易日</span></h2>')
H.append('<div class="scroll"><table><thead><tr><th>日期</th><th>组合D+1均值</th><th>组合5日均值</th><th>5日胜率</th><th>选出的5只（代码 名称 评分 形态）</th></tr></thead><tbody>' + ''.join(t1) + '</tbody></table></div>')
H.append('<h2 id="t2">表2 · 选后5个交易日逐日涨跌幅<span>共 ' + str(len(picks)) + ' 只</span></h2>')
H.append('<div class="scroll"><table><thead><tr><th>日期</th><th>代码</th><th>名称</th><th>评分</th><th>形态</th><th>D+1</th><th>D+2</th><th>D+3</th><th>D+4</th><th>D+5</th><th>5日累计</th><th>5日内关键事件</th></tr></thead><tbody>' + ''.join(t2) + '</tbody></table></div>')
H.append('<h2 id="t3">表3 · 持仓5日内出现的关键事件<span>' + str(len(t3)) + ' 条</span></h2>')
H.append('<div class="scroll"><table><thead><tr><th>日期</th><th>代码</th><th>名称</th><th>事件</th><th>D+1..D+5</th><th>5日累计</th></tr></thead><tbody>' + ''.join(t3) + '</tbody></table></div>')
H.append('<h2 id="t4">表4 · 统计评估</h2>')
H.append('<div class="scroll"><table><thead><tr><th>分组</th><th>样本</th><th>次日上涨率</th><th>次日平均</th><th>次日再涨停率</th><th>5日上涨率</th><th>5日平均</th><th>5日中位数</th><th>5日最好/最差</th></tr></thead><tbody>' + ''.join(t41) + '</tbody></table></div>')
H.append('<h2>表4.2 · 5日累计收益分布<span>完整样本 ' + str(len(cum)) + ' 只</span></h2>')
H.append('<div class="scroll"><table style="max-width:460px"><thead><tr><th>5日累计区间</th><th>只数</th><th>占比</th></tr></thead><tbody>' + ''.join(t42) + '</tbody></table></div>')
H.append('<h2>表4.3 · 组合层面（每日等权买入5只，持有5个交易日）</h2>')
H.append('<div class="scroll"><table style="max-width:460px"><tbody>' + ''.join(t43) + '</tbody></table></div>')
H.append('<h2>结论</h2><div class="note">')
H.append('1. 这是“1日爆破力”策略：次日上涨率 ' + n1(s['p_d1_up']*100) + '%、次日平均 +' + n2(s['m_d1']) + '%，高于全市场基准（' + n1(base['p1_up']*100) + '% / +' + n2(base['m1']) + '%）；但持有到第5日胜率降到 '
         + n1(s['p5_up']*100) + '%、平均 ' + n2(s['m5']) + '%，低于基准（' + n1(base['p5_up']*100) + '% / +' + n2(base['m5']) + '%）。<br>')
H.append('2. 只有连板股能拿5天：连板组5日胜率 ' + n1(stats['zt_multi']['p5_up']*100) + '%、5日平均 ' + pct(stats['zt_multi']['m5']) + '；首板组 ' + n1(stats['zt_first']['p5_up']*100) + '% / ' + pct(stats['zt_first']['m5']) + '。<br>')
H.append('3. 放量突破类几乎无效（样本 ' + str(stats['breakout']['n']) + ' 只，次日胜率 ' + n1(stats['breakout']['p_d1_up']*100) + '%）。<br>')
H.append('4. 尾部风险：' + format(sum(1 for x in cum if x <= -5)/len(cum)*100, '.0f') + '% 的标的5日累计亏5%以上，最差 ' + pct(min(cum)) + '，最好 ' + pct(max(cum)) + '。</div>')
H.append('<footer>口径与局限：①收益为“选股日收盘 → D+k收盘”的前复权持有收益，未扣手续费/印花税/滑点，未处理“次日一字板买不进”；②板块分项用新浪行业成分股涨跌中位数替代同花顺行业+资金流，板质量分项用价格推导替代封单/首封时间；③全市场基准为同期全部个股（样本 ' + str(base['n5']) + '）等权统计；④历史统计，不构成投资建议。</footer>')
H.append('</div></body></html>')
os.makedirs('docs', exist_ok=True)
open('docs/tables.html', 'w', encoding='utf-8', newline=chr(10)).write(chr(10).join(H))
print('docs/tables.html', os.path.getsize('docs/tables.html'), 'bytes | t1', len(t1), 't2', len(t2), 't3', len(t3))
