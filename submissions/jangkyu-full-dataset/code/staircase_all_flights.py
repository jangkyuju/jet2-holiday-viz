"""Do fares jump at the 21-, 14- and 7-day advance-purchase cutoffs for ALL flights?

1. Daily lowest fare per flight (legId) per search day, from the Parquet copy.
2. Fare by days before departure across all quotes (median / mean).
3. Matched changes: the same flight compared with its check exactly one day earlier,
   so the result is not driven by which flights happen to be searched on each day.
4. The same jump test split by airline, nonstop/connecting, basic economy, origin, month.
Writes CSVs and a chart to analysis/out/.
"""
import os
import time
import duckdb

PARQUET = r"C:\Users\jujkp\.cache\kagglehub\datasets\dilwong\flightprices\versions\1\itineraries.parquet"
OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)

con = duckdb.connect(os.path.join(OUT, "work.duckdb"))
con.execute("SET memory_limit='6GB'")
con.execute(f"SET temp_directory='{os.path.dirname(PARQUET).replace(os.sep, '/')}/duckdb_tmp'")
t0 = time.time()

def step(msg):
    print(f"[{time.time() - t0:5.0f}s] {msg}", flush=True)

# 1. one row per flight per search day: its lowest fare that day
if "daily" not in con.execute("SELECT table_name FROM information_schema.tables").df()["table_name"].tolist():
    step("building daily lowest fare per flight...")
    con.execute(f"""
        CREATE TABLE daily AS
        SELECT legId, searchDate, flightDate, startingAirport AS orig, destinationAirport AS dest,
               DATE_DIFF('day', searchDate, flightDate) AS dbf,
               ANY_VALUE(isNonStop) AS nonstop,
               BOOL_AND(isBasicEconomy) AS basic,
               ANY_VALUE(STRING_SPLIT(segmentsAirlineName, '||')[1]) AS airline,
               MIN(totalFare) AS fare
        FROM read_parquet('{PARQUET}')
        GROUP BY ALL
    """)
step(f"daily rows: {con.execute('SELECT COUNT(*) FROM daily').fetchone()[0]:,}")

# 2. matched one-day changes
if "chg" not in con.execute("SELECT table_name FROM information_schema.tables").df()["table_name"].tolist():
    step("computing matched day-over-day changes...")
    con.execute("""
        CREATE TABLE chg AS
        SELECT *, fare / prev_fare - 1 AS pct FROM (
          SELECT *, LAG(fare) OVER w AS prev_fare, LAG(searchDate) OVER w AS prev_search
          FROM daily WINDOW w AS (PARTITION BY legId ORDER BY searchDate)
        ) WHERE prev_fare IS NOT NULL AND DATE_DIFF('day', prev_search, searchDate) = 1
    """)
step(f"matched one-day pairs: {con.execute('SELECT COUNT(*) FROM chg').fetchone()[0]:,}")

# 3. curve by days before departure
curve = con.execute("""
    WITH q AS (SELECT dbf, COUNT(*) AS n_flights, MEDIAN(fare) AS median_fare, AVG(fare) AS mean_fare FROM daily GROUP BY dbf),
         c AS (SELECT dbf, COUNT(*) AS n_pairs,
                      AVG(LN(fare / prev_fare)) AS mean_log_change,
                      MEDIAN(pct) AS median_pct_change,
                      100 * AVG((pct >= 0.10)::INT) AS pct_rose10,
                      100 * AVG((pct <= -0.10)::INT) AS pct_fell10,
                      100 * AVG((ABS(pct) < 0.01)::INT) AS pct_unchanged
               FROM chg GROUP BY dbf)
    SELECT q.*, c.* EXCLUDE (dbf) FROM q LEFT JOIN c USING (dbf) ORDER BY dbf DESC
""").df()
# chain index: a typical flight's fare relative to day 60, built only from matched changes
import numpy as np
curve = curve.sort_values("dbf", ascending=False).reset_index(drop=True)
curve["matched_index"] = np.exp(curve["mean_log_change"].fillna(0).where(curve["dbf"] < 60, 0).cumsum()) * 100
curve.to_csv(os.path.join(OUT, "curve_by_days_out.csv"), index=False)
step("curve done")

