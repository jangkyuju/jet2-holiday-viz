# Cleaned data, by visualization

All files come from one source: **Expedia Flight Prices** (Kaggle, `dilwong/flightprices`),
`itineraries.csv`, 31 GB, 82,138,753 one-way fare quotes searched April 16 – October 5, 2022
for flights from 16 U.S. airports. Download: https://www.kaggle.com/datasets/dilwong/flightprices
(not included here because of its size).

## Cleaning applied to everything

1. Converted the CSV to Parquet and processed it with DuckDB (the file does not fit in memory).
2. Derived **days out** = flight date − search date (1–60), **route** = origin–destination, and a
   **travel period** tag: Memorial Day (May 26–31), July 4 (Jun 30–Jul 5), Labor Day (Sep 1–6),
   Non-holiday (Jun 9–14, Aug 11–16).
3. One fare per flight (`legId`) per search day: the lowest total fare (967 duplicate flight-day rows merged).
4. `seatsRemaining = 0` treated as missing.
5. **Same-flight changes** compare a flight only with its own fare exactly one day earlier
   (64,543,702 pairs), so results are not driven by which flights happen to be searched on each day.

## Per visualization

| Folder | Scene · author | Files | How it was made |
|---|---|---|---|
| `AG01_destination_map/` | Where to? · Arrington Goss | `atl_destination_fares.csv` (15 rows) | Flights from ATL, all dates; per destination: quotes, average and lowest total fare. |
| `CZ01_price_diary/` | Watching the fare · Cynthia Zhou | `diary_labor_day_atl.csv` (7,200 rows), `daily_change_shares.csv` | Diary: Labor Day flights from ATL, up to 8 per route (densest daily coverage first), lowest fare each day 60→1 and its change vs. the previous check (±10%). Shares: 16,182 flights observed on every day they could be searched; share of daily checks that rose 10%+, fell 10%+ or barely moved. |
| `CZ03_staircase/` | Fares jump · Cynthia Zhou (extended to all flights) | `fare_by_days_out.csv` (60 rows) | All 82.1M quotes by days out (median, mean) plus the same-flight fare index (60 days out = 100) and the share of flights rising / falling 10%+ overnight. |
| `JK3_route_heatmap/` | Every route · Jangkyu Ju | `route_windows.csv` (234 routes), `route_index_by_day.csv` | Same-flight index per route (routes with ≥20,000 pairs and ≥50 every day); change in each cutoff-aligned window (60–45, 45–30, 30–21, 21–14, 14–7, 7–1 days out); the day the route was cheapest. |
| `SS5_fare_bands/` | The bet · Sagarika Srinivasan (method), all flights | `ribbon_counts.csv`, `checkpoint_shares.csv` | 482,975 flights with a price near all five checkpoints (60, 30, 21, 14, 7 days out, ±2 days). State vs. the flight's own lowest of its five prices: Floor <5%, Middle 5–10%, Jumped ≥10%. Counts of moves between checkpoints, for all flights and each travel period (Memorial Day has no 60-day checkpoint). |
| `YH02_nonstop/` | One more check · Yuhan Hu (method), all dates | `nonstop_vs_connecting.csv` (15 rows) | Median total fare for nonstop vs. connecting over all routes, and within each route from ATL. Stricter check (same route, flight date and search day, 1.7M choices): nonstop cheaper 61.5% of the time, median −7.1%. |

`build_clean_data.py` regenerates these folders from the analysis outputs in `submissions/`;
the analysis scripts that produced those outputs are in each `submissions/*/code/` folder.
