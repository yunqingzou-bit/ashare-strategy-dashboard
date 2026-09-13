# -*- coding: utf-8 -*-
'''Server-side rendered responsive dashboard (works without JS).'''
import json, os
F = json.load(open('data/final.json', encoding='utf-8'))
R = json.load(open('data/result.json', encoding='utf-8'))
base = F['base']; stats = R['stats']; picks = F['picks']
CN = {'zt_first': '首板涨停', 'zt_multi': '连板涨停', 'trend': '趋势多头', 'breakout': '放量突破', 'other': '其他'}
NM = {'all': '全部选出', 'zt_first': '首板涨停', 'zt_multi': '连板涨停', 'breakout': '放量突破',
      'trend': '趋势多头', 'other': '其他', '2026-07': '2026年7月', '2026-08': '2026年8月', '2026-09': '2026年9月'}
def pct(x, na='未满'):
    if x is None: return na
    return ('+' if x >= 0 else '') + format(float(x), '.2f') + '%'
def pc(x):
    if x is None: return ''
    return 'pos' if x >= 0 else 'neg'
def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
def tag(k): return '<span class="tag t-' + k + '">' + CN.get(k, k) + '</span>'
dates = sorted({p['date'] for p in picks})
dayrows = []
for d in dates:
    rs = [p for p in picks if p['date'] == d]
    d1 = [p['paths'][0] for p in rs if p['paths']]
    m5 = [p['cum'] for p in rs if p['cum'] is not None]
    dm = 'D+1 ' + (pct(sum(d1)/len(d1)) if d1 else '未满')
    dm += ' · 5日 ' + (pct(sum(m5)/len(m5)) if m5 else '未满')
    dm += ' · 胜率 ' + ((str(round(sum(1 for x in m5 if x > 0)/len(m5)*100)) + '%') if m5 else '-')
    chips = ''.join('<span class="chip"><b>' + p['code'] + '</b>' + esc(p['name'])
                    + '<span style="color:#94a3b8">' + format(p['score'], '.1f') + '</span>' + tag(p['cls']) + '</span>' for p in rs)
    dayrows.append('<div class="day"><div class="dh"><span>' + d[5:] + '</span><span class="dm">' + dm + '</span></div><div class="chips">' + chips + '</div></div>')
trend = [d for d in dates]
bars = []
vals = []
for d in dates:
    rs = [p for p in picks if p['date'] == d]
    m5 = [p['cum'] for p in rs if p['cum'] is not None]
    vals.append((d[5:], (sum(m5)/len(m5)) if m5 else None))
mx = max([abs(v) for _, v in vals if v is not None] + [1])
for lab, v in vals:
    if v is None:
        bars.append('<div class="bar" style="height:4px;background:#cbd5e1" title="' + lab + ' 未满5日"></div>')
    else:
        h = max(3, int(abs(v)/mx*92))
        col = 'var(--up)' if v >= 0 else 'var(--dn)'
        bars.append('<div class="bar" style="height:' + str(h) + 'px;background:' + col + '" title="' + lab + ' 组合5日均值 ' + pct(v) + '"></div>')
det = []
for p in picks:
    ps = list(p['paths']) + [None]*(5-len(p['paths']))
    tds = '<td data-l="日期">' + p['date'][5:] + '</td><td data-l="代码">' + p['code'] + '</td><td data-l="名称">' + esc(p['name']) + '</td>'
    tds += '<td data-l="评分" class="num">' + format(p['score'], '.1f') + '</td><td data-l="形态">' + CN.get(p['cls'], p['cls']) + '</td>'
    for v in ps:
        tds += '<td data-l="D+k" class="num ' + pc(v) + '">' + (pct(v, '-') if v is not None else '-') + '</td>'
    tds += '<td data-l="5日累计" class="num ' + pc(p['cum']) + '">' + pct(p['cum']) + '</td>'
    ev = esc(' ; '.join(p['events'])) if p['events'] else '-'
    tds += '<td data-l="关键事件" class="ev">' + ev + '</td>'
    txt = (p['code'] + ' ' + str(p['name']) + ' ' + str(p.get('board') or '')).replace('"', '')
    det.append('<tr data-d="' + p['date'] + '" data-d1="' + ('%.4f' % p['paths'][0] if p['paths'] else '-999')
               + '" data-cum="' + ('%.4f' % p['cum'] if p['cum'] is not None else '-999')
               + '" data-k="' + p['cls'] + '" data-txt="' + txt + '">' + tds + '</tr>')
