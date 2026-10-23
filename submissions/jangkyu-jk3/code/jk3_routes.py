"""JK3: does every route follow the staircase, and does each route bottom out at a different time?

Population: every same-flight pair checked exactly one day apart (64.5M), split by route.
Per route: a chain index (60 days out = 100) built from mean log day-over-day changes, its
change inside cutoff-aligned windows, and the day its index is lowest. A split-half check
(odd vs. even flight dates) tests whether route differences are real or noise.
"""
import json
import os
import numpy as np
import pandas as pd
from redo_common import connect, step, PARQUET

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "jk3")
os.makedirs(OUT, exist_ok=True)
WINDOWS = [(60, 45), (45, 30), (30, 21), (21, 14), (14, 7), (7, 1)]
MIN_PAIRS, MIN_PER_DAY = 20_000, 50

con = connect()
pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_rows", 300)

step("route x day changes (all, and split by flight-date parity)")
rd = con.execute("""
    SELECT orig, dest, dbf, DAY(flightDate) % 2 AS half, COUNT(*) AS n, SUM(LN(fare / prev_fare)) AS s
    FROM chg WHERE dbf BETWEEN 1 AND 59 GROUP BY ALL""").df()
step("route x day average fare and route traits")
fares = con.execute("SELECT orig, dest, dbf, AVG(fare) AS mean_fare, COUNT(*) AS quotes FROM daily WHERE dbf BETWEEN 1 AND 60 GROUP BY ALL").df()
traits = con.execute(f"""SELECT startingAirport AS orig, destinationAirport AS dest, AVG(isNonStop::INT) AS nonstop,
                                MEDIAN(totalTravelDistance) AS distance, MEDIAN(totalFare) AS median_fare
                         FROM read_parquet('{PARQUET}') GROUP BY ALL""").df()

def curves(df):
    """mean log change per route/day -> index (60 = 100) for each route with full coverage"""
    g = df.groupby(["orig", "dest", "dbf"]).agg(n=("n", "sum"), s=("s", "sum")).reset_index()
    g["m"] = g.s / g.n
    out = {}
    for (o, d), r in g.groupby(["orig", "dest"]):
        r = r.set_index("dbf").reindex(range(59, 0, -1))
        if r.n.isna().any() or (r.n < MIN_PER_DAY).any() or r.n.sum() < MIN_PAIRS:
            continue
        idx = np.concatenate([[100.0], 100 * np.exp(r.m.cumsum().values)])  # days 60..1
        out[(o, d)] = (idx, int(r.n.sum()))
    return out

def describe(idx):
    days = np.arange(60, 0, -1)
    at = dict(zip(days, idx))
    win = [at[b] / at[a] - 1 for a, b in WINDOWS]
    low_day = int(days[np.argmin(idx)])            # first (furthest-out) day of the minimum
    return win, low_day, at

full = curves(rd)
halves = [curves(rd[rd.half == h]) for h in (0, 1)]
step(f"routes kept: {len(full)} of {rd.groupby(['orig', 'dest']).ngroups}")

rows = []
for (o, d), (idx, n) in full.items():
    win, low, at = describe(idx)
    t = traits[(traits.orig == o) & (traits.dest == d)].iloc[0]
    r = {"orig": o, "dest": d, "pairs": n, "low_day": low, "low_index": round(float(idx.min()), 2),
         "index_21": round(at[21], 2), "index_1": round(at[1], 2), "nonstop": round(float(t.nonstop), 3),
         "distance": float(t.distance) if t.distance == t.distance else None, "median_fare": float(t.median_fare)}
    for (a, b), w in zip(WINDOWS, win):
        r[f"w{a}_{b}"] = round(100 * w, 2)
    for h, H in enumerate(halves):
        if (o, d) in H:
            w2, l2, _ = describe(H[(o, d)][0])
            r[f"low_day_h{h}"] = l2
            r[f"w14_7_h{h}"], r[f"w7_1_h{h}"] = round(100 * w2[4], 2), round(100 * w2[5], 2)
    rows.append(r)