# 4. robustness: jump share on the days right after each cutoff vs. the rest
SPIKE = (20, 13, 6, 5)
def split(dim_sql, name, min_pairs=200_000):
    df = con.execute(f"""
        SELECT {dim_sql} AS grp, dbf, COUNT(*) AS n, 100 * AVG((pct >= 0.10)::INT) AS rose10
        FROM chg GROUP BY ALL
    """).df()
    rows = []
    for g, d in df.groupby("grp"):
        if d["n"].sum() < min_pairs:
            continue
        base = d[~d["dbf"].isin(SPIKE) & d["dbf"].between(2, 59)]
        b = np.average(base["rose10"], weights=base["n"])
        r = {"split": name, "group": g, "pairs": int(d["n"].sum()), "baseline_rose10": round(b, 1)}
        for s in (22, 21, 20, 19, 15, 14, 13, 12, 8, 7, 6, 5, 4):
            v = d.loc[d["dbf"] == s, "rose10"]
            r[f"d{s}"] = round(float(v.iloc[0]), 1) if len(v) else None
        rows.append(r)
    return rows
import pandas as pd
rob = pd.DataFrame(
    split("'all flights'", "all")
    + split("CASE WHEN nonstop THEN 'nonstop' ELSE 'connecting' END", "stops")
    + split("CASE WHEN basic THEN 'basic economy' ELSE 'regular' END", "fare class")
    + split("airline", "airline (first segment)", 1_000_000)
    + split("orig", "origin airport")
    + split("STRFTIME(flightDate, '%m')", "flight month", 1_000_000)
    + split("STRFTIME(flightDate, '%a')", "flight weekday")
)
rob.to_csv(os.path.join(OUT, "jump_robustness.csv"), index=False)
step("robustness done")

pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_rows", 200)
print("\n== Curve (every day; matched columns compare each flight with its own check one day earlier) ==")
print(curve[["dbf", "n_flights", "median_fare", "mean_fare", "matched_index", "median_pct_change", "pct_rose10", "pct_fell10", "pct_unchanged", "n_pairs"]]
      .round(2).to_string(index=False))
print("\n== Share of flights whose fare rose 10%+ overnight, by group ==")
print(rob.to_string(index=False))

# 5. chart
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
c = curve
fig, ax = plt.subplots(3, 1, figsize=(11, 11), sharex=True)
ax[0].plot(c.dbf, c.median_fare, color="#0a1f3c", lw=2, drawstyle="steps-post", label="Median fare (all quotes)")
ax[0].plot(c.dbf, c.mean_fare, color="#7d8aa2", lw=1.5, ls="--", label="Mean fare (all quotes)")
ax[0].set_ylabel("USD"); ax[0].legend(frameon=False); ax[0].set_title("All flights: lowest daily fare by days before departure")
ax[1].plot(c.dbf, c.matched_index, color="#c8102e", lw=2, drawstyle="steps-post")
ax[1].axhline(100, color="#c0cad8", lw=1)
ax[1].set_ylabel("Index (day 60 = 100)"); ax[1].set_title("Same flights tracked day to day (chain index of matched changes)")
w = 0.4
ax[2].bar(c.dbf + w / 2, c.pct_rose10, width=w, color="#d0263c", label="Rose 10%+ since previous day")
ax[2].bar(c.dbf - w / 2, c.pct_fell10, width=w, color="#2a6fd0", label="Fell 10%+")
ax[2].set_ylabel("% of matched flights"); ax[2].legend(frameon=False); ax[2].set_title("Overnight jumps and drops")
for a in ax:
    for d in (21, 14, 7):
        a.axvline(d, color="#6f7c90", ls=":", lw=1)
    a.spines[["top", "right"]].set_visible(False)
ax[2].set_xlim(61, 0); ax[2].set_xlabel("Days before departure")
for d in (21, 14, 7):
    ax[0].text(d, ax[0].get_ylim()[1], f"{d}-day", ha="center", va="bottom", fontsize=9, color="#6f7c90")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "staircase_all_flights.png"), dpi=130)
step("chart saved")