evt = []
for p in sorted([x for x in picks if x['events']], key=lambda x: x['date']):
    cells = ''.join('<span class="' + pc(v) + '">' + pct(v, '-') + '</span> ' for v in p['paths'])
    evt.append('<tr data-d="' + p['date'] + '"><td data-l="日期">' + p['date'][5:] + '</td><td data-l="代码">' + p['code']
               + '</td><td data-l="名称">' + esc(p['name']) + '</td><td data-l="事件" class="ev">' + esc(' ; '.join(p['events']))
               + '</td><td data-l="逐日">' + cells + '</td><td data-l="5日累计" class="num ' + pc(p['cum']) + '">' + pct(p['cum']) + '</td></tr>')
order = ['all', 'zt_first', 'zt_multi', 'breakout', 'trend', 'other', '2026-07', '2026-08', '2026-09']
strows = []
for k in order:
    s = stats.get(k)
    if not s: continue
    strows.append('<tr><td data-l="分组">' + NM[k] + '</td><td data-l="样本" class="num">' + str(s['n']) + '</td>'
                  + '<td data-l="次日上涨率" class="num">' + format(s['p_d1_up']*100, '.1f') + '%</td>'
                  + '<td data-l="次日平均" class="num ' + pc(s['m_d1']) + '">' + pct(s['m_d1']) + '</td>'
                  + '<td data-l="次日再涨停" class="num">' + format(s['d1_zt_rate']*100, '.1f') + '%</td>'
                  + '<td data-l="5日上涨率" class="num">' + format(s['p5_up']*100, '.1f') + '%</td>'
                  + '<td data-l="5日平均" class="num ' + pc(s['m5']) + '">' + pct(s['m5']) + '</td>'
                  + '<td data-l="5日中位" class="num ' + pc(s['med5']) + '">' + pct(s['med5']) + '</td>'
                  + '<td data-l="最好/最差" class="num">' + pct(s['best5']) + ' / ' + pct(s['worst5']) + '</td></tr>')
strows.append('<tr style="background:#f1f5f9;font-weight:650"><td data-l="分组">全市场基准（同期全部个股）</td><td data-l="样本" class="num">' + str(base['n5'])
              + '</td><td data-l="次日上涨率" class="num">' + format(base['p1_up']*100, '.1f') + '%</td>'
              + '<td data-l="次日平均" class="num ' + pc(base['m1']) + '">' + pct(base['m1']) + '</td><td data-l="次日再涨停" class="num">-</td>'
              + '<td data-l="5日上涨率" class="num">' + format(base['p5_up']*100, '.1f') + '%</td>'
              + '<td data-l="5日平均" class="num ' + pc(base['m5']) + '">' + pct(base['m5']) + '</td><td data-l="5日中位" class="num">-</td><td data-l="最好/最差" class="num">-</td></tr>')
cum = [p['cum'] for p in picks if p['cum'] is not None]
bk = [(-100, -10), (-10, -5), (-5, 0), (0, 5), (5, 10), (10, 100)]
cnts = [sum(1 for x in cum if a <= x < b) for a, b in bk]
bmx = max(cnts + [1])
dbars = []
for (a, b), c2 in zip(bk, cnts):
    w = max(1, int(c2/bmx*100))
    col = 'var(--up)' if a >= 0 else 'var(--dn)'
    dbars.append('<div class="brow"><span>' + str(a) + '% ~ ' + str(b) + '%</span><span class="bar2"><i style="width:' + str(w) + '%;background:' + col + '"></i></span><span class="num" style="text-align:right">' + str(c2) + ' 只 ' + format(c2/len(cum)*100, '.1f') + '%</span></div>')
