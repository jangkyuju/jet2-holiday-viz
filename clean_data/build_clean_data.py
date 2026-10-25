"""Collect the cleaned data behind each visualization into clean_data/<viz>/.

Run from the repository root:  python clean_data/build_clean_data.py
Inputs are the analysis outputs already in submissions/ (see clean_data/README.md for how each was made).
"""
import json
import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUB = os.path.join(ROOT, "submissions")
OUT = os.path.join(ROOT, "clean_data")
FD = os.path.join(SUB, "jangkyu-full-dataset", "data")


def write(df, folder, name):
    d = os.path.join(OUT, folder)
    os.makedirs(d, exist_ok=True)
    df.to_csv(os.path.join(d, name), index=False)
    print(f"{folder}/{name}: {len(df):,} rows")


# ---------- AG01 destination map (Arrington Goss) ----------
ag = pd.read_csv(os.path.join(SUB, "Arrington_Visualizations", "atl_airport_fares.csv"))
ag = ag.rename(columns={"starting_airport": "origin", "destination_airport": "destination", "itinerary_count": "quotes"})
write(ag[["origin", "destination", "destination_state", "quotes", "avg_fare", "min_fare"]].sort_values("avg_fare"),
      "AG01_destination_map", "atl_destination_fares.csv")

# ---------- CZ-01 price diary (Cynthia Zhou) ----------
cz = json.load(open(os.path.join(SUB, "cynthia-cz01-cz03", "website_data.json")))
CLS = {"r": "rose_10pct_plus", "f": "fell_10pct_plus", ".": "barely_moved", " ": "no_previous_check", "-": "not_checked"}
rows = []
for route, flights in cz["SITE_DIARY"].items():
    if not route.startswith("ATL-"):
        continue
    for i, fl in enumerate(flights, 1):
        for j, (fare, c) in enumerate(zip(fl["f"], fl["c"])):
            rows.append({"route": route, "flight": i, "airline": fl["a"], "nonstop": fl["ns"],
                         "days_out": 60 - j, "lowest_fare": fare, "change_vs_previous_check": CLS[c]})
write(pd.DataFrame(rows), "CZ01_price_diary", "diary_labor_day_atl.csv")
sh = pd.read_csv(os.path.join(FD, "cz_c3b_diary_shares.csv")).iloc[[0]]
coh = pd.read_csv(os.path.join(FD, "cz_c3_cohort_size.csv"))["flights"].sum()
write(pd.DataFrame([{"flights": int(coh), "daily_checks": int(sh.checks.iloc[0]), "pct_rose_10pct_plus": sh.pct_rose10.iloc[0],
                     "pct_fell_10pct_plus": sh.pct_fell10.iloc[0], "pct_barely_moved": sh.pct_barely_moved.iloc[0]}]),
      "CZ01_price_diary", "daily_change_shares.csv")

# ---------- CZ-03 staircase (Cynthia Zhou; all flights) ----------
cv = pd.read_csv(os.path.join(FD, "curve_by_days_out.csv")).rename(columns={
    "dbf": "days_out", "n_flights": "quotes", "matched_index": "fare_index_day60_100", "n_pairs": "same_flight_pairs",
    "pct_rose10": "pct_rose_10pct_plus", "pct_fell10": "pct_fell_10pct_plus", "pct_unchanged": "pct_unchanged"})
write(cv[["days_out", "quotes", "median_fare", "mean_fare", "fare_index_day60_100", "same_flight_pairs",
          "pct_rose_10pct_plus", "pct_fell_10pct_plus", "pct_unchanged"]].round(3), "CZ03_staircase", "fare_by_days_out.csv")

# ---------- JK3 route heatmap (Jangkyu Ju) ----------
jr = pd.read_csv(os.path.join(SUB, "jangkyu-jk3", "data", "jk3_routes.csv"))
jr = jr.rename(columns={"low_day": "cheapest_days_out", "pairs": "same_flight_pairs",
                        **{c: f"pct_change_{c[1:].replace('_', '_to_')}d" for c in jr.columns if c.startswith("w") and c.count("_") == 1}})
keep = ["orig", "dest", "same_flight_pairs", "cheapest_days_out"] + [c for c in jr.columns if c.startswith("pct_change_")] + ["nonstop", "distance", "median_fare"]
write(jr[keep].rename(columns={"orig": "origin", "dest": "destination", "nonstop": "share_nonstop"}), "JK3_route_heatmap", "route_windows.csv")
jw = json.load(open(os.path.join(SUB, "jangkyu-jk3", "data", "website_data.json")))
rows = [{"origin": k[:3], "destination": k[4:], "days_out": 60 - i, "fare_index_day60_100": v["idx"][i], "avg_fare": v["mean"][i]}
        for k, v in jw["routes"].items() for i in range(60)]
write(pd.DataFrame(rows), "JK3_route_heatmap", "route_index_by_day.csv")

# ---------- SS5 fare bands (Sagarika Srinivasan's method, all flights) ----------
SD = os.path.join(SUB, "jangkyu-ss5-full", "data")
parts = []
for name, label in [("all_flights", "All flights"), ("july_4", "July 4"), ("labor_day", "Labor Day"), ("non-holiday", "Non-holiday")]:
    r = pd.read_csv(os.path.join(SD, f"ribbon_widths_{name}.csv")); r.insert(0, "period", label); parts.append(r)
write(pd.concat(parts).rename(columns={"from_cp": "from_days_out", "to_cp": "to_days_out", "count": "flights"}), "SS5_fare_bands", "ribbon_counts.csv")
ss = json.load(open(os.path.join(SD, "ss5_summary.json")))
rows = []
for period, v in ss["periods"].items():
    for cp in (60, 30, 21, 14, 7):
        rows.append({"period": period, "flights": v["flights"], "days_out": cp, "pct_floor": v["shares"][f"floor_{cp}"],
                     "pct_middle": v["shares"][f"middle_{cp}"], "pct_jumped": v["shares"][f"jumped_{cp}"]})
write(pd.DataFrame(rows), "SS5_fare_bands", "checkpoint_shares.csv")

# ---------- YH-02 nonstop vs. connecting (Yuhan Hu's method, all flight dates) ----------
q1 = pd.read_csv(os.path.join(FD, "q7_1_pooled.csv")).query("period == 'All flights'").iloc[0]
q2 = pd.read_csv(os.path.join(FD, "q7_2_same_route.csv")).query("period == 'All flights' and orig == 'ATL'")
rows = [{"scope": "all routes (pooled)", "origin": "", "destination": "", "nonstop_median_fare": q1.median_fare_Nonstop,
         "connecting_median_fare": q1.median_fare_Connecting, "nonstop_quotes": int(q1.quotes_Nonstop), "connecting_quotes": int(q1.quotes_Connecting)}]
rows += [{"scope": "same route", "origin": r.orig, "destination": r.dest, "nonstop_median_fare": r.ns, "connecting_median_fare": r.cn,
          "nonstop_quotes": int(r.n_ns), "connecting_quotes": int(r.n_cn)} for r in q2.sort_values("dest").itertuples()]
write(pd.DataFrame(rows), "YH02_nonstop", "nonstop_vs_connecting.csv")
