# =============================================================================
# Jet 2 Holiday — CZ-01 / CZ-03 prototype: clean-data export
# Cynthia Zhou
#
# WHERE TO RUN THIS: a Kaggle Notebook with the dataset `dilwong/flightprices`
# attached (same setup as the Week-3 Data Exploration notebook). Each "# %%"
# block below is one notebook cell. Run them top to bottom.
#
# WHAT IT PRODUCES (CSVs in /kaggle/working/):
#   cz_staircase.csv  median / IQR lowest fare + seat scarcity, by period x daysBefore
#   cz_changes.csv    share of fares that rose or fell >=10% since the last check
#   cz_diary.csv      day-by-day fare history of 48 individual flights (the diary)
#   cz_site_diary.csv Labor Day, up to 8 real flights per route, for the team
#                     site's diary scene (which follows the route picked on its map)
#
# Download all three from the notebook's Output panel into
#   "04 - Prototype Phase 1&2/data/"
# and the chart build script will pick them up automatically.
#
# The aggregation logic is deliberately identical to cynthia_exploration.py, so
# the prototype's numbers match the Data Exploration section already in the
# process book.
# =============================================================================

# %% Cell 1: build the holiday subset (~5 min; scans the full 6 GB CSV once)
import duckdb, glob, os, time

path = glob.glob('/kaggle/input/**/itineraries.csv', recursive=True)[0]
print("Data file:", path)
con = duckdb.connect('/kaggle/working/flights.duckdb')

# Flight-date windows. Three holidays plus two ordinary summer weeks as a baseline.
HOLIDAY_SQL = """
    CASE
      WHEN fd BETWEEN DATE '2022-05-26' AND DATE '2022-05-31' THEN 'Memorial Day'
      WHEN fd BETWEEN DATE '2022-06-30' AND DATE '2022-07-05' THEN 'July 4'
      WHEN fd BETWEEN DATE '2022-09-01' AND DATE '2022-09-06' THEN 'Labor Day'
      ELSE 'Non-holiday'
    END
"""
WINDOW_FILTER = """
       fd BETWEEN DATE '2022-05-26' AND DATE '2022-05-31'
    OR fd BETWEEN DATE '2022-06-30' AND DATE '2022-07-05'
    OR fd BETWEEN DATE '2022-09-01' AND DATE '2022-09-06'
    OR fd BETWEEN DATE '2022-06-09' AND DATE '2022-06-14'
    OR fd BETWEEN DATE '2022-08-11' AND DATE '2022-08-16'
"""

already_built = con.sql(
    "SELECT count(*) FROM duckdb_tables() WHERE table_name = 'daily'"
).fetchone()[0]

if already_built:
    print("Table `daily` already exists in flights.duckdb — skipping the 6 GB scan.")
else:
    start = time.time()
    con.sql(f"""
    CREATE OR REPLACE TABLE daily AS
    WITH raw AS (
      SELECT *, CAST(flightDate AS DATE) AS fd, CAST(searchDate AS DATE) AS sd
      FROM read_csv_auto('{path}')
    )
    SELECT
      legId, fd AS flightDate, sd AS searchDate,
      startingAirport, destinationAirport,
      {HOLIDAY_SQL} AS period,
      DATEDIFF('day', sd, fd) AS daysBefore,
      ANY_VALUE(segmentsAirlineName) AS airline,
      ANY_VALUE(isNonStop)           AS isNonStop,
      MIN(totalFare)                 AS minFare,
      ARG_MIN(seatsRemaining, totalFare) AS seatsAtMinFare,
      COUNT(*)                       AS nFares
    FROM raw
    WHERE {WINDOW_FILTER}
    GROUP BY legId, fd, sd, startingAirport, destinationAirport
    """)
    print(f"Built `daily` in {time.time()-start:.0f}s")

print(con.sql("""
  SELECT period, COUNT(*) AS rows, COUNT(DISTINCT legId) AS flights,
         MIN(searchDate) AS first_search, MAX(searchDate) AS last_search
  FROM daily GROUP BY period ORDER BY period
""").df().to_string(index=False))


# %% Cell 2: day-over-day fare change for every flight
# Each row is compared with the SAME flight's previous observed search date.
# Gaps longer than 3 days are dropped so a "change" is always a short-horizon one.
con.sql("""
CREATE OR REPLACE TABLE changes AS
SELECT *,
  LAG(minFare)    OVER w AS prevFare,
  DATEDIFF('day', LAG(searchDate) OVER w, searchDate) AS gapDays
FROM daily
WINDOW w AS (PARTITION BY legId, flightDate ORDER BY searchDate)
""")

print(con.sql("""
  SELECT gapDays, COUNT(*) AS n,
         ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
  FROM changes WHERE prevFare IS NOT NULL AND gapDays <= 3
  GROUP BY gapDays ORDER BY gapDays
""").df().to_string(index=False))