pf = []
for d in dates:
    rs = [p for p in picks if p['date'] == d]
    m5 = [p['cum'] for p in rs if p['cum'] is not None]
    if len(m5) == 5: pf.append(sum(m5)/5)
pw = sum(1 for x in pf if x > 0)
pavg = sum(pf)/len(pf)
s = stats['all']
kpi = [('回测区间', R['window'][0][5:] + ' ~ ' + R['window'][1][5:], str(len(dates)) + ' 个交易日 · ' + str(len(picks)) + ' 只标的', ''),
       ('次日上涨率', format(s['p_d1_up']*100, '.1f') + '%', '基准 ' + format(base['p1_up']*100, '.1f') + '%', 'pos'),
       ('次日平均涨幅', '+' + format(s['m_d1'], '.2f') + '%', '基准 +' + format(base['m1'], '.2f') + '%', 'pos'),
       ('5日累计上涨率', format(s['p5_up']*100, '.1f') + '%', '基准 ' + format(base['p5_up']*100, '.1f') + '%', 'neg'),
       ('5日平均收益', format(s['m5'], '.2f') + '%', '基准 +' + format(base['m5'], '.2f') + '%', 'neg'),
       ('连板组5日胜率', format(stats['zt_multi']['p5_up']*100, '.1f') + '%', '首板组 ' + format(stats['zt_first']['p5_up']*100, '.1f') + '%', 'pos')]
kpis = ''.join('<div class="kpi"><div class="k">' + a + '</div><div class="v ' + d + '">' + b + '</div><div class="n">' + c + '</div></div>' for a, b, c, d in kpi)
CSSADD = open('scripts/assets/dash_add.css', encoding='utf-8').read()
JS = open('scripts/assets/dash2.js', encoding='utf-8').read()
H = []
H.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">')
H.append('<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">')
H.append('<meta name="theme-color" content="#0f172a"><title>选股策略回测看板 2026-07-13~09-11</title>')
H.append('<style>' + open('scripts/assets/dash.css', encoding='utf-8').read() + CSSADD + '</style><noscript><style>.sec{display:block!important}.tabs{display:none}</style></noscript></head><body>')
H.append('<header class="top"><div class="in"><h1>A股选股策略回测看板</h1><div class="sub">' + R['window'][0] + ' ~ ' + R['window'][1]
         + ' · 全市场5562只 · 225只标的 · 数据源：同花顺前复权 + 东方财富涨停池/龙虎榜/公告</div></div></header>')
