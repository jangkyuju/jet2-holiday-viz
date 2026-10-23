"""Redo of Arrington's AG01 (where to go) on the full dataset.

Arrington: average fare from ATL to 15 destinations, all dates. Here: every origin x
destination, median and mean, for all flights and each holiday window, plus the
nearby-airport question (Q5) for New York (JFK/LGA/EWR) and the Bay Area (SFO/OAK).
"""
import pandas as pd
from redo_common import connect, save, step, PERIODS

con = connect()
con.execute("SET threads=4")
con.execute("SET preserve_insertion_order=false")

step("1. every route, all flights and each window (one window at a time to keep memory low)")
parts = []
for p in PERIODS:
    where = "TRUE" if p == "All flights" else f"period = '{p}'"
    parts.append(con.execute(f"""
        SELECT '{p}' AS period, orig, dest, COUNT(*) AS quotes,
               MEDIAN(fare) AS median_fare, ROUND(AVG(fare), 2) AS mean_fare, MIN(fare) AS min_fare,
               QUANTILE_CONT(fare, 0.25) AS p25_fare, ROUND(100 * AVG(nonstop::INT), 1) AS pct_nonstop
        FROM q WHERE {where} GROUP BY orig, dest""").df())
    step(f"   {p} done")
routes = pd.concat(parts, ignore_index=True)
save(routes, "ag01_1_routes.csv")

atl = routes[(routes.orig == "ATL") & (routes.period == "All flights")].sort_values("median_fare")
print("From ATL, all flights (compare: Arrington used the mean):")
print(atl[["dest", "quotes", "median_fare", "mean_fare", "min_fare", "pct_nonstop"]].to_string(index=False))

step("2. cheapest and priciest destination from each origin")
allf = routes[routes.period == "All flights"]
ext = allf.loc[allf.groupby("orig")["median_fare"].idxmin(), ["orig", "dest", "median_fare"]].merge(
    allf.loc[allf.groupby("orig")["median_fare"].idxmax(), ["orig", "dest", "median_fare"]], on="orig", suffixes=("_cheapest", "_priciest"))
save(ext, "ag01_2_extremes_by_origin.csv")
print(ext.to_string(index=False))

step("3. nearby airports (Q5)")
metro = {"JFK": "New York", "LGA": "New York", "EWR": "New York", "SFO": "Bay Area", "OAK": "Bay Area"}
m = routes[routes.dest.isin(metro) & ~routes.orig.isin(metro)].copy()
m["metro"] = m.dest.map(metro)
wide = m.pivot_table(index=["period", "orig", "metro"], columns="dest", values="median_fare").reset_index()
def best(row):
    cols = [c for c in ("JFK", "LGA", "EWR", "SFO", "OAK") if c in row and row[c] == row[c]]
    vals = {c: row[c] for c in cols}
    lo, hi = min(vals, key=vals.get), max(vals, key=vals.get)
    return pd.Series({"cheapest": lo, "priciest": hi, "saving_usd": round(vals[hi] - vals[lo], 2)})
wide = pd.concat([wide, wide.apply(best, axis=1)], axis=1)
save(wide, "ag01_3_nearby_airports.csv")
summ = wide.groupby(["period", "metro"]).agg(origins=("orig", "size"), median_saving=("saving_usd", "median")).reset_index()
summ["cheapest_most_often"] = wide.groupby(["period", "metro"])["cheapest"].agg(lambda s: s.value_counts().idxmax()).values
print(summ.to_string(index=False))
print(wide[wide.period == "All flights"].round(0).to_string(index=False))
step("done")
