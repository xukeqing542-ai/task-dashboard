"""Offline practice: synthetic order, shipping and ERP reconciliation.

No Amazon Seller Central, enterprise ERP or customer records are accessed.
"""
import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "amazon_ops"
OUT.mkdir(parents=True, exist_ok=True)
rng = random.Random(20260926)

def write_csv(name, headers, rows):
    with (OUT / name).open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)

orders = []
shipments = []
erp = []
for i in range(1, 121):
    oid = f"DEMO-{i:04d}"
    sku = f"S{(i - 1) % 12 + 1:02d}"
    price = round(25 + ((i - 1) % 12 + 1) * 3, 2)
    qty = 1 + (i % 3 == 0)
    gross = round(price * qty, 2)
    orders.append([oid, sku, qty, gross, "paid"])
    if i <= 112:
        shipments.append([oid, f"TRACK-{i:04d}", "shipped"])
    if i <= 118:
        erp_amount = gross + (1.0 if i in {10, 20, 30, 40} else 0.0)
        erp.append([oid, round(erp_amount, 2), "posted"])

write_csv("orders_synthetic.csv", ["order_id", "sku", "qty", "paid_amount_usd", "status"], orders)
write_csv("shipments_synthetic.csv", ["order_id", "tracking_id", "ship_status"], shipments)
write_csv("erp_entries_synthetic.csv", ["order_id", "erp_amount_usd", "posting_status"], erp)

ship_map = {r[0]: r for r in shipments}
erp_map = {r[0]: r for r in erp}
audit = []
for o in orders:
    oid, sku, qty, paid, status = o
    flags = []
    if oid not in ship_map:
        flags.append("pending_fulfillment_review")
    if oid not in erp_map:
        flags.append("erp_missing")
    elif erp_map[oid][1] != paid:
        flags.append("erp_amount_mismatch")
    audit.append([oid, sku, qty, paid, oid in ship_map,
                  erp_map[oid][1] if oid in erp_map else "", ";".join(flags)])
write_csv("order_reconciliation.csv", ["order_id", "sku", "qty", "paid_amount_usd",
                                   "has_tracking", "erp_amount_usd", "review_flag"], audit)

# Listing draft records do not invent vehicle fitment: unknown fitment is held for verification.
listing_rows = []
with (ROOT / "output" / "listing_audit_synthetic.csv").open(encoding="utf-8") as f:
    for record in csv.DictReader(f):
        if not record["review_flag"]:
            continue
        fitment = record["fitment_demo"].strip()
        draft = "Brake Pad Set | Model Fitment Verification Required" if not fitment else f"Brake Pad Set | {fitment}"
        listing_rows.append([record["sku"], record["review_flag"], draft,
                             "Confirm vehicle compatibility before listing.",
                             "Check material, package contents and product images against source specifications.",
                             "hold_for_fitment_check" if not fitment else "editorial_review"])
write_csv("listing_drafts.csv", ["sku", "source_issue", "english_title_draft",
                                 "bullet_1", "bullet_2", "release_status"], listing_rows)

counts = {
    "orders": len(orders), "shipped": len(shipments),
    "pending_fulfillment_review": sum("pending_fulfillment_review" in r[-1] for r in audit),
    "erp_rows": len(erp), "erp_missing": sum("erp_missing" in r[-1] for r in audit),
    "erp_amount_mismatch": sum("erp_amount_mismatch" in r[-1] for r in audit),
    "orders_with_any_flag": sum(bool(r[-1]) for r in audit),
    "listing_drafts": len(listing_rows),
    "listing_hold_for_fitment": sum(r[-1] == "hold_for_fitment_check" for r in listing_rows),
    "paid_total_usd": round(sum(r[3] for r in orders), 2),
    "data_scope": "locally generated synthetic orders, shipping records, ERP rows and Listing drafts",
    "limitations": "No live marketplace, ERP access, stock, actual shipment, policy approval or selling results."
}
assert counts["orders"] == 120 and counts["shipped"] == 112
assert counts["erp_missing"] == 2 and counts["erp_amount_mismatch"] == 4
assert counts["listing_drafts"] == 6
(OUT / "summary.json").write_text(json.dumps(counts, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(counts, ensure_ascii=False, indent=2))