H.append('<div class="wrap"><div class="kpis">' + kpis + '</div>')
H.append('<div class="card"><h2>每日选股组合的5日累计收益（等权5只）<span>红=正 绿=负 · 悬停看数值</span></h2><div class="bd"><div class="chart">' + ''.join(bars) + '</div><div class="axis"><span>' + dates[0][5:] + '</span><span>' + dates[len(dates)//2][5:] + '</span><span>' + dates[-1][5:] + '</span></div></div></div>')
H.append('<div class="tabs" id="tb"><button data-v="s1" class="on">每日选股</button><button data-v="s2">逐日明细</button><button data-v="s3">大事件</button><button data-v="s4">统计评估</button></div>')
H.append('<section id="s1" class="sec on"><div class="card"><h2>表1 · 每个交易日选出的5只<span>共 ' + str(len(dates)) + ' 个交易日</span></h2><div class="bd"><div class="grid-days">' + ''.join(dayrows) + '</div></div></div></section>')
H.append('<section id="s2" class="sec"><div class="card"><h2>表2 · 选后5个交易日逐日涨跌幅<span id="cnt">共 ' + str(len(picks)) + ' 只</span></h2><div class="bd">')
H.append('<div class="tools"><input id="q" placeholder="搜索代码 / 名称 / 行业"><select id="kf"><option value="">全部形态</option>' + ''.join('<option value="' + k + '">' + v + '</option>' for k, v in CN.items()) + '</select><select id="sk"><option value="d">按日期</option><option value="d1">按次日涨幅</option><option value="cum">按5日累计</option></select></div>')
H.append('<div class="tw"><table class="resp"><thead><tr><th>日期</th><th>代码</th><th>名称</th><th>评分</th><th>形态</th><th>D+1</th><th>D+2</th><th>D+3</th><th>D+4</th><th>D+5</th><th>5日累计</th><th>5日内关键事件</th></tr></thead><tbody id="db">' + ''.join(det) + '</tbody></table></div></div></div></section>')
H.append('<section id="s3" class="sec"><div class="card"><h2>表3 · 持仓5日内出现的关键事件<span>' + str(len(evt)) + ' 条：龙虎榜净买额+席位性质+涨跌停/异动</span></h2><div class="bd"><div class="tw"><table class="resp"><thead><tr><th>日期</th><th>代码</th><th>名称</th><th>事件</th><th>D+1..D+5</th><th>5日累计</th></tr></thead><tbody>' + ''.join(evt) + '</tbody></table></div></div></div></section>')
H.append('<section id="s4" class="sec">')
H.append('<div class="card"><h2>表4.1 · 分组成功率 vs 基准<span>样本为选出的225只</span></h2><div class="bd"><div class="tw"><table class="resp"><thead><tr><th>分组</th><th>样本</th><th>次日上涨率</th><th>次日平均</th><th>次日再涨停率</th><th>5日上涨率</th><th>5日平均</th><th>5日中位数</th><th>5日最好/最差</th></tr></thead><tbody>' + ''.join(strows) + '</tbody></table></div></div></div>')
H.append('<div class="card"><h2>表4.2 · 5日累计收益分布<span>完整样本 ' + str(len(cum)) + ' 只</span></h2><div class="bd"><div class="bars">' + ''.join(dbars) + '</div></div></div>')
H.append('<div class="card"><h2>表4.3 · 组合层面（每日等权买入5只，持有5个交易日）</h2><div class="bd"><div class="bars">')
H.append('<div class="brow"><span>有效天数</span><span>' + str(len(pf)) + ' 个交易日</span><span></span></div>')
H.append('<div class="brow"><span>为正占比</span><span class="' + pc(pavg) + '">' + format(pw/len(pf)*100, '.1f') + '%</span><span>' + str(pw) + '/' + str(len(pf)) + '</span></div>')
H.append('<div class="brow"><span>平均收益</span><span class="' + pc(pavg) + '">' + pct(pavg) + '</span><span></span></div>')
H.append('<div class="brow"><span>最好 / 最差</span><span>' + pct(max(pf)) + ' / ' + pct(min(pf)) + '</span><span></span></div>')
H.append('</div></div></div>')
H.append('<div class="card"><h2>结论</h2><div class="bd"><div class="hint">')
H.append('<b>1. 这是“1日爆破力”策略，不是“5日持有”策略。</b>次日上涨率 ' + format(s['p_d1_up']*100, '.1f') + '%、次日平均 +' + format(s['m_d1'], '.2f') + '%，均显著高于全市场基准（' + format(base['p1_up']*100, '.1f') + '% / +' + format(base['m1'], '.2f') + '%）；但持有到第5日，胜率降到 ' + format(s['p5_up']*100, '.1f') + '%、平均 ' + format(s['m5'], '.2f') + '%，<b>低于</b>基准（' + format(base['p5_up']*100, '.1f') + '% / +' + format(base['m5'], '.2f') + '%）。<br><br>')
H.append('<b>2. 只有连板股能拿5天。</b>连板组（' + str(stats['zt_multi']['n']) + '只）：次日 ' + format(stats['zt_multi']['p_d1_up']*100, '.1f') + '%、5日胜率 ' + format(stats['zt_multi']['p5_up']*100, '.1f') + '%、5日平均 ' + pct(stats['zt_multi']['m5']) + '；首板组（' + str(stats['zt_first']['n']) + '只）：次日 ' + format(stats['zt_first']['p_d1_up']*100, '.1f') + '%、5日胜率 ' + format(stats['zt_first']['p5_up']*100, '.1f') + '%、5日平均 ' + pct(stats['zt_first']['m5']) + '。<br><br>')
H.append('<b>3. 放量突破类几乎无效</b>（样本 ' + str(stats['breakout']['n']) + ' 只，次日胜率 ' + format(stats['breakout']['p_d1_up']*100, '.1f') + '%），与9/11大样本条件概率（45.5%）一致。<br><br>')
H.append('<b>4. 尾部风险实在：</b>' + format(sum(1 for x in cum if x <= -5)/len(cum)*100, '.0f') + '% 的标的5日累计亏5%以上，最差 ' + pct(min(cum)) + '，最好 ' + pct(max(cum)) + '。<br><br>')
H.append('<b>5. 改进方向：</b>把“次日兑现”写进纪律（D+1 不创新高/不封板即走），持有期从5天压到1–2天；上调“连板+龙虎榜净买为正”权重，下调“首板+高换手”权重。')
H.append('</div></div></div></section>')
H.append('<footer><b>口径与局限：</b>①收益为“选股日收盘 → D+k收盘”的前复权持有收益，未扣手续费/印花税/滑点，也未处理“次日一字板买不进”，实际可执行收益低于本表；②回放时板块分项用新浪行业(49类)成分股涨跌中位数替代同花顺行业+资金流，板质量分项用价格推导替代封单/首封时间（东财涨停池历史仅可回溯约3周）；③全市场基准为同期全部个股（样本 ' + str(base['n5']) + '）的等权统计；④历史统计，不构成投资建议。</footer>')
H.append('</div><script>' + JS + '</script></body></html>')
os.makedirs('docs', exist_ok=True)
open('docs/index.html', 'w', encoding='utf-8').write(chr(10).join(H))
print('bytes', os.path.getsize('docs/index.html'), 'days', len(dates), 'picks', len(picks), 'events', len(evt))

# ---- post-process: render 表1 as a real table (not cards) ----
import re as _re
_p = 'docs/index.html'
_t = open(_p, encoding='utf-8').read()
_rows = []
for _d in dates:
    _rs = [x for x in picks if x['date'] == _d]
    _d1 = [x['paths'][0] for x in _rs if x['paths']]
    _m5 = [x['cum'] for x in _rs if x['cum'] is not None]
    _v1 = (sum(_d1) / len(_d1)) if _d1 else None
    _v5 = (sum(_m5) / len(_m5)) if _m5 else None
    _w5 = (round(sum(1 for y in _m5 if y > 0) / len(_m5) * 100) if _m5 else None)
    _nm = ' / '.join(x['code'] + ' ' + str(x['name']) + ' ' + format(x['score'], '.1f') + ' ' + CN.get(x['cls'], x['cls']) for x in _rs)
    _rows.append('<tr data-d="' + _d + '"><td data-l="日期">' + _d + '</td>'
                 + '<td data-l="组合D+1均值" class="num ' + pc(_v1) + '">' + pct(_v1) + '</td>'
                 + '<td data-l="组合5日均值" class="num ' + pc(_v5) + '">' + pct(_v5) + '</td>'
                 + '<td data-l="5日胜率" class="num">' + ((str(_w5) + '%') if _w5 is not None else '-') + '</td>'
                 + '<td data-l="选出的5只 (代码 名称 评分 形态)" class="ev">' + _nm + '</td></tr>')
_NEW = ('<section id="s1" class="sec on"><div class="card"><h2>表1 · 每个交易日选出的5只（共 ' + str(len(dates)) + ' 个交易日）'
        + '<span>红=正 绿=负</span></h2><div class="bd"><div class="tw"><table class="resp"><thead><tr>'
        + '<th>日期</th><th>组合D+1均值</th><th>组合5日均值</th><th>5日胜率</th><th>选出的5只 (代码 名称 评分 形态)</th>'
        + '</tr></thead><tbody>' + ''.join(_rows) + '</tbody></table></div></div></div></section>')
_t2, _n = _re.subn(r'<section id="s1".*?</section>', _NEW, _t, count=1, flags=_re.S)
open(_p, 'w', encoding='utf-8').write(_t2)
print('s1 rendered as table:', _n)