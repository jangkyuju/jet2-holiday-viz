# Jangkyu Ju — JK3: every route, different low point, same ending

**Question (Q13, Q2):** do different routes have a different best time to book, and does the
late-booking jump hold on every route?

**Population:** every same-flight pair checked exactly one day apart (64.5M), split into 234 routes
(one route, OAK→OAK-area pair with too few comparisons, was dropped: each route needs ≥20,000 pairs and ≥50 on every day).

**Method:** per route, a chain index (60 days out = 100) from the mean log day-over-day change; its change in
cutoff-aligned windows (60–45, 45–30, 30–21, 21–14, 14–7, 7–1 days out); and the day the index is lowest.
Split-half check: the same steps on odd vs. even flight dates.

## Results

| | |
|---|---|
| Routes rising in the last week (7→1) | **99.1%** (232 of 234) |
| Routes rising in both of the last two windows | 98.3% |
| Share rising by window | 43% (60–45) · 74% · 73% · 84% (21–14) · 98% (14–7) · 99% (7–1) |
| Cheapest day across routes | 2 to 60 days out; middle half **30–57** |
| Routes cheapest before day 21 | **91.5%** (214 of 234) |
| Split-half agreement | cheapest day: Spearman 0.66, 72% within 7 days · last-week rise: Spearman 0.99, both halves rise on 99% |
| What moves the cheapest day | more nonstop → cheapest later (ρ = −0.35); longer routes → cheapest earlier (ρ = 0.24) |
| What moves the last-week jump | bigger on nonstop-heavy routes (ρ = 0.42), smaller on long routes (ρ = −0.38) |

From ATL (15 routes): cheapest day ranges from 55 (CLT) to 15 (DEN) days out; every route rises in the last week
(+13% to +47%). ATL→CLT jumps +52% between 14 and 7 days out.

## Files
- `data/jk3_routes.csv` — one row per route: window changes, cheapest day, split-half values, traits
- `data/jk3_summary.json` — the numbers above
- `data/jk3_by_origin.csv` — median cheapest day and last-week rise by origin airport
- `data/website_data.json` — per-route index and average fare by day, used by the site
- `code/jk3_routes.py` — the analysis (needs the DuckDB work file from `../jangkyu-full-dataset/code`)
