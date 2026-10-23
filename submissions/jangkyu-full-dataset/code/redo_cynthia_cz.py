"""Redo of Cynthia's CZ-01 (price diary) and CZ-03 (staircase) on the full dataset.

Populations, each the largest set the question allows:
  C1  every quote (82.1M)                         -> fare by days out, seat squeeze
  C2  every same-flight one-day pair (64.5M)      -> overnight rises/drops, chain index
  C3  every flight observed on EVERY day it could  -> a fixed cohort followed day by day:
      have been searched (complete record)           staircase without mix effects,
                                                      diary shares, when the low point falls,
                                                      odds of waiting
"""
import numpy as np
import pandas as pd
from redo_common import connect, save, step, PERIOD_SQL, PERIODS

con = connect()
P = PERIOD_SQL

def stack(sql_body, group="dbf", src="q", where="TRUE"):
    """sql_body uses columns of src; returns all flights + each window."""
    return con.execute(f"""
        SELECT 'All flights' AS period, {group}, {sql_body} FROM {src} WHERE {where} GROUP BY {group}
        UNION ALL
        SELECT period, {group}, {sql_body} FROM {src} WHERE period IS NOT NULL AND {where} GROUP BY period, {group}
    """).df()

# ---------- C1: every quote ----------
step("C1 staircase over every quote + seat squeeze")
c1 = stack("""COUNT(*) AS quotes, MEDIAN(fare) AS median_fare, QUANTILE_CONT(fare, 0.25) AS p25, QUANTILE_CONT(fare, 0.75) AS p75,
              ROUND(AVG(fare), 2) AS mean_fare,
              ROUND(100 * AVG((seats BETWEEN 1 AND 3)::INT) FILTER (WHERE seats IS NOT NULL), 2) AS pct_1to3_seats""")
c1 = save(c1.sort_values(["period", "dbf"], ascending=[True, False]), "cz_c1_every_quote.csv")

# ---------- C2: matched one-day pairs ----------
step("C2 matched one-day changes")
con.execute(f"CREATE OR REPLACE TEMP VIEW chg_p AS SELECT *, {P} AS period FROM chg")
c2 = stack("""COUNT(*) AS pairs, ROUND(100 * AVG((pct >= 0.10)::INT), 2) AS pct_rose10,
              ROUND(100 * AVG((pct <= -0.10)::INT), 2) AS pct_fell10, ROUND(100 * AVG((ABS(pct) < 0.01)::INT), 2) AS pct_unchanged,
              AVG(LN(fare / prev_fare)) AS mean_log_change""", src="chg_p")
c2 = c2.sort_values(["period", "dbf"], ascending=[True, False])
c2["index"] = c2.groupby("period")["mean_log_change"].transform(lambda s: 100 * np.exp(s.fillna(0).cumsum()))
c2 = save(c2, "cz_c2_matched_changes.csv")

# ---------- C3: complete-record cohort ----------
step("C3 building the complete-record cohort")
con.execute("""
    CREATE OR REPLACE TABLE complete AS
    WITH cov AS (
      SELECT legId, MIN(flightDate) AS fd, COUNT(DISTINCT dbf) AS k,
             LEAST(60, DATE_DIFF('day', DATE '2022-04-16', MIN(flightDate))) AS max_d,
             GREATEST(1, DATE_DIFF('day', DATE '2022-10-05', MIN(flightDate))) AS min_d
      FROM daily WHERE dbf BETWEEN 1 AND 60 GROUP BY legId)
    SELECT legId, max_d FROM cov WHERE min_d = 1 AND max_d >= 30 AND k = max_d - min_d + 1""")
con.execute(f"""CREATE OR REPLACE TEMP VIEW panel AS
    SELECT d.*, c.max_d, {P} AS period FROM daily d JOIN complete c USING (legId) WHERE d.dbf BETWEEN 1 AND 60""")
cohort = con.execute(f"""SELECT COALESCE({P}, 'other dates') AS period, max_d = 60 AS full_60, COUNT(*) AS flights
                         FROM complete JOIN (SELECT DISTINCT legId, flightDate FROM daily) USING (legId) GROUP BY ALL ORDER BY ALL""").df()
save(cohort, "cz_c3_cohort_size.csv")
print(cohort.to_string(index=False))

step("C3a cohort staircase (same flights every day, no mix effect)")
c3a = stack("""COUNT(*) AS flights, MEDIAN(fare) AS median_fare, ROUND(AVG(fare), 2) AS mean_fare""", src="panel")
c3a = save(c3a.sort_values(["period", "dbf"], ascending=[True, False]), "cz_c3a_cohort_staircase.csv")

step("C3b diary shares and when each flight's low point falls")
con.execute("""CREATE OR REPLACE TEMP VIEW pchg AS
    SELECT *, fare / LAG(fare) OVER (PARTITION BY legId ORDER BY dbf DESC) - 1 AS pct FROM panel""")
diary = con.execute("""
    SELECT COALESCE(period, 'other dates') AS period, COUNT(*) AS checks,
           ROUND(100 * AVG((pct >= 0.10)::INT), 1) AS pct_rose10, ROUND(100 * AVG((pct <= -0.10)::INT), 1) AS pct_fell10,
           ROUND(100 * AVG((ABS(pct) < 0.10)::INT), 1) AS pct_barely_moved
    FROM pchg WHERE pct IS NOT NULL GROUP BY ROLLUP (period)""").df()
diary["period"] = diary["period"].fillna("All flights")
save(diary, "cz_c3b_diary_shares.csv")
print(diary.to_string(index=False))

