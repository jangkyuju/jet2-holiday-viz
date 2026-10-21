
from pathlib import Path
import csv
import duckdb
import airportsdata

# STEP 1: Set your file locations
# Replace this path with the actual location of your CSV.
csv_path = Path(r"C:\Users\arrin\DataVisFlights\itineraries.csv")

# Save outputs in the same folder as the original file.
output_folder = csv_path.parent

# STEP 2: Connect to DuckDB
con = duckdb.connect()
con.execute("SET threads = 4")
con.execute("SET memory_limit = '4GB'")
con.execute(
    f"SET temp_directory = '{(output_folder / 'duckdb_temp').as_posix()}'"
)

# STEP 3: Filter ATL flights and aggregate by destination.
# DuckDB processes the CSV without loading all rows into Python.
print("Reading and processing flight data...")

con.execute("""
CREATE TEMP TABLE airport_fares AS
SELECT
    destinationAirport AS airport,
    COUNT(*) AS itinerary_count,
    ROUND(AVG(totalFare), 2) AS avg_fare,
    ROUND(MIN(totalFare), 2) AS min_fare,
    SUM(totalFare) AS fare_sum
FROM read_csv(
    ?,
    header = true,
    auto_detect = true
)
WHERE startingAirport = 'ATL'
  AND destinationAirport IS NOT NULL
  AND totalFare IS NOT NULL
  AND totalFare > 0
GROUP BY destinationAirport
""", [str(csv_path)])

# STEP 4: Match airport codes to U.S. states.
airports = airportsdata.load("IATA")
print("ATL:", airports.get("ATL"))
print("LAX:", airports.get("LAX"))
print("JFK:", airports.get("JFK"))

airport_rows = con.execute("""
SELECT airport, itinerary_count, avg_fare, min_fare, fare_sum
FROM airport_fares
""").fetchall()
print("Number of destination airports:", len(airport_rows))
print("First 10 destinations:", airport_rows[:10])

results = []

for airport, count, avg, minimum, fare_sum in airport_rows:
    info = airports.get(airport)

    if not info or info.get("country") != "US":
        continue

    state = info.get("subd", "")

    if not state:
        continue

    results.append({
        "starting_airport": "ATL",
        "destination_airport": airport,
        "destination_state": state,
        "itinerary_count": count,
        "avg_fare": float(avg),
        "min_fare": float(minimum),
        "fare_sum": float(fare_sum)
    })

# STEP 5: Export airport-level summary.
airport_file = output_folder / "atl_airport_fares.csv"

with airport_file.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "starting_airport",
        "destination_airport",
        "destination_state",
        "itinerary_count",
        "avg_fare",
        "min_fare"
    ])
    writer.writeheader()
    for row in results:
        writer.writerow({
            k: row[k] for k in writer.fieldnames
        })

# STEP 6: Aggregate airports into states.
states = {}

for row in results:
    state = row["destination_state"]

    if state not in states:
        states[state] = {
            "count": 0,
            "fare_sum": 0,
            "min_fare": float("inf"),
            "airports": []
        }

    s = states[state]
    s["count"] += row["itinerary_count"]
    s["fare_sum"] += row["fare_sum"]
    s["min_fare"] = min(s["min_fare"], row["min_fare"])
    s["airports"].append(row)

state_file = output_folder / "atl_state_fares.csv"

with state_file.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "state",
        "country",
        "avg_fare",
        "min_fare",
        "cheapest_airport",
        "cheapest_airport_avg_fare",
        "itinerary_count",
        "airport_count"
    ])

    for state, s in sorted(states.items()):
        cheapest = min(
            s["airports"],
            key=lambda x: x["avg_fare"]
        )

        writer.writerow([
            state,
            "United States",
            round(s["fare_sum"] / s["count"], 2),
            round(s["min_fare"], 2),
            cheapest["destination_airport"],
            cheapest["avg_fare"],
            s["count"],
            len(s["airports"])
        ])

con.close()

print("Finished!")
print(f"Airport data: {airport_file}")
print(f"State data: {state_file}")
print(f"U.S. airports found: {len(results)}")
print(f"States/territories found: {len(states)}")
