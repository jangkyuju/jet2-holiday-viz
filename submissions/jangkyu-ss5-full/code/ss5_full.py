"""SS5 on the full dataset, using Sagarika's definitions (submissions/Sagarika_Visualizations/make_ribbons.py).

- Checkpoints 60, 30, 21, 14, 7 days out; each flight's lowest daily fare on the day nearest each
  checkpoint, within +/-2 days (ties: the exact day first, then the earlier day out).
- Keep flights that have all five checkpoints.
- State at each checkpoint, relative to that flight's own lowest of the five:
  Floor < 5% above, Middle 5-10%, Jumped >= 10%   (pd.cut [-1, .05, .10, 99], right=False)
- Ribbons: counts of state transitions between consecutive checkpoints.
Run for all flight dates and for each of the team's holiday windows; also writes a random
sample of 1,000 flights' state paths for the site's animated dots.
"""
import json
import os
import pandas as pd
from redo_common import connect, step, PERIOD_SQL

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "ss5")
os.makedirs(OUT, exist_ok=True)
CPS = [60, 30, 21, 14, 7]

con = connect()
step("pick each flight's fare at the five checkpoints")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE cp AS
    WITH c AS (
      SELECT d.legId, d.flightDate, d.dbf, d.fare, t.cp,
             ROW_NUMBER() OVER (PARTITION BY d.legId, t.cp ORDER BY ABS(d.dbf - t.cp), d.dbf DESC) AS rn
      FROM daily d JOIN (VALUES (60), (30), (21), (14), (7)) t(cp) ON ABS(d.dbf - t.cp) <= 2)
    SELECT legId, flightDate, cp, fare FROM c WHERE rn = 1""")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE st AS
    WITH full5 AS (SELECT legId FROM cp GROUP BY legId HAVING COUNT(*) = 5),
         m AS (SELECT legId, MIN(fare) AS lo FROM cp JOIN full5 USING (legId) GROUP BY legId)
    SELECT cp.legId, ANY_VALUE(cp.flightDate) OVER (PARTITION BY cp.legId) AS flightDate, cp.cp,
           CASE WHEN fare / lo - 1 < 0.05 THEN 'Floor' WHEN fare / lo - 1 < 0.10 THEN 'Middle' ELSE 'Jumped' END AS state
    FROM cp JOIN m USING (legId)""")
con.execute(f"""
    CREATE OR REPLACE TEMP TABLE paths AS
    SELECT legId, ANY_VALUE(flightDate) AS flightDate,
           MAX(state) FILTER (WHERE cp = 60) AS s60, MAX(state) FILTER (WHERE cp = 30) AS s30, MAX(state) FILTER (WHERE cp = 21) AS s21,
           MAX(state) FILTER (WHERE cp = 14) AS s14, MAX(state) FILTER (WHERE cp = 7) AS s7
    FROM st GROUP BY legId""")
con.execute(f"CREATE OR REPLACE TEMP VIEW pp AS SELECT *, {PERIOD_SQL} AS period FROM paths")
n = con.execute("SELECT COUNT(*) FROM paths").fetchone()[0]
step(f"flights with all five checkpoints: {n:,}")

cols = ["s60", "s30", "s21", "s14", "s7"]
def ribbons(where):
    parts = []
    for a, b, ca, cb in zip(CPS, CPS[1:], cols, cols[1:]):
        t = con.execute(f"SELECT {ca} AS from_state, {cb} AS to_state, COUNT(*) AS count FROM pp WHERE {where} GROUP BY ALL").df()
        t["from_cp"], t["to_cp"] = a, b
        parts.append(t)
    return pd.concat(parts)[["from_cp", "from_state", "to_cp", "to_state", "count"]].sort_values(["from_cp", "from_state", "to_state"], ascending=[False, True, True])

periods = {"All flights": "TRUE", "Memorial Day": "period = 'Memorial Day'", "July 4": "period = 'July 4'", "Labor Day": "period = 'Labor Day'", "Non-holiday": "period = 'Non-holiday'"}
summary = {"definition": "Floor <5%, Middle 5-10%, Jumped >=10% above the flight's own lowest fare across the five checkpoints (60, 30, 21, 14, 7 days out, +/-2 days)", "periods": {}}
for name, where in periods.items():
    r = ribbons(where)
    r.to_csv(os.path.join(OUT, f"ribbon_widths_{name.replace(' ', '_').lower()}.csv"), index=False)
    shares = con.execute(f"""SELECT {', '.join(f"ROUND(100 * AVG(({c} = 'Floor')::INT), 1) AS floor_{c[1:]}, ROUND(100 * AVG(({c} = 'Middle')::INT), 1) AS middle_{c[1:]}, ROUND(100 * AVG(({c} = 'Jumped')::INT), 1) AS jumped_{c[1:]}" for c in cols)}, COUNT(*) AS flights FROM pp WHERE {where}""").df().iloc[0].to_dict()
    stay = con.execute(f"""SELECT ROUND(100 * AVG((s7 = 'Floor')::INT) FILTER (WHERE s21 = 'Floor'), 1) AS floor21_still_floor7,
                                  ROUND(100 * AVG((s7 = 'Jumped')::INT) FILTER (WHERE s21 = 'Floor'), 1) AS floor21_jumped7,
                                  ROUND(100 * AVG((s60 = 'Floor')::INT), 1) AS floor_at_60,
                                  ROUND(100 * AVG((s7 = 'Jumped')::INT), 1) AS jumped_at_7 FROM pp WHERE {where}""").df().iloc[0].to_dict()
    summary["periods"][name] = {"flights": int(shares.pop("flights")), "shares": shares, **stay}
    step(f"{name}: {summary['periods'][name]['flights']:,} flights")
json.dump(summary, open(os.path.join(OUT, "ss5_summary.json"), "w"), indent=2)
print(json.dumps(summary["periods"]["All flights"], indent=2))
print(pd.read_csv(os.path.join(OUT, "ribbon_widths_all_flights.csv")).to_string(index=False))

step("sample 1,000 flights for the animated dots")
code = {"Floor": "F", "Middle": "M", "Jumped": "J"}
sample = con.execute("SELECT s60, s30, s21, s14, s7 FROM paths USING SAMPLE reservoir(1000 ROWS) REPEATABLE (42)").df()
paths = ["".join(code[v] for v in row) for row in sample.itertuples(index=False)]
allr = pd.read_csv(os.path.join(OUT, "ribbon_widths_all_flights.csv"))
site = {"checkpoints": CPS, "flights": n, "sample": paths,
        "links": [[int(r.from_cp), code[r.from_state], int(r.to_cp), code[r.to_state], int(r["count"])] for _, r in allr.iterrows()],
        "summary": summary["periods"]["All flights"]}
json.dump(site, open(os.path.join(OUT, "website_data.json"), "w"), separators=(",", ":"))
step(f"wrote {OUT}")