lows = con.execute("""
    WITH m AS (SELECT legId, period, max_d, MIN(fare) AS lo FROM panel GROUP BY ALL),
         first_low AS (SELECT p.legId, MAX(p.dbf) AS low_day FROM panel p JOIN m USING (legId) WHERE p.fare = m.lo GROUP BY p.legId)
    SELECT COALESCE(m.period, 'other dates') AS period, m.max_d = 60 AS full_60, f.low_day FROM m JOIN first_low f USING (legId)""").df()
bins = [0, 5, 13, 20, 30, 45, 60]
labels = ["1-5", "6-13", "14-20", "21-30", "31-45", "46-60"]
lows["window"] = pd.cut(lows["low_day"], bins=bins, labels=labels)
low_tab = pd.concat([lows.assign(period="All flights"), lows]).groupby(["period", "window"], observed=False).size().unstack(fill_value=0)
low_pct = (100 * low_tab.div(low_tab.sum(axis=1), axis=0)).round(1)
low_pct["flights"] = low_tab.sum(axis=1)
save(low_pct.reset_index(), "cz_c3b_low_point_timing.csv")
print("\nWhere each flight's lowest fare first appeared (days out, % of flights):")
print(low_pct.to_string())
full = lows[lows.full_60]
save(full.groupby("low_day").size().rename("flights").reset_index(), "cz_c3b_low_day_hist_full60.csv")

step("C3c odds of waiting")
odds = con.execute("""
    WITH f AS (SELECT legId, period, dbf, fare, MIN(fare) OVER (PARTITION BY legId ORDER BY dbf ASC
                                                 ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS later_min
               FROM panel)
    SELECT 'All flights' AS period, dbf, COUNT(*) AS flights,
           ROUND(100 * AVG((later_min < fare)::INT), 1) AS pct_cheaper_later,
           ROUND(100 * AVG((later_min < 0.9 * fare)::INT), 1) AS pct_10pct_cheaper_later
    FROM f WHERE dbf > 1 GROUP BY dbf ORDER BY dbf DESC""").df()
save(odds, "cz_c3c_cheaper_later.csv")
wait = con.execute("""
    WITH w AS (SELECT legId, dbf, fare FROM panel)
    SELECT a.dbf AS buy_at, b.dbf AS wait_until, COUNT(*) AS flights,
           ROUND(100 * AVG((b.fare < a.fare)::INT), 1) AS pct_cheaper, ROUND(100 * AVG((b.fare > a.fare)::INT), 1) AS pct_pricier,
           ROUND(100 * AVG((b.fare = a.fare)::INT), 1) AS pct_same, ROUND(MEDIAN(100 * (b.fare / a.fare - 1)), 1) AS median_pct_change,
           ROUND(AVG(100 * (b.fare / a.fare - 1)), 1) AS mean_pct_change
    FROM w a JOIN w b ON a.legId = b.legId AND b.dbf IN (21, 14, 7, 1) AND a.dbf IN (44, 30, 22, 15, 8) AND b.dbf < a.dbf
    GROUP BY ALL ORDER BY buy_at DESC, wait_until DESC""").df()
save(wait, "cz_c3c_wait_outcomes.csv")
print(wait.to_string(index=False))

# ---------- print key tables ----------
def show(df, cols, title, days=(60, 44, 30, 22, 21, 20, 15, 14, 13, 8, 7, 6, 5, 2, 1)):
    print(f"\n== {title} ==")
    for p in PERIODS:
        d = df[(df.period == p) & df.dbf.isin(days)][["dbf"] + cols]
        if len(d):
            print(f"-- {p}"); print(d.to_string(index=False))
show(c1, ["quotes", "median_fare", "mean_fare", "pct_1to3_seats"], "C1 every quote")
show(c2, ["pairs", "pct_rose10", "pct_fell10", "pct_unchanged", "index"], "C2 matched one-day changes")
show(c3a, ["flights", "median_fare", "mean_fare"], "C3a complete-record cohort")
print(odds.iloc[[0, 15, 22, 29, 37, 38, 39, 45, 46, 47, 52, 53, 54, 55, 57, 58]].to_string(index=False))

# ---------- chart ----------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
col = {"All flights": "#0a1f3c", "Memorial Day": "#2a6fd0", "July 4": "#c8102e", "Labor Day": "#1baf7a", "Non-holiday": "#a3adbd"}
fig, ax = plt.subplots(2, 2, figsize=(14, 9))
for p in PERIODS:
    d = c2[c2.period == p]; ax[0, 0].plot(d.dbf, d["index"], drawstyle="steps-post", color=col[p], lw=2 if p == "All flights" else 1.4, label=p)
    d = c2[c2.period == p]; ax[0, 1].plot(d.dbf, d.pct_rose10, color=col[p], lw=2 if p == "All flights" else 1.2, label=p)
    d = c3a[c3a.period == p]; ax[1, 0].plot(d.dbf, d.median_fare, drawstyle="steps-post", color=col[p], lw=2 if p == "All flights" else 1.4, label=p)
    d = c1[c1.period == p]; ax[1, 1].plot(d.dbf, d.pct_1to3_seats, color=col[p], lw=2 if p == "All flights" else 1.2, label=p)
ax[0, 0].set_title("Matched changes: fare index (start of record = 100)")
ax[0, 1].set_title("% of flights whose fare rose 10%+ overnight")
ax[1, 0].set_title("Complete-record cohort: median fare (same flights every day)")
ax[1, 1].set_title("% of quotes with only 1-3 seats left")
for a in ax.flat:
    for d in (21, 14, 7):
        a.axvline(d, color="#6f7c90", ls=":", lw=1)
    a.set_xlim(61, 0); a.spines[["top", "right"]].set_visible(False); a.set_xlabel("Days before departure")
ax[0, 0].legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig(f"{__import__('redo_common').OUT}/cz_redo.png", dpi=120)
step("done")
