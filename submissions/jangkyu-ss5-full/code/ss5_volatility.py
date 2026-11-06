"""How much fares move between consecutive SS5 checkpoints (same flights as ss5_baseline7.py)."""
import json, os
from redo_common import connect
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "ss5")
con = connect()
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
rows = {}
for a, b, days in [("f60", "f30", 30), ("f30", "f21", 9), ("f21", "f14", 7), ("f14", "f7", 7), ("f60", "f21", 39), ("f21", "f7", 14)]:
    r = con.execute(f"""SELECT ROUND(100 * AVG((ABS({b} / {a} - 1) >= 0.10)::INT), 1), ROUND(100 * AVG(({b} / {a} - 1 >= 0.10)::INT), 1),
                               ROUND(100 * AVG(({b} / {a} - 1 <= -0.10)::INT), 1), ROUND(100 * AVG(({b} = {a})::INT), 1),
                               ROUND(100 * STDDEV(LN({b} / {a})), 1), ROUND(100 * MEDIAN({b} / {a} - 1), 1), ROUND(100 * (AVG({b}) / AVG({a}) - 1), 1)
                        FROM w""").fetchone()
    rows[f"{a[1:]}->{b[1:]}"] = dict(days=days, moved10=r[0], up10=r[1], down10=r[2], same=r[3], sd_log=r[4], median=r[5], mean_change=r[6])
print(json.dumps(rows, indent=1))
json.dump(rows, open(os.path.join(OUT, "ss5_volatility.json"), "w"), indent=1)
