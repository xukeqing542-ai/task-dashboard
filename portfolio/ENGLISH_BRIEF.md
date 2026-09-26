# Growth data exercise: a short stakeholder brief

I built a small, reproducible pipeline from a locally generated event CSV to SQLite, daily and channel metrics, an Excel workbook and a static dashboard. The 90-day dataset contains **6,203 synthetic event rows**. The validation step rejected one duplicate event; **6,202 rows** entered the analysis. I generated 90 daily summaries, 13 weekly summaries and three monthly summaries.

The sample has **449 orders** and **CNY 51,622.05 GMV**. Overall conversion is **7.24%**, defined as orders divided by active-user days. Search, Direct and Social show conversion rates of **9.26%, 6.99% and 5.43%** respectively. These differences are descriptive: neither acquisition traffic nor channel assignment was randomized. I would first confirm the channel attribution and order/refund rules with the business owner before recommending a change in channel spend.

The Excel workbook retains 90 editable daily input rows, formula-driven weekly summaries, a channel check and a linked chart. Its reconciliation value is zero for the supplied inputs. The final week contains six days, so its GMV total is not directly comparable with a full seven-day week.

For an independent synthetic A/B exercise with 4,000 visitors, 86 of 2,000 users converted in A versus 85 of 2,000 in B. The observed difference is **−0.05 percentage points**. An approximate 95% confidence interval includes zero (about −1.30 to +1.20 percentage points); the sample does not establish an improvement.

**Scope:** Both exercises use synthetic data. I have not worked with a live analytics SDK, a company data warehouse, a real advertising account or a production deployment. The event dictionary is a design proposal, not a record of company implementation.
