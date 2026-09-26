"""Reproducible synthetic growth-data ingest, quality checks and reports.

Usage: python run_pipeline.py. All outputs are local; no live company data.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import sqlite3
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW, OUT = ROOT / "raw", ROOT / "output"
RAW.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)
SEED = 20260926
rng = random.Random(SEED)

# Collection stage: create and read a separately stored raw event extract.
# There is no production collection API behind this exercise.
source = RAW / "events_synthetic.csv"
if not source.exists():
    with source.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["event_id", "event_date", "user_id", "channel", "is_order", "gmv_cny"])
        event_id = 1
        start = date(2026, 6, 1)
        for day in range(90):
            current = start + timedelta(days=day)
            active = rng.sample(range(1, 301), rng.randrange(50, 91))
            for user in active:
                channel = rng.choice(["Search", "Social", "Direct"])
                order = int(rng.random() < {"Search": .09, "Social": .055, "Direct": .075}[channel])
                amount = round(rng.uniform(45, 180), 2) if order else 0.0
                writer.writerow([event_id, current.isoformat(), user, channel, order, amount])
                event_id += 1
        # An intentional duplicate to show rejection and an audit trail.
        writer.writerow([1, start.isoformat(), 1, "Search", 0, 0.0])

df = pd.read_csv(source, dtype={"event_id":"int64", "event_date":"string", "user_id":"int64", "channel":"string", "is_order":"int64", "gmv_cny":"float64"})
issues = []
dup_mask = df.duplicated("event_id", keep="first")
for row in df.loc[dup_mask, "event_id"]:
    issues.append({"event_id":int(row), "reason":"duplicate_event_id"})
valid = df.loc[~dup_mask].copy()
bad_mask = (~valid.channel.isin(["Search", "Social", "Direct"])) | (~valid.is_order.isin([0, 1])) | (valid.gmv_cny < 0) | ((valid.is_order == 0) & (valid.gmv_cny != 0))
for row in valid.loc[bad_mask, "event_id"]:
    issues.append({"event_id":int(row), "reason":"invalid_channel_order_or_amount"})
valid = valid.loc[~bad_mask].copy()
valid["event_date"] = pd.to_datetime(valid.event_date, errors="coerce")
assert valid.event_date.notna().all()
assert valid.event_id.is_unique
assert not valid.isna().any().any()

db_path = OUT / "growth_metrics.sqlite"
with sqlite3.connect(db_path) as con:
    valid.assign(event_date=valid.event_date.dt.strftime("%Y-%m-%d")).to_sql("events", con, if_exists="replace", index=False)
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_event ON events(event_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_user_date ON events(user_id, event_date)")
    daily = pd.read_sql_query("""
        SELECT event_date, COUNT(DISTINCT user_id) AS dau,
               SUM(is_order) AS orders, ROUND(SUM(gmv_cny), 2) AS gmv_cny,
               ROUND(1.0*SUM(is_order)/COUNT(DISTINCT user_id), 4) AS conversion
        FROM events GROUP BY event_date ORDER BY event_date
    """, con)
    channel = pd.read_sql_query("""
        SELECT channel, COUNT(DISTINCT user_id) AS unique_users, COUNT(*) AS active_user_days,
               SUM(is_order) AS orders, ROUND(SUM(gmv_cny),2) AS gmv_cny
        FROM events GROUP BY channel ORDER BY gmv_cny DESC
    """, con)
    retention = pd.read_sql_query("""
        WITH base AS (SELECT DISTINCT event_date, user_id FROM events),
        cohorts AS (
           SELECT a.event_date, COUNT(*) AS base_users,
                  SUM(CASE WHEN b.user_id IS NULL THEN 0 ELSE 1 END) AS next_day_returned
           FROM base a LEFT JOIN base b ON a.user_id=b.user_id
            AND b.event_date=date(a.event_date, '+1 day')
           WHERE a.event_date < (SELECT MAX(event_date) FROM events)
           GROUP BY a.event_date
        ) SELECT event_date, base_users, next_day_returned,
                 ROUND(1.0*next_day_returned/base_users,4) AS d1_retention
          FROM cohorts ORDER BY event_date
    """, con)
    rolling = pd.read_sql_query("""
       WITH d AS (SELECT event_date, SUM(gmv_cny) AS gmv FROM events GROUP BY event_date)
       SELECT event_date, ROUND(gmv,2) AS gmv,
              ROUND(AVG(gmv) OVER (ORDER BY event_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW),2) AS gmv_7d_avg
       FROM d ORDER BY event_date
    """, con)

daily.to_csv(OUT / "daily_kpis.csv", index=False)
channel.to_csv(OUT / "channel_kpis.csv", index=False)
retention.to_csv(OUT / "d1_retention.csv", index=False)
rolling.to_csv(OUT / "gmv_7d.csv", index=False)
pd.DataFrame(issues).to_csv(OUT / "quality_issues.csv", index=False)

daily["event_date"] = pd.to_datetime(daily.event_date)
weekly = daily.assign(period=daily.event_date.dt.to_period("W").astype(str)).groupby("period",as_index=False).agg(active_user_days=("dau","sum"), orders=("orders","sum"),gmv_cny=("gmv_cny","sum"))
monthly = daily.assign(period=daily.event_date.dt.to_period("M").astype(str)).groupby("period",as_index=False).agg(active_user_days=("dau","sum"), orders=("orders","sum"),gmv_cny=("gmv_cny","sum"))
weekly.to_csv(OUT / "weekly_report.csv", index=False)
monthly.to_csv(OUT / "monthly_report.csv", index=False)

summary = {
 "source_type":"locally generated synthetic CSV; no company, platform or actual visitor data",
 "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
 "raw_rows":int(len(df)),"accepted_rows":int(len(valid)),"rejected_rows":len(issues),
 "date_count":int(len(daily)),"date_range":[daily.event_date.min().strftime("%Y-%m-%d"),daily.event_date.max().strftime("%Y-%m-%d")],
 "unique_users":int(valid.user_id.nunique()),"orders":int(valid.is_order.sum()),
 "gmv_cny":round(float(valid.gmv_cny.sum()),2),
 "mean_dau":round(float(np.mean(daily.dau.to_numpy())),2),
 "weighted_d1_retention":round(float(retention.next_day_returned.sum()/retention.base_users.sum()),4),
 "channel_rows":len(channel),"weekly_rows":len(weekly),"monthly_rows":len(monthly),
 "checks":["event_id unique","date parse","channel whitelist","binary order","nonnegative GMV","GMV zero without order"]
}
assert abs(summary["gmv_cny"]-round(float(daily.gmv_cny.sum()),2)) < .001
assert summary["orders"] == int(daily.orders.sum())
assert len(daily) == 90 and len(retention) == 89
(OUT / "summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")

def chart(series, label, stroke):
    values=np.asarray(series,dtype=float)
    low,high=float(values.min()),float(values.max())
    span=high-low or 1.0
    pts=" ".join(f"{round(i*700/(len(values)-1),1)},{round(118-(v-low)*100/span,1)}" for i,v in enumerate(values))
    return f'<figure><figcaption>{label}</figcaption><svg viewBox="0 0 700 130" role="img" aria-label="{label}"><polyline fill="none" stroke="{stroke}" stroke-width="2.8" points="{pts}" /></svg><small>第 1 天 → 第 90 天　｜　最小 {low:,.2f}　最大 {high:,.2f}</small></figure>'

dashboard=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>增长指标看板 · 项目练习</title><style>
body{{font:16px/1.6 system-ui,'Noto Sans CJK SC',sans-serif;background:#f4f7f9;color:#152331;margin:0}}main{{max-width:1100px;margin:auto;padding:28px 24px 65px}}h1{{font-size:30px;margin:0 0 9px}}.c{{color:#536578}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:30px 0}}.card,figure,table{{background:#fff;border:1px solid #d8e1e9;padding:18px}}.card strong{{display:block;font-size:28px}}.plots{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}figure{{margin:0}}figcaption{{font-weight:700}}svg{{width:100%;height:150px}}small{{color:#536578}}table{{width:100%;border-collapse:collapse;margin-top:20px;text-align:left}}th,td{{padding:9px;border-bottom:1px solid #e5ebee}}@media(max-width:700px){{.cards,.plots{{grid-template-columns:1fr 1fr}}.plots{{display:block}}figure{{margin-bottom:14px}}}}@media(max-width:480px){{.cards{{grid-template-columns:1fr}}}}
</style></head><body><main><h1>增长业务指标看板</h1><p class="c">独立练习 · 合成事件 · {summary['date_range'][0]}—{summary['date_range'][1]} · 不是企业真实运营结果</p><div class="cards"><div class="card"><span>平均 DAU</span><strong>{summary['mean_dau']}</strong></div><div class="card"><span>D1 加权留存</span><strong>{summary['weighted_d1_retention']:.1%}</strong></div><div class="card"><span>订单数</span><strong>{summary['orders']}</strong></div><div class="card"><span>GMV（元）</span><strong>{summary['gmv_cny']:,.2f}</strong></div></div><div class="plots">{chart(daily.dau,'每日 DAU','#135b78')}{chart(daily.gmv_cny,'每日 GMV','#bd663d')}{chart(retention.d1_retention,'D1 留存（前 89 天）','#346a59')}{chart(rolling.gmv_7d_avg,'GMV 七日均值','#626199')}</div><h2>渠道贡献</h2><table><thead><tr><th>渠道</th><th>活跃用户日</th><th>订单</th><th>GMV（元）</th></tr></thead><tbody>'''
for item in channel.itertuples():
    dashboard+=f'<tr><td>{item.channel}</td><td>{item.active_user_days}</td><td>{item.orders}</td><td>{item.gmv_cny:,.2f}</td></tr>'
dashboard+='''</tbody></table><p class="c">口径：DAU 为当天去重用户；订单数 / DAU 为日转化；GMV 未扣除退货与费用；D1 留存排除最后一天。按周/月报表及质量日志见下载包。</p></main></body></html>'''
(OUT / "dashboard.html").write_text(dashboard,encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
