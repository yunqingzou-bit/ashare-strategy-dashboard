# -*- coding: utf-8 -*-
"""Build the searchable A-share monitor dataset and static dashboard."""
import datetime as dt
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "bars.json")
DOCS = os.path.join(ROOT, "docs")


def mean(values):
    return sum(values) / len(values) if values else None


def ema(values, period):
    alpha = 2 / (period + 1)
    out = []
    cur = values[0]
    for value in values:
        cur = value * alpha + cur * (1 - alpha)
        out.append(cur)
    return out


def rsi(values, period=14):
    if len(values) <= period:
        return None
    gains, losses = [], []
    for a, b in zip(values[-period-1:-1], values[-period:]):
        delta = b - a
        gains.append(max(delta, 0)); losses.append(max(-delta, 0))
    gain, loss = mean(gains), mean(losses)
    return 100.0 if not loss else 100 - 100 / (1 + gain / loss)


def round_or_none(value, digits=2):
    return None if value is None or not math.isfinite(value) else round(value, digits)


def analyse(code, name, rows):
    if len(rows) < 30:
        return None
    closes = [float(r[2]) for r in rows]
    highs = [float(r[3]) for r in rows]
    lows = [float(r[4]) for r in rows]
    volumes = [float(r[5] or 0) for r in rows]
    last, prev = rows[-1], rows[-2]
    ma5, ma10, ma20 = (mean(closes[-n:]) for n in (5, 10, 20))
    e12, e26 = ema(closes, 12), ema(closes, 26)
    dif = [a-b for a, b in zip(e12, e26)]
    dea = ema(dif, 9)
    macd = (dif[-1] - dea[-1]) * 2
    prev_macd = (dif[-2] - dea[-2]) * 2
    rsi14 = rsi(closes)
    vol5 = mean(volumes[-6:-1]) or 0
    vr = volumes[-1] / vol5 if vol5 else None
    support = min(lows[-20:])
    resistance = max(highs[-20:])
    price = closes[-1]
    pct = (price / closes[-2] - 1) * 100

    score = 50
    reasons, risks = [], []
    if price > ma20: score += 12; reasons.append("收盘价位于MA20上方")
    else: score -= 12; risks.append("收盘价低于MA20")
    if ma5 > ma10 > ma20: score += 15; reasons.append("MA5、MA10、MA20呈多头排列")
    elif ma5 < ma10 < ma20: score -= 15; risks.append("短中期均线呈空头排列")
    if macd > 0 and prev_macd <= 0: score += 10; reasons.append("MACD柱由负转正")
    elif macd < 0: score -= 6; risks.append("MACD动能为负")
    if rsi14 is not None and rsi14 >= 75: score -= 8; risks.append("RSI进入偏热区")
    elif rsi14 is not None and 45 <= rsi14 <= 65: score += 5; reasons.append("RSI处于中性偏强区")
    if vr is not None and vr >= 1.5 and pct > 0: score += 8; reasons.append("上涨且成交量高于近5日均量")
    elif vr is not None and vr >= 1.5 and pct < 0: score -= 8; risks.append("下跌同时放量")
    score = max(0, min(100, score))

    if score >= 75:
        stance = "偏强持有 / 等回踩确认"
    elif score >= 60:
        stance = "持有观察 / 不追高"
    elif score >= 45:
        stance = "中性观察 / 等待方向"
    else:
        stance = "风险优先 / 反弹减仓观察"
    if price <= support * 1.015:
        stance = "临近支撑 / 严格观察破位"

    invalidation = min(support, ma20 * 0.985)
    pullback_low = max(support, ma20 * 0.99)
    pullback_high = max(pullback_low, ma20 * 1.015)
    first_target = max(price, ma5, ma10)
    second_target = max(first_target, resistance)
    breakout = resistance * 1.005
    if score >= 75:
        posture, sell_pct = "核心持有，冲高分批兑现；只在突破后回踩确认时考虑换回", [15, 20]
    elif score >= 60:
        posture, sell_pct = "保留观察仓，靠近压力分批降风险，不在压力下方追涨", [20, 25]
    elif score >= 45:
        posture, sell_pct = "等待方向，反弹优先回收现金，破位则进一步收缩仓位", [25, 25]
    else:
        posture, sell_pct = "风险优先，反弹减仓；收盘破位时执行纪律而非等待回本", [30, 30]

    return {
        "code": code, "name": name, "date": last[0], "price": round_or_none(price),
        "pct": round_or_none(pct), "open": round_or_none(float(last[1])),
        "high": round_or_none(float(last[3])), "low": round_or_none(float(last[4])),
        "amount": round_or_none(float(last[6] or 0), 0),
        "turnover": round_or_none(float(last[7]), 2) if len(last) > 7 and last[7] is not None else None,
        "ma5": round_or_none(ma5), "ma10": round_or_none(ma10), "ma20": round_or_none(ma20),
        "rsi14": round_or_none(rsi14, 1), "macd": round_or_none(macd, 3),
        "volumeRatio5": round_or_none(vr, 2), "support20": round_or_none(support),
        "resistance20": round_or_none(resistance), "score": score, "stance": stance,
        "reasons": reasons or ["暂无明确增强信号"], "risks": risks or ["未触发主要技术风险规则"],
        "wavePlan": {
            "horizon": "1—2周", "posture": posture,
            "pullbackLow": round_or_none(pullback_low), "pullbackHigh": round_or_none(pullback_high),
            "firstTarget": round_or_none(first_target), "secondTarget": round_or_none(second_target),
            "breakoutTrigger": round_or_none(breakout), "invalidation": round_or_none(invalidation),
            "firstSellPct": sell_pct[0], "secondSellPct": sell_pct[1],
        },
    }


def build_payload(source):
    stocks = []
    for code, rows in source.get("bars", {}).items():
        item = analyse(code, source.get("names", {}).get(code, code), rows)
        if item:
            stocks.append(item)
    dates = [s["date"] for s in stocks]
    provisional = source.get("provisional") or {}
    return {
        "generatedAt": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds"),
        "marketDate": max(dates) if dates else None,
        "dataMode": "盘中快照（非实时）" if provisional.get("applied") else "最近收盘数据",
        "source": "同花顺日线；盘中快照若可用则来自公开行情接口",
        "provisional": provisional,
        "ruleVersion": "technical-rules-v2-wave",
        "stocks": stocks,
    }


def main():
    os.makedirs(DOCS, exist_ok=True)
    source = json.load(open(DATA, encoding="utf-8"))
    payload = build_payload(source)
    with open(os.path.join(DOCS, "monitor-data.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print("monitor-data.json", len(payload["stocks"]), "stocks", payload["marketDate"])


if __name__ == "__main__":
    main()
