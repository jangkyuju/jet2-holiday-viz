"""Redo of Yuhan's Q7 (nonstop vs. connecting) on the full dataset.

Three levels, each a stricter comparison than the last:
  1. Pooled medians over every quote (Yuhan's method, now for all flight dates too).
  2. Same route: median nonstop vs. median connecting within each origin-destination pair.
  3. Same choice: same route, same flight date, same search day. The cheapest nonstop vs.
     the cheapest connecting option a traveler saw side by side.
"""
from redo_common import connect, by_period, save, step, PERIOD_SQL

con = connect()

step("1. pooled medians")
pooled = by_period(con, """
    CASE WHEN nonstop THEN 'Nonstop' ELSE 'Connecting' END AS type,
    COUNT(*) AS quotes, MEDIAN(fare) AS median_fare, ROUND(AVG(fare), 2) AS mean_fare""", "type")
pooled = pooled.pivot_table(index="period", columns="type", values=["median_fare", "mean_fare", "quotes"]).round(2)
pooled.columns = [f"{a}_{b}" for a, b in pooled.columns]
pooled["nonstop_minus_connecting"] = (pooled["median_fare_Nonstop"] - pooled["median_fare_Connecting"]).round(2)
pooled["nonstop_pct"] = (100 * (pooled["median_fare_Nonstop"] / pooled["median_fare_Connecting"] - 1)).round(1)
pooled = save(pooled.reset_index(), "q7_1_pooled.csv")
print(pooled.to_string(index=False))

step("2. same route")
route = by_period(con, """orig, dest,
    MEDIAN(fare) FILTER (WHERE nonstop) AS ns, MEDIAN(fare) FILTER (WHERE NOT nonstop) AS cn,
    COUNT(*) FILTER (WHERE nonstop) AS n_ns, COUNT(*) FILTER (WHERE NOT nonstop) AS n_cn""", "orig, dest")
route = route.dropna(subset=["ns", "cn"])
route["pct"] = 100 * (route["ns"] / route["cn"] - 1)
save(route, "q7_2_same_route.csv")
s2 = route.groupby("period").agg(routes=("pct", "size"), nonstop_cheaper=("pct", lambda p: int((p < 0).sum())),
                                 median_pct=("pct", "median")).reset_index()
s2["share_nonstop_cheaper"] = (100 * s2["nonstop_cheaper"] / s2["routes"]).round(1)
print(s2.round(1).to_string(index=False))

step("3. same choice (route x flight date x search day)")
choice = con.execute(f"""
    WITH c AS (
      SELECT orig, dest, flightDate, searchDate, dbf, {PERIOD_SQL} AS period,
             MIN(fare) FILTER (WHERE nonstop) AS ns, MIN(fare) FILTER (WHERE NOT nonstop) AS cn
      FROM q GROUP BY ALL)
    SELECT COALESCE(period, 'other dates') AS period, COUNT(*) AS choices,
           ROUND(100 * AVG((ns < cn)::INT), 1) AS pct_nonstop_cheaper,
           ROUND(100 * AVG((ns = cn)::INT), 1) AS pct_tie,
           ROUND(MEDIAN(100 * (ns / cn - 1)), 1) AS median_pct_diff,
           ROUND(MEDIAN(ns - cn), 2) AS median_usd_diff
    FROM c WHERE ns IS NOT NULL AND cn IS NOT NULL
    GROUP BY ROLLUP (period) ORDER BY period NULLS FIRST""").df()
choice["period"] = choice["period"].fillna("All flights")
save(choice, "q7_3_same_choice.csv")
print(choice.to_string(index=False))

step("3b. same choice by days before departure (all flights)")
by_dbf = con.execute("""
    WITH c AS (SELECT orig, dest, flightDate, searchDate, dbf,
                      MIN(fare) FILTER (WHERE nonstop) AS ns, MIN(fare) FILTER (WHERE NOT nonstop) AS cn
               FROM q GROUP BY ALL)
    SELECT dbf, COUNT(*) AS choices, ROUND(100 * AVG((ns < cn)::INT), 1) AS pct_nonstop_cheaper,
           ROUND(MEDIAN(100 * (ns / cn - 1)), 1) AS median_pct_diff
    FROM c WHERE ns IS NOT NULL AND cn IS NOT NULL GROUP BY dbf ORDER BY dbf DESC""").df()
save(by_dbf, "q7_3b_same_choice_by_days_out.csv")
print(by_dbf.iloc[[0, 9, 19, 29, 39, 45, 50, 55, 58, 59]].to_string(index=False))
step("done")