# %% Cell 3: EXPORT 1 — cz_staircase.csv  (drives CZ-03, the staircase)
con.sql("""
COPY (
  SELECT period, daysBefore,
         ROUND(MEDIAN(minFare), 2)                   AS median_fare,
         ROUND(QUANTILE_CONT(minFare, 0.25), 2)      AS p25_fare,
         ROUND(QUANTILE_CONT(minFare, 0.75), 2)      AS p75_fare,
         ROUND(AVG(CASE WHEN seatsAtMinFare BETWEEN 1 AND 3 THEN 1 ELSE 0 END)
               FILTER (WHERE seatsAtMinFare > 0) * 100, 2) AS pct_low_seats,
         COUNT(*)                                    AS n_flights
  FROM daily
  WHERE daysBefore BETWEEN 0 AND 60
  GROUP BY period, daysBefore
  ORDER BY period, daysBefore
) TO '/kaggle/working/cz_staircase.csv' (HEADER, DELIMITER ',')
""")
print("wrote cz_staircase.csv",
      con.sql("SELECT COUNT(*) FROM read_csv_auto('/kaggle/working/cz_staircase.csv')").fetchone()[0], "rows")


# %% Cell 4: EXPORT 2 — cz_changes.csv  (the >=10% move rates; annotates CZ-01)
con.sql("""
COPY (
  SELECT period, daysBefore, COUNT(*) AS n,
         ROUND(AVG(CASE WHEN minFare <= prevFare * 0.9 THEN 1 ELSE 0 END) * 100, 2) AS pct_drop,
         ROUND(AVG(CASE WHEN minFare >= prevFare * 1.1 THEN 1 ELSE 0 END) * 100, 2) AS pct_rise,
         ROUND(AVG(CASE WHEN minFare > prevFare * 0.9
                         AND minFare < prevFare * 1.1 THEN 1 ELSE 0 END) * 100, 2) AS pct_flat
  FROM changes
  WHERE prevFare IS NOT NULL AND gapDays <= 3 AND daysBefore BETWEEN 0 AND 60
  GROUP BY period, daysBefore
  ORDER BY period, daysBefore
) TO '/kaggle/working/cz_changes.csv' (HEADER, DELIMITER ',')
""")
print("wrote cz_changes.csv",
      con.sql("SELECT COUNT(*) FROM read_csv_auto('/kaggle/working/cz_changes.csv')").fetchone()[0], "rows")


# %% Cell 5: EXPORT 3 — cz_diary.csv  (drives CZ-01, the price diary)
# One diary row = one real flight a traveler really could have watched every
# morning: observed on at least 20 separate search days and still listed within
# 7 days of departure. Per period we keep the 12 most densely observed flights,
# at most one per route and one per departure airport, so the diary spans the
# country instead of one hub. Many flights tie on coverage; ties are broken by
# md5(route), a fixed pseudo-random order -- a rule, not a hand pick, so the
# selection is reproducible and not cherry-picked.
con.sql("""
CREATE OR REPLACE TABLE diary_pick AS
WITH dense AS (
  SELECT legId, flightDate, period, startingAirport,
         startingAirport || '-' || destinationAirport AS route,
         ANY_VALUE(airline)   AS airline,
         ANY_VALUE(isNonStop) AS isNonStop,
         COUNT(*)             AS nDays,
         MIN(daysBefore)      AS minDb,
         MAX(daysBefore)      AS maxDb
  FROM daily
  WHERE daysBefore BETWEEN 0 AND 60
  GROUP BY legId, flightDate, period, startingAirport, destinationAirport
  HAVING COUNT(*) >= 20 AND MIN(daysBefore) <= 7
),
one_per_route AS (
  SELECT * FROM dense
  QUALIFY ROW_NUMBER() OVER (PARTITION BY period, route ORDER BY nDays DESC, legId) = 1
),
one_per_origin AS (
  SELECT * FROM one_per_route
  QUALIFY ROW_NUMBER() OVER (PARTITION BY period, startingAirport
                             ORDER BY nDays DESC, md5(route)) = 1
)
SELECT * FROM one_per_origin
QUALIFY ROW_NUMBER() OVER (PARTITION BY period ORDER BY nDays DESC, md5(route)) <= 12
""")

print(con.sql("""
  SELECT period, COUNT(*) AS flights_picked,
         COUNT(DISTINCT startingAirport) AS origins,
         MIN(nDays) AS fewest_mornings, MAX(nDays) AS most_mornings,
         STRING_AGG(route, ' ' ORDER BY route) AS routes
  FROM diary_pick GROUP BY period ORDER BY period
""").df().to_string(index=False))

