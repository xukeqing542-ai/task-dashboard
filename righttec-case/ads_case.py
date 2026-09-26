"""Deterministic *synthetic* advertising scenario, not a Meta account export."""
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

root = Path(__file__).resolve().parent
out = root / "ads_output"
out.mkdir(exist_ok=True)
rng = random.Random(20260926)
audiences = [
    ("kitchen_efficiency", 0.020, 0.055),
    ("home_organization", 0.024, 0.044),
    ("outdoor_living", 0.017, 0.051),
]
creatives = [("short_video_storyboard", 1.08), ("static_comparison", 0.92)]
rows = []
for day in range(1, 8):
    for audience, click_prob, order_prob in audiences:
        for creative, adjustment in creatives:
            impressions = 1800 + rng.randrange(300)
            clicks = sum(rng.random() < click_prob * adjustment for _ in range(impressions))
            orders = sum(rng.random() < order_prob * adjustment for _ in range(clicks))
            spend = round(clicks * (0.68 + 0.06 * (day % 3)), 2)
            revenue = orders * 45
            rows.append([day, audience, creative, impressions, clicks, orders, spend, revenue])

def csv_write(path, header, data):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)

csv_write(out / "ads_daily_synthetic.csv",
          ["day", "audience", "creative", "impressions", "clicks", "orders", "spend_usd", "revenue_usd"], rows)

by_audience = defaultdict(lambda: [0, 0, 0, 0., 0.])
by_creative = defaultdict(lambda: [0, 0, 0, 0., 0.])
for _, audience, creative, impressions, clicks, orders, spend, revenue in rows:
    for bucket in (by_audience[audience], by_creative[creative]):
        bucket[0] += impressions
        bucket[1] += clicks
        bucket[2] += orders
        bucket[3] += spend
        bucket[4] += revenue

def summary(group):
    result = []
    for name, (impr, clicks, orders, spend, revenue) in sorted(group.items()):
        result.append([name, impr, clicks, orders, round(spend, 2), round(revenue, 2),
                       round(100 * clicks / impr, 2), round(100 * orders / clicks, 2),
                       round(spend / clicks, 2), round(spend / orders, 2),
                       round(revenue / spend, 2)])
    return result

header = ["segment", "impressions", "clicks", "orders", "spend_usd", "revenue_usd",
          "CTR_pct", "CVR_pct", "CPC_usd", "CPA_usd", "ROAS"]
aud = summary(by_audience)
creative = summary(by_creative)
csv_write(out / "audience_report.csv", header, aud)
csv_write(out / "creative_report.csv", header, creative)
totals = [sum(row[i] for row in rows) for i in (3, 4, 5, 6, 7)]
break_even_roas = 1 / 0.40  # example contribution margin *before advertising*; assumes zero fixed cost
review = [
    {"audience": r[0], "ROAS": r[-1], "suggestion":
     "review/hold, check attribution and creative" if r[-1] < break_even_roas else
     "eligible for small controlled retest; no claim of validated uplift"}
    for r in aud
]
result = {
    "scope": "synthetic scenario; not actual Facebook advertising, spend, impressions or sales",
    "cells": len(rows), "audiences": len(aud), "creative_variants": len(creative),
    "impressions": totals[0], "clicks": totals[1], "orders": totals[2],
    "spend_usd": round(totals[3], 2), "revenue_usd": totals[4],
    "CTR_pct": round(100 * totals[1] / totals[0], 2),
    "CVR_pct": round(100 * totals[2] / totals[1], 2),
    "ROAS": round(totals[4] / totals[3], 2),
    "break_even_roas_assuming_40pct_margin": break_even_roas,
    "review": review,
    "limitations": "All observations generated locally from chosen rates; no causal lift, account access, attribution, platform fees, refunds or external benchmark."
}
assert len(rows) == 42 and sum(x[3] for x in rows) == totals[0]
assert all(r[4] >= 0 for r in rows)
(out / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
