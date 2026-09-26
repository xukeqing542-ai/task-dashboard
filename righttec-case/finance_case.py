"""Deterministic cross-border management reporting rehearsal with synthetic records."""
import csv
import json
from collections import defaultdict
from pathlib import Path

root = Path(__file__).resolve().parent
out = root / "finance_output"
out.mkdir(exist_ok=True)
platforms = ["Amazon", "DTC", "TikTok"]
shops = ["Store_A", "Store_B"]
categories = ["Home", "Outdoor"]
daily = []
for day in range(1, 31):
    for p_idx, platform in enumerate(platforms):
        for s_idx, shop in enumerate(shops):
            for c_idx, category in enumerate(categories):
                units = 8 + p_idx * 3 + s_idx * 2 + c_idx + day % 6
                unit_price = 34 + c_idx * 8 + p_idx * 3
                gross = units * unit_price
                refunds = ((day + s_idx) % 7 == 0) * unit_price
                net = gross - refunds
                product_cost = round(units * unit_price * 0.48, 2)
                fees = round(net * (0.14 if platform == "Amazon" else 0.055), 2)
                ads = round(net * (0.10 if platform == "DTC" else 0.075), 2)
                contribution = round(net - product_cost - fees - ads, 2)
                daily.append([day, platform, shop, category, units, gross, refunds, net,
                              product_cost, fees, ads, contribution])

def write(name, header, rows):
    with (out / name).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)

head = ["day", "platform", "shop", "category", "units", "gross_sales", "refunds",
        "net_sales", "product_cost", "platform_fees", "ad_spend", "contribution"]
write("transaction_daily_synthetic.csv", head, daily)
reported = []
for row in daily:
    day, platform, shop, category = row[:4]
    delta = 25 if (day, platform, shop, category) in {
        (4, "Amazon", "Store_A", "Home"),
        (14, "DTC", "Store_B", "Outdoor"),
        (26, "TikTok", "Store_B", "Home")
    } else 0
    reported.append([day, platform, shop, category, row[7] + delta])
write("business_export_synthetic.csv", ["day", "platform", "shop", "category", "reported_net_sales"], reported)
exceptions = []
daily_report = defaultdict(lambda: [0, 0., 0., 0., 0.])
monthly = defaultdict(lambda: [0, 0., 0., 0., 0.])
matrix = defaultdict(lambda: [0, 0., 0., 0., 0.])
for row, source in zip(daily, reported):
    d, platform, shop, category, units, gross, refunds, net, cost, fees, ads, contribution = row
    if round(net, 2) != round(source[-1], 2):
        exceptions.append([d, platform, shop, category, source[-1], net, round(source[-1] - net, 2),
                           "review with business owner; no source overwrite"])
    for bucket in (daily_report[d], monthly[platform], matrix[(platform, shop, category)]):
        bucket[0] += units
        bucket[1] += net
        bucket[2] += refunds
        bucket[3] += ads
        bucket[4] += contribution

def rounded(values): return [values[0], *[round(x, 2) for x in values[1:]]]
write("daily_report.csv", ["day", "units", "net_sales", "refunds", "ad_spend", "contribution"],
      [[k, *rounded(v)] for k, v in sorted(daily_report.items())])
write("monthly_by_platform.csv", ["platform", "units", "net_sales", "refunds", "ad_spend", "contribution"],
      [[k, *rounded(v)] for k, v in sorted(monthly.items())])
write("shop_category_matrix.csv", ["platform", "shop", "category", "units", "net_sales", "refunds", "ad_spend", "contribution"],
      [[*k, *rounded(v)] for k, v in sorted(matrix.items())])
write("exceptions.csv", ["day", "platform", "shop", "category", "business_export_net_sales",
                          "recomputed_net_sales", "difference", "action"], exceptions)
sum_net = round(sum(r[7] for r in daily), 2)
sum_contribution = round(sum(r[11] for r in daily), 2)
result = {"scope": "synthetic management accounting case, no company systems or real transactions",
          "source_rows": len(daily), "days": len(daily_report), "platforms": len(monthly),
          "shop_category_cells": len(matrix), "exceptions": len(exceptions),
          "reported_overstatement": round(sum(r[6] for r in exceptions), 2),
          "net_sales": sum_net, "contribution": sum_contribution,
          "validation": "monthly net sales equals daily report and shop/category matrix totals",
          "limitations": "Example prices/cost rates, one month only; no actual close, tax, inventory valuation or ad attribution."}
assert len(daily) == 360 and len(daily_report) == 30 and len(matrix) == 12
assert len(exceptions) == 3 and round(sum(v[1] for v in monthly.values()), 2) == sum_net
assert round(sum(v[1] for v in matrix.values()), 2) == sum_net
(out / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