con.sql("""
COPY (
  SELECT c.legId, c.period, p.route, p.airline, p.isNonStop,
         c.flightDate, c.searchDate, c.daysBefore,
         c.minFare, c.prevFare, c.gapDays, c.seatsAtMinFare,
         CASE WHEN c.prevFare IS NULL OR c.gapDays > 3 THEN NULL
              ELSE ROUND((c.minFare - c.prevFare) / c.prevFare * 100, 3) END AS pct_change
  FROM changes c
  JOIN diary_pick p ON c.legId = p.legId AND c.flightDate = p.flightDate
  WHERE c.daysBefore BETWEEN 0 AND 60
  ORDER BY c.period, p.route, c.legId, c.daysBefore DESC
) TO '/kaggle/working/cz_diary.csv' (HEADER, DELIMITER ',')
""")
print("wrote cz_diary.csv",
      con.sql("SELECT COUNT(*) FROM read_csv_auto('/kaggle/working/cz_diary.csv')").fetchone()[0], "rows")


# %% Cell 6: numbers to quote in the process book
print("--- CZ-03 staircase, Labor Day key points ---")
print(con.sql("""
  SELECT daysBefore, ROUND(MEDIAN(minFare),0) AS median_fare
  FROM daily WHERE period = 'Labor Day' AND daysBefore IN (60, 21, 14, 13, 7, 1)
  GROUP BY daysBefore ORDER BY daysBefore DESC
""").df().to_string(index=False))

print("\n--- CZ-01 diary, overall outcome mix (all periods, 0-60 days) ---")
print(con.sql("""
  SELECT ROUND(AVG(CASE WHEN minFare >= prevFare*1.1 THEN 1 ELSE 0 END)*100, 1) AS pct_rose_10,
         ROUND(AVG(CASE WHEN minFare <= prevFare*0.9 THEN 1 ELSE 0 END)*100, 1) AS pct_fell_10,
         ROUND(AVG(CASE WHEN minFare > prevFare*0.9
                         AND minFare < prevFare*1.1 THEN 1 ELSE 0 END)*100, 1) AS pct_flat,
         COUNT(*) AS n_checks
  FROM changes
  WHERE prevFare IS NOT NULL AND gapDays <= 3 AND daysBefore BETWEEN 0 AND 60
""").df().to_string(index=False))



# %% Cell 7: EXPORT 4 — cz_site_diary.csv  (the team site's CZ-01 scene)
# The site's diary shows four flights at a time for whatever route the reader
# picked on the map, so it needs real flights for every route, not one per
# period. Labor Day only (the scene is labelled "YOUR TRIP · LABOR DAY").
# Per route: up to 8 flights with a check on at least 50 of the 60 mornings,
# first seen 58+ days out and still listed 3 days out; densest first.
# The change class uses exactly the rule above (>=10% vs the same flight's
# previous check, gaps over 3 days not compared).
con.sql("""
CREATE OR REPLACE TABLE site_pick AS
SELECT legId, flightDate,
       startingAirport || '-' || destinationAirport AS route,
       ANY_VALUE(airline) AS airline, ANY_VALUE(isNonStop) AS isNonStop,
       COUNT(*) AS nDays
FROM daily
WHERE period = 'Labor Day' AND daysBefore BETWEEN 1 AND 60
GROUP BY legId, flightDate, startingAirport, destinationAirport
HAVING COUNT(*) >= 50 AND MAX(daysBefore) >= 58 AND MIN(daysBefore) <= 3
QUALIFY ROW_NUMBER() OVER (PARTITION BY route ORDER BY nDays DESC, legId) <= 8
""")
print(con.sql("""
  SELECT COUNT(DISTINCT route) AS routes, COUNT(*) AS flights,
         MIN(nDays) AS fewest_mornings, ROUND(AVG(nDays),1) AS avg_mornings
  FROM site_pick
""").df().to_string(index=False))

con.sql("""
COPY (
  SELECT p.route, c.legId, p.airline, p.isNonStop, c.daysBefore, c.minFare,
         CASE WHEN c.prevFare IS NULL OR c.gapDays > 3 THEN NULL
              WHEN c.minFare >= c.prevFare * 1.1 THEN 'rose'
              WHEN c.minFare <= c.prevFare * 0.9 THEN 'fell'
              ELSE 'flat' END AS cls
  FROM changes c
  JOIN site_pick p ON c.legId = p.legId AND c.flightDate = p.flightDate
  WHERE c.daysBefore BETWEEN 1 AND 60
  ORDER BY p.route, p.nDays DESC, c.legId, c.daysBefore DESC
) TO '/kaggle/working/cz_site_diary.csv' (HEADER, DELIMITER ',')
""")


# %% Cell 8: file sizes, and tidy up when run as a batch job
print("\n--- file sizes ---")
for f in ['cz_staircase.csv', 'cz_changes.csv', 'cz_diary.csv', 'cz_site_diary.csv']:
    print(f"{f:20s} {os.path.getsize('/kaggle/working/'+f)/1024:8.1f} KB")

# When this runs as a pushed script (not in the notebook editor), drop the
# working database so the job's output is only the small CSVs.
if os.environ.get("KAGGLE_KERNEL_RUN_TYPE", "").lower() == "batch":
    con.close()
    os.remove('/kaggle/working/flights.duckdb')
    print("removed flights.duckdb from the batch output")
print("\nDownload the cz_*.csv files from the Output panel on the right.")
