"""Reproducible overseas game live-ops practice case, synthetic users only."""
import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)
rng = random.Random(372027)
N = 2400
rows = []
tickets = []
themes = ['purchase_issue', 'event_rules', 'login', 'localization', 'reward_delay']
for i in range(N):
    arm = 'B' if i % 2 else 'A'
    market = ['EN', 'RU', 'SEA'][i % 3]
    active_d1 = int(rng.random() < (0.405 if arm == 'A' else 0.435))
    active_d7 = int(rng.random() < (0.188 if arm == 'A' else 0.205))
    participated = int(rng.random() < (0.33 if arm == 'A' else 0.39))
    purchased = int(participated and rng.random() < (0.13 if arm == 'A' else 0.145))
    revenue = 9.99 if purchased else 0.0
    rows.append(dict(player_id=f'P{i+1:04d}',arm=arm,market=market,d1=active_d1,d7=active_d7,
                     event_join=participated,purchased=purchased,revenue_usd=revenue))
    if rng.random() < 0.095:
        theme = rng.choice(themes)
        tickets.append(dict(ticket_id=f'T{len(tickets)+1:03d}',player_id=f'P{i+1:04d}',market=market,
                            theme=theme,priority='P1' if theme in {'purchase_issue','login'} else 'P2',
                            action='escalate_cs' if theme in {'purchase_issue','login'} else 'faq_or_copy_review'))

with (OUT/'players.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
with (OUT/'feedback.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=tickets[0]);w.writeheader();w.writerows(tickets)

summary={}
for arm in ('A','B'):
    group=[r for r in rows if r['arm']==arm]
    summary[arm]={k:sum(r[k] for r in group) for k in ['d1','d7','event_join','purchased','revenue_usd']}
    summary[arm]['players']=len(group)
    for k in ['d1','d7','event_join','purchased']:
        summary[arm][k+'_rate']=round(summary[arm][k]/len(group),4)
cost_usd = {'creative':140,'localization':65,'cs':55,'paid_media':120}
total_revenue=sum(r['revenue_usd'] for r in rows)
platform_fee=round(total_revenue*.30,2)
cost_total=sum(cost_usd.values())+platform_fee
net_contribution=round(total_revenue-cost_total,2)
def diff_ci(k):
    p=[summary[a][k+'_rate'] for a in ('A','B')]
    se=math.sqrt(sum(x*(1-x)/1200 for x in p))
    return [round(p[1]-p[0],4),round(p[1]-p[0]-1.96*se,4),round(p[1]-p[0]+1.96*se,4)]
result=dict(players=N,markets=Counter(r['market'] for r in rows),arms=summary,
            d7_diff_ci95=diff_ci('d7'),event_join_diff_ci95=diff_ci('event_join'),
            feedback_count=len(tickets),feedback_by_theme=Counter(t['theme'] for t in tickets),
            p1_count=sum(t['priority']=='P1' for t in tickets),revenue_usd=round(total_revenue,2),
            cost_breakdown_usd=cost_usd,platform_fee_usd=platform_fee,
            cost_total_usd=round(cost_total,2),net_contribution_usd=net_contribution,
            contribution_margin=round(net_contribution/total_revenue,4))
assert len({r['player_id'] for r in rows})==N
assert summary['A']['players']==summary['B']['players']==1200
assert sum(result['feedback_by_theme'].values())==len(tickets)
assert abs(result['revenue_usd']-result['cost_total_usd']-net_contribution)<.01
(OUT/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
