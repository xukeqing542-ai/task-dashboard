"""Reproducible portfolio case: synthetic cross-border growth and listing checks."""
import csv
import json
import math
import random
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
rng = random.Random(20260926)

visitors = []
for i in range(4000):
    group = "B" if i % 2 else "A"  # deterministic random assignment below
    channel = "Search" if rng.random() < 0.55 else "Social"
    base = 0.052 if channel == "Search" else 0.038
    propensity = base + (0.008 if group == "B" else 0)
    purchase = int(rng.random() < propensity)
    visitors.append((i + 1, group, channel, purchase, 49.9 * purchase))
rng.shuffle(visitors)

with (OUT / "visitors_synthetic.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["visitor_id", "randomized_variant", "channel", "purchase", "revenue_usd"])
    w.writerows(visitors)

db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE visitors(visitor_id INTEGER, variant TEXT, channel TEXT, purchase INTEGER, revenue REAL)")
db.executemany("INSERT INTO visitors VALUES (?,?,?,?,?)", visitors)
rows = db.execute("SELECT variant,channel,count(*),sum(purchase),round(sum(revenue),2) FROM visitors GROUP BY variant,channel ORDER BY variant,channel").fetchall()
with (OUT / "funnel_by_channel.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["variant", "channel", "visitors", "orders", "revenue_usd"])
    w.writerows(rows)

agg = {v: (sum(r[3] for r in visitors if r[1] == v), 2000) for v in "AB"}
p_a, p_b = (agg[v][0] / 2000 for v in "AB")
diff = p_b - p_a
se = math.sqrt(p_a * (1-p_a) / 2000 + p_b * (1-p_b) / 2000)
ci = [diff - 1.96 * se, diff + 1.96 * se]

products = []
for i in range(1, 13):
    price = 25 + i * 3
    cost = 12 + i * 1.8
    fee = round(price * 0.15, 2)
    title = "Brake Pad Set" if i % 3 else "Pad"
    fitment = "Sedan 2016-2020" if i % 4 else ""
    flag = []
    if len(title) < 10: flag.append("short_title")
    if not fitment: flag.append("missing_fitment")
    baseline = round(price - cost - fee - 4.5, 2)
    promo = round(price * 0.95 - cost - fee - 4.5, 2)
    products.append([f"S{i:02}", title, fitment, price, cost, fee, baseline, promo, ";".join(flag)])
with (OUT / "listing_audit_synthetic.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["sku", "title_demo", "fitment_demo", "price", "cost", "platform_fee", "unit_margin_base", "unit_margin_5pct_off", "review_flag"])
    w.writerows(products)

summary = {
    "dataset": "synthetic portfolio case; not a live Amazon account or real users",
    "visitors": len(visitors),
    "split": {v: {"visitors": n, "orders": orders, "conversion": round(orders/n, 4)} for v,(orders,n) in agg.items()},
    "conversion_diff_percentage_points": round(100 * diff, 2),
    "approx_95pct_confidence_interval_percentage_points": [round(100*x, 2) for x in ci],
    "statistically_conclusive_at_5pct": not (ci[0] <= 0 <= ci[1]),
    "listing_skus": len(products),
    "listing_records_flagged": sum(bool(p[-1]) for p in products),
    "assumptions": "constant $4.50 fulfillment cost; platform fee fixed at original price; no tax, returns, inventory or ad attribution"
}
assert sum(x[3] for x in rows) == sum(x[3] for x in visitors)
assert len({v[0] for v in visitors}) == 4000
assert all(p[7] <= p[6] for p in products)
(OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
