"""Shared setup for the full-dataset re-analysis of the team's submissions."""
import os
import time
import duckdb
import pandas as pd

PARQUET = r"C:\Users\jujkp\.cache\kagglehub\datasets\dilwong\flightprices\versions\1\itineraries.parquet"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "redo")
os.makedirs(OUT, exist_ok=True)

# Same windows the team used (flight dates, inclusive). "All flights" is every flight date.
PERIOD_SQL = """CASE
  WHEN flightDate BETWEEN DATE '2022-05-26' AND DATE '2022-05-31' THEN 'Memorial Day'
  WHEN flightDate BETWEEN DATE '2022-06-30' AND DATE '2022-07-05' THEN 'July 4'
  WHEN flightDate BETWEEN DATE '2022-09-01' AND DATE '2022-09-06' THEN 'Labor Day'
  WHEN flightDate BETWEEN DATE '2022-06-09' AND DATE '2022-06-14'
    OR flightDate BETWEEN DATE '2022-08-11' AND DATE '2022-08-16' THEN 'Non-holiday'
END"""
PERIODS = ["All flights", "Memorial Day", "July 4", "Labor Day", "Non-holiday"]

pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 300)
_t0 = time.time()


def step(msg):
    print(f"[{time.time() - _t0:6.0f}s] {msg}", flush=True)


def connect():
    con = duckdb.connect(os.path.join(HERE, "out", "work.duckdb"))
    con.execute("SET memory_limit='6GB'")
    con.execute(f"SET temp_directory='{os.path.dirname(PARQUET).replace(os.sep, '/')}/duckdb_tmp'")
    # every quote, with period tag (one row per flight per search day in this dataset)
    con.execute(f"""CREATE OR REPLACE TEMP VIEW q AS
        SELECT legId, searchDate, flightDate, startingAirport AS orig, destinationAirport AS dest,
               DATE_DIFF('day', searchDate, flightDate) AS dbf, isNonStop AS nonstop, isBasicEconomy AS basic,
               totalFare AS fare, NULLIF(seatsRemaining, 0) AS seats, totalTravelDistance AS dist,
               {PERIOD_SQL} AS period
        FROM read_parquet('{PARQUET}')""")
    return con


def save(df, name):
    df.to_csv(os.path.join(OUT, name), index=False)
    return df


def by_period(con, sql_select, group_extra="", where="TRUE"):
    """Run one aggregate for all flights and for each holiday window, stacked."""
    parts = [f"SELECT 'All flights' AS period, {sql_select} FROM q WHERE {where} {('GROUP BY ' + group_extra) if group_extra else ''}",
             f"SELECT period, {sql_select} FROM q WHERE period IS NOT NULL AND {where} GROUP BY period{(', ' + group_extra) if group_extra else ''}"]
    return con.execute(" UNION ALL ".join(parts)).df()