R = pd.DataFrame(rows).sort_values("low_day", ascending=False)
R.to_csv(os.path.join(OUT, "jk3_routes.csv"), index=False)

# ---------- summary ----------
wcols = [f"w{a}_{b}" for a, b in WINDOWS]
summ = {
    "routes": len(R),
    "pairs": int(R.pairs.sum()),
    "pct_rising_by_window": {c: round(100 * float((R[c] > 0).mean()), 1) for c in wcols},
    "median_change_by_window": {c: round(float(R[c].median()), 2) for c in wcols},
    "pct_low_before_21": round(100 * float((R.low_day > 21).mean()), 1),
    "low_day_quartiles": [float(q) for q in R.low_day.quantile([0, 0.25, 0.5, 0.75, 1])],
    "pct_rising_last_14": round(100 * float(((R["w14_7"] > 0) & (R["w7_1"] > 0)).mean()), 1),
    "pct_up_14_to_1": round(100 * float((R.index_1 > R.index_21).mean()), 1),
}
h = R.dropna(subset=["low_day_h0", "low_day_h1"])
summ["split_half"] = {
    "routes": len(h),
    "spearman_low_day": round(float(h.low_day_h0.corr(h.low_day_h1, method="spearman")), 3),
    "pct_low_day_within_7": round(100 * float(((h.low_day_h0 - h.low_day_h1).abs() <= 7).mean()), 1),
    "pct_both_halves_rise_7_1": round(100 * float(((h.w7_1_h0 > 0) & (h.w7_1_h1 > 0)).mean()), 1),
    "spearman_rise_7_1": round(float(h.w7_1_h0.corr(h.w7_1_h1, method="spearman")), 3),
}
summ["traits"] = {
    "spearman_low_day_vs_nonstop": round(float(R.low_day.corr(R.nonstop, method="spearman")), 3),
    "spearman_low_day_vs_distance": round(float(R.low_day.corr(R.distance, method="spearman")), 3),
    "spearman_last7_vs_nonstop": round(float(R.w7_1.corr(R.nonstop, method="spearman")), 3),
    "spearman_last7_vs_distance": round(float(R.w7_1.corr(R.distance, method="spearman")), 3),
}
bins = pd.cut(R.low_day, [0, 7, 14, 21, 30, 45, 60], labels=["1-7", "8-14", "15-21", "22-30", "31-45", "46-60"])
summ["low_day_hist"] = {str(k): int(v) for k, v in bins.value_counts().sort_index().items()}
by_origin = R.groupby("orig").agg(routes=("dest", "size"), median_low_day=("low_day", "median"), median_last7=("w7_1", "median")).reset_index()
by_origin.to_csv(os.path.join(OUT, "jk3_by_origin.csv"), index=False)
json.dump(summ, open(os.path.join(OUT, "jk3_summary.json"), "w"), indent=2)
print(json.dumps(summ, indent=2))
print(R[R.orig == "ATL"][["dest", "pairs", "low_day", "index_21", "index_1"] + wcols].to_string(index=False))
print(by_origin.to_string(index=False))

# ---------- website data ----------
fares["key"] = fares.orig + "-" + fares.dest
site = {"windows": WINDOWS, "routes": {}}
for (o, d), (idx, n) in full.items():
    k = f"{o}-{d}"
    f = fares[fares.key == k].set_index("dbf").reindex(range(60, 0, -1))["mean_fare"]
    r = R[(R.orig == o) & (R.dest == d)].iloc[0]
    site["routes"][k] = {"n": n, "low": int(r.low_day), "idx": [round(float(v), 2) for v in idx],
                         "mean": [None if v != v else round(float(v), 1) for v in f.values],
                         "win": [float(r[c]) for c in wcols]}
json.dump(site, open(os.path.join(OUT, "website_data.json"), "w"), separators=(",", ":"))
step(f"wrote {OUT}")
