"""Basic statistics for the Expedia Flight Prices dataset (dilwong/flightprices).

Converts itineraries.csv to Parquet once (much faster for later queries), then prints
an overview: size, date ranges, airports and routes, fares, flight attributes, missing values.
"""
import os
import time
import duckdb

CSV = r"C:\Users\jujkp\.cache\kagglehub\datasets\dilwong\flightprices\versions\1\itineraries.csv"
PARQUET = os.path.join(os.path.dirname(CSV), "itineraries.parquet")

con = duckdb.connect()
con.execute("SET memory_limit='6GB'")
con.execute(f"SET temp_directory='{os.path.dirname(CSV).replace(os.sep, '/')}/duckdb_tmp'")

t0 = time.time()
if not os.path.exists(PARQUET):
    print("Converting CSV to Parquet (one time)...", flush=True)
    con.execute(f"""
        COPY (SELECT * EXCLUDE (segmentsDepartureTimeEpochSeconds, segmentsArrivalTimeEpochSeconds, segmentsDurationInSeconds, segmentsDistance)
              FROM read_csv_auto('{CSV}'))
        TO '{PARQUET}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    print(f"  done in {time.time() - t0:.0f}s, {os.path.getsize(PARQUET) / 1e9:.1f} GB", flush=True)
con.execute(f"CREATE VIEW f AS SELECT * FROM read_parquet('{PARQUET}')")

def show(title, sql):
    print(f"\n== {title} ==", flush=True)
    print(con.execute(sql).df().to_string(index=False), flush=True)

show("Size and coverage", """
    SELECT COUNT(*) AS rows,
           COUNT(DISTINCT legId) AS unique_flights,
           MIN(searchDate) AS first_search, MAX(searchDate) AS last_search, COUNT(DISTINCT searchDate) AS search_days,
           MIN(flightDate) AS first_flight, MAX(flightDate) AS last_flight,
           COUNT(DISTINCT startingAirport) AS origins, COUNT(DISTINCT destinationAirport) AS destinations,
           COUNT(DISTINCT startingAirport || '-' || destinationAirport) AS routes
    FROM f""")

show("Days between search and flight", """
    SELECT MIN(d) AS min_days, QUANTILE_CONT(d, 0.25) AS p25, MEDIAN(d) AS median, QUANTILE_CONT(d, 0.75) AS p75, MAX(d) AS max_days
    FROM (SELECT DATE_DIFF('day', searchDate, flightDate) AS d FROM f)""")

show("Total fare (USD)", """
    SELECT MIN(totalFare) AS min, QUANTILE_CONT(totalFare, 0.01) AS p1, QUANTILE_CONT(totalFare, 0.25) AS p25,
           MEDIAN(totalFare) AS median, ROUND(AVG(totalFare), 2) AS mean, QUANTILE_CONT(totalFare, 0.75) AS p75,
           QUANTILE_CONT(totalFare, 0.99) AS p99, MAX(totalFare) AS max, ROUND(STDDEV(totalFare), 2) AS sd,
           ROUND(AVG(totalFare - baseFare), 2) AS avg_taxes_fees
    FROM f""")

show("Flight attributes (share of rows, %)", """
    SELECT ROUND(100 * AVG(isNonStop::INT), 1) AS nonstop,
           ROUND(100 * AVG(isBasicEconomy::INT), 1) AS basic_economy,
           ROUND(100 * AVG(isRefundable::INT), 1) AS refundable,
           ROUND(100 * AVG((elapsedDays > 0)::INT), 1) AS arrives_next_day,
           ROUND(100 * AVG((seatsRemaining = 0)::INT), 1) AS seats_zero,
           MEDIAN(seatsRemaining) AS median_seats_left,
           MEDIAN(totalTravelDistance) AS median_distance_mi
    FROM f""")

show("Missing values (rows)", """
    SELECT COUNT(*) - COUNT(totalTravelDistance) AS distance_missing,
           COUNT(*) - COUNT(segmentsAirlineName) AS airline_missing,
           COUNT(*) - COUNT(segmentsCabinCode) AS cabin_missing,
           COUNT(*) - COUNT(travelDuration) AS duration_missing
    FROM f""")

show("Rows by origin airport", """
    SELECT startingAirport AS airport, COUNT(*) AS rows, MEDIAN(totalFare) AS median_fare,
           ROUND(100 * AVG(isNonStop::INT), 1) AS pct_nonstop
    FROM f GROUP BY 1 ORDER BY rows DESC""")

show("Top 10 airlines (itinerary as listed; '||' joins segments)", """
    SELECT segmentsAirlineName AS airline, COUNT(*) AS rows, MEDIAN(totalFare) AS median_fare
    FROM f GROUP BY 1 ORDER BY rows DESC LIMIT 10""")

show("Number of segments", """
    SELECT LEN(STRING_SPLIT(segmentsAirlineCode, '||')) AS segments, COUNT(*) AS rows, MEDIAN(totalFare) AS median_fare
    FROM f GROUP BY 1 ORDER BY 1""")

show("Cabin (first segment)", """
    SELECT STRING_SPLIT(segmentsCabinCode, '||')[1] AS cabin, COUNT(*) AS rows, MEDIAN(totalFare) AS median_fare
    FROM f GROUP BY 1 ORDER BY rows DESC""")

show("Rows by flight month", """
    SELECT STRFTIME(flightDate, '%Y-%m') AS month, COUNT(*) AS rows, MEDIAN(totalFare) AS median_fare
    FROM f GROUP BY 1 ORDER BY 1""")

show("Our holiday windows (flight dates)", """
    SELECT period, COUNT(*) AS rows, COUNT(DISTINCT legId) AS flights, MEDIAN(totalFare) AS median_fare FROM (
      SELECT CASE WHEN flightDate BETWEEN '2022-05-26' AND '2022-05-31' THEN 'Memorial Day'
                  WHEN flightDate BETWEEN '2022-06-30' AND '2022-07-05' THEN 'July 4'
                  WHEN flightDate BETWEEN '2022-09-01' AND '2022-09-06' THEN 'Labor Day'
                  WHEN flightDate BETWEEN '2022-06-09' AND '2022-06-14' OR flightDate BETWEEN '2022-08-11' AND '2022-08-16' THEN 'Non-holiday'
             END AS period, legId, totalFare FROM f)
    WHERE period IS NOT NULL GROUP BY 1 ORDER BY rows DESC""")

print(f"\nTotal time {time.time() - t0:.0f}s")
