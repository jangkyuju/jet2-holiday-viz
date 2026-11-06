"""Story numbers for the 60-day-baseline alluvial: what happened to flights still at or below their 60-day fare at day 21."""
import json, os
from redo_common import connect, step
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
    SELECT legId, MAX(fare) FILTER (WHERE cp = 60) AS f60, MAX(fare) FILTER (WHERE cp = 21) AS f21, MAX(fare) FILTER (WHERE cp = 7) AS f7
    FROM cp JOIN full5 USING (legId) GROUP BY legId""")
r = con.execute("""
    SELECT COUNT(*) FILTER (WHERE f21 / f60 - 1 < 0.10) AS cohort,
           ROUND(100 * AVG((f7 / f60 - 1 >= 0.10)::INT) FILTER (WHERE f21 / f60 - 1 < 0.10), 1) AS cohort_higher7_vs60,
           ROUND(100 * AVG((f7 / f60 - 1 >= 0.25)::INT) FILTER (WHERE f21 / f60 - 1 < 0.10), 1) AS cohort_much7_vs60,
           ROUND(100 * AVG((f7 / f60 - 1 <= -0.10)::INT) FILTER (WHERE f21 / f60 - 1 < 0.10), 1) AS cohort_cheaper7_vs60,
           ROUND(100 * AVG((f21 / f60 - 1 < 0.10)::INT), 1) AS share_at_or_below_21,
           ROUND(100 * AVG((f7 / f21 - 1 >= 0.10)::INT), 1) AS all_up10_21to7,
           ROUND(100 * AVG((f7 / f21 - 1 <= -0.10)::INT), 1) AS all_down10_21to7,
           ROUND(100 * AVG((f7 / f21 - 1 >= 0.10)::INT) FILTER (WHERE f21 / f60 - 1 < 0.10), 1) AS cohort_up10_21to7,
           ROUND(100 * AVG((f7 / f21 - 1 <= -0.10)::INT) FILTER (WHERE f21 / f60 - 1 < 0.10), 1) AS cohort_down10_21to7
    FROM w""").df().iloc[0].to_dict()
r = {k: (int(v) if k == "cohort" else float(v)) for k, v in r.items()}
print(json.dumps(r, indent=1))
d = json.load(open(os.path.join(OUT, "ss5_baseline.json")))
d["story"] = r
json.dump(d, open(os.path.join(OUT, "ss5_baseline.json"), "w"), separators=(",", ":"))
