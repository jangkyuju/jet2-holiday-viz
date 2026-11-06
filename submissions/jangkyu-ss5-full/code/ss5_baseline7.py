"""SS5 checkpoints vs each flight's own fare 60 days out, in seven symmetric bands.

Same flights as ss5_full.py (60, 30, 21, 14, 7 days out, +/-2 days, all five present).
Change c = fare / fare_at_60 - 1:
  A  c <= -20%     B  -20% < c <= -10%    C  -10% < c < 0
  Z  c = 0 (same fare)
  E  0 < c < 10%   F  10% <= c < 20%      G  c >= 20%
Also: how deep the discounts go, and the day-21 -> day-7 story numbers.
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
    WITH c AS (SELECT d.legId, d.dbf, d.fare, t.cp,
                 ROW_NUMBER() OVER (PARTITION BY d.legId, t.cp ORDER BY ABS(d.dbf - t.cp), d.dbf DESC) AS rn
               FROM daily d JOIN (VALUES (60), (30), (21), (14), (7)) t(cp) ON ABS(d.dbf - t.cp) <= 2)
    SELECT legId, cp, fare FROM c WHERE rn = 1""")
con.execute("""
    CREATE OR REPLACE TEMP TABLE w AS
    WITH full5 AS (SELECT legId FROM cp GROUP BY legId HAVING COUNT(*) = 5)
    SELECT legId, MAX(fare) FILTER (WHERE cp = 60) AS f60, MAX(fare) FILTER (WHERE cp = 30) AS f30, MAX(fare) FILTER (WHERE cp = 21) AS f21,
           MAX(fare) FILTER (WHERE cp = 14) AS f14, MAX(fare) FILTER (WHERE cp = 7) AS f7
    FROM cp JOIN full5 USING (legId) GROUP BY legId""")
def band(c):
    x = f"({c} / f60 - 1)"
    return (f"CASE WHEN {x} <= -0.20 THEN 'A' WHEN {x} <= -0.10 THEN 'B' WHEN {c} < f60 THEN 'C' WHEN {c} = f60 THEN 'Z' "
            f"WHEN {x} < 0.10 THEN 'E' WHEN {x} < 0.20 THEN 'F' ELSE 'G' END")
cols = ["b60", "b30", "b21", "b14", "b7"]
con.execute(f"CREATE OR REPLACE TEMP TABLE bp AS SELECT *, {', '.join(f'{band(f)} AS b{f[1:]}' for f in ['f60', 'f30', 'f21', 'f14', 'f7'])} FROM w")
n = con.execute("SELECT COUNT(*) FROM bp").fetchone()[0]
step(f"flights: {n:,}")
shares = {}
for c in cols:
    for code, cnt in con.execute(f"SELECT {c}, COUNT(*) FROM bp GROUP BY 1").fetchall():
        shares[f"{code}_{c[1:]}"] = round(100 * cnt / n, 1)
links = []
for a, b, ca, cb in zip(CPS, CPS[1:], cols, cols[1:]):
    for fa, fb, cnt in con.execute(f"SELECT {ca}, {cb}, COUNT(*) FROM bp GROUP BY ALL ORDER BY 1, 2").fetchall():
        links.append([a, fa, b, fb, int(cnt)])
# how deep discounts go, at each checkpoint, among flights cheaper than at 60 days
depth = {}
for c in ["f30", "f21", "f14", "f7"]:
    r = con.execute(f"""SELECT ROUND(100 * MIN({c} / f60 - 1), 1), ROUND(100 * QUANTILE_CONT({c} / f60 - 1, 0.01), 1),
                               ROUND(100 * MEDIAN({c} / f60 - 1) FILTER (WHERE {c} < f60), 1),
                               ROUND(100 * MAX({c} / f60 - 1), 1), ROUND(100 * QUANTILE_CONT({c} / f60 - 1, 0.99), 1)
                        FROM bp""").fetchone()
    depth[c[1:]] = {"deepest": r[0], "p1": r[1], "median_of_cheaper": r[2], "highest": r[3], "p99": r[4]}
story = con.execute("""SELECT ROUND(100 * AVG((f7 / f21 - 1 >= 0.10)::INT), 1), ROUND(100 * AVG((f7 / f21 - 1 <= -0.10)::INT), 1) FROM bp""").fetchone()
sample = ["".join(r) for r in con.execute(f"SELECT {', '.join(cols)} FROM bp USING SAMPLE reservoir(1000 ROWS) REPEATABLE (42)").fetchall()]
out = {"definition": "fare at each checkpoint vs the same flight's fare 60 days out: A <=-20%, B -20..-10%, C -10..0%, Z same fare, E 0..+10%, F +10..+20%, G >=+20%",
       "flights": n, "shares": shares, "links": links, "sample": sample, "depth": depth,
       "story": {"all_up10_21to7": story[0], "all_down10_21to7": story[1]}}
json.dump(out, open(os.path.join(OUT, "ss5_baseline7.json"), "w"), separators=(",", ":"))
print(json.dumps({k: v for k, v in out.items() if k not in ("links", "sample")}, indent=1))
