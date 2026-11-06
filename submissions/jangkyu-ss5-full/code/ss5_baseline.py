"""SS5 variant: each flight compared with its OWN fare 60 days out (not with its lowest of five).

Same checkpoints and flight selection as ss5_full.py (60, 30, 21, 14, 7 days out, +/-2 days, all five present).
State at each checkpoint, fare / fare_at_60 - 1:
  Cheaper  <= -10%,  Same  within +/-10%,  Higher  +10% to +25%,  Much higher  >= +25%
At 60 days out every flight is 'Same' by construction, so the chart starts as one bar.
"""
import json
import os
from redo_common import connect, step

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "ss5")
CPS = [60, 30, 21, 14, 7]
con = connect()
step("fares at the five checkpoints")
con.execute("""
    CREATE OR REPLACE TEMP TABLE cp AS
    WITH c AS (
      SELECT d.legId, d.dbf, d.fare, t.cp,
             ROW_NUMBER() OVER (PARTITION BY d.legId, t.cp ORDER BY ABS(d.dbf - t.cp), d.dbf DESC) AS rn
      FROM daily d JOIN (VALUES (60), (30), (21), (14), (7)) t(cp) ON ABS(d.dbf - t.cp) <= 2)
    SELECT legId, cp, fare FROM c WHERE rn = 1""")
con.execute("""
    CREATE OR REPLACE TEMP TABLE paths AS
    WITH full5 AS (SELECT legId FROM cp GROUP BY legId HAVING COUNT(*) = 5),
         w AS (SELECT legId,
                 MAX(fare) FILTER (WHERE cp = 60) AS f60, MAX(fare) FILTER (WHERE cp = 30) AS f30, MAX(fare) FILTER (WHERE cp = 21) AS f21,
                 MAX(fare) FILTER (WHERE cp = 14) AS f14, MAX(fare) FILTER (WHERE cp = 7) AS f7
               FROM cp JOIN full5 USING (legId) GROUP BY legId)
    SELECT legId, f60, f30, f21, f14, f7 FROM w""")
band = lambda c: f"CASE WHEN {c} / f60 - 1 <= -0.10 THEN 'D' WHEN {c} / f60 - 1 < 0.10 THEN 'S' WHEN {c} / f60 - 1 < 0.25 THEN 'U' ELSE 'X' END"
con.execute(f"CREATE OR REPLACE TEMP TABLE bp AS SELECT legId, {', '.join(f'{band(c)} AS b{c[1:]}' for c in ['f60', 'f30', 'f21', 'f14', 'f7'])}, f7 / f60 - 1 AS chg7 FROM paths")
n = con.execute("SELECT COUNT(*) FROM bp").fetchone()[0]
step(f"flights: {n:,}")
cols = ["b60", "b30", "b21", "b14", "b7"]
shares = {}
for c in cols:
    for k in "DSUX":
        shares[f"{k}_{c[1:]}"] = round(100 * con.execute(f"SELECT AVG(({c} = '{k}')::INT) FROM bp").fetchone()[0], 1)
links = []
for a, b, ca, cb in zip(CPS, CPS[1:], cols, cols[1:]):
    for fa, fb, cnt in con.execute(f"SELECT {ca}, {cb}, COUNT(*) FROM bp GROUP BY ALL ORDER BY 1, 2").fetchall():
        links.append([a, fa, b, fb, int(cnt)])
extra = con.execute("""SELECT ROUND(100 * AVG((b7 IN ('U','X'))::INT), 1), ROUND(100 * AVG((b7 = 'D')::INT), 1),
                              ROUND(100 * AVG((b21 IN ('U','X'))::INT), 1), ROUND(100 * MEDIAN(chg7), 1) FROM bp""").fetchone()
sample = ["".join(r) for r in con.execute(f"SELECT {', '.join(cols)} FROM bp USING SAMPLE reservoir(1000 ROWS) REPEATABLE (42)").fetchall()]
out = {"definition": "fare at each checkpoint vs the same flight's fare 60 days out: D <= -10%, S within 10%, U +10 to +25%, X >= +25%",
       "flights": n, "shares": shares, "links": links, "sample": sample,
       "higher_at_7": extra[0], "cheaper_at_7": extra[1], "higher_at_21": extra[2], "median_change_7": extra[3]}
json.dump(out, open(os.path.join(OUT, "ss5_baseline.json"), "w"), separators=(",", ":"))
print(json.dumps({k: v for k, v in out.items() if k not in ("links", "sample")}, indent=1))
