"""Prepare quote-level and chart-level CSVs for the team's Q7 Tableau chart.

Run with the six-column CSV as input. No source records are overwritten.
"""
from pathlib import Path
from collections import defaultdict, Counter
from datetime import date, timedelta
from functools import lru_cache
import argparse
import csv
import json
import time

PERIODS = {
    "Memorial Day": [("2022-05-26", "2022-05-31")],
    "July 4": [("2022-06-30", "2022-07-05")],
    "Labor Day": [("2022-09-01", "2022-09-06")],
    "Non-holiday": [("2022-06-09", "2022-06-14"), ("2022-08-11", "2022-08-16")],
}
SOURCE_COLUMNS = ["searchDate", "flightDate", "startingAirport", "destinationAirport", "isNonStop", "totalFare"]
QUOTE_COLUMNS = ["holiday", "flightType", "route"] + SOURCE_COLUMNS + ["daysBeforeFlight"]


def frequency_median(values):
    count = sum(values.values())
    assert count > 0
    lower = (count - 1) // 2
    upper = count // 2
    cumulative = 0
    lower_value = None
    for value, frequency in sorted(values.items()):
        cumulative += frequency
        if lower_value is None and cumulative > lower:
            lower_value = value
        if cumulative > upper:
            return (lower_value + value) / 200
    raise AssertionError("Missing median")


@lru_cache(maxsize=20000)
def lead_days(search, flight):
    return (date.fromisoformat(flight) - date.fromisoformat(search)).days


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="flightprices_six_columns.csv")
    parser.add_argument("--output", default=str(Path(__file__).parent))
    args = parser.parse_args()
    source = Path(args.input)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    quote_path = output / "Q7_Tableau_quotes.csv"
    route_values = defaultdict(Counter)
    scanned = retained = outside = invalid = 0
    lead_min = 10**9
    lead_max = -1
    started = time.monotonic()

    date_labels = {}
    for holiday, windows in PERIODS.items():
        for start, end in windows:
            current = date.fromisoformat(start)
            while current <= date.fromisoformat(end):
                date_labels[current.isoformat()] = holiday
                current += timedelta(days=1)
    with source.open(newline="", encoding="utf-8") as original, quote_path.open("w", newline="", encoding="utf-8") as target:
        assert next(csv.reader([original.readline()])) == SOURCE_COLUMNS
        writer = csv.writer(target, lineterminator="\n")
        writer.writerow(QUOTE_COLUMNS)
        for line in original:
            scanned += 1
            # These six source fields contain no embedded commas or newlines.
            holiday = date_labels.get(line[11:21])
            if holiday is None:
                outside += 1
            else:
                fields = line.rstrip("\r\n").split(",")
                if len(fields) != 6 or '"' in line:
                    fields = next(csv.reader([line]))
                assert len(fields) == 6
                search, flight, origin, destination, nonstop, fare_text = fields
                try:
                    days = lead_days(search, flight)
                    fare = float(fare_text)
                    cents = round(fare * 100)
                    good = (days >= 0 and cents > 0 and origin and destination and nonstop in ["True", "False"])
                except (ValueError, OverflowError):
                    good = False
                if not good:
                    invalid += 1
                else:
                    assert abs(fare - cents / 100) < 1e-7
                    flight_type = "Nonstop" if nonstop == "True" else "Connecting"
                    route = f"{origin}-{destination}"
                    writer.writerow([holiday, flight_type, route] + fields + [days])
                    route_values[(holiday, origin, destination, flight_type)][cents] += 1
                    retained += 1
                    lead_min = min(lead_min, days)
                    lead_max = max(lead_max, days)
            if scanned % 10_000_000 == 0:
                print(f"Scanned {scanned:,}; retained {retained:,}; {time.monotonic()-started:.0f}s", flush=True)

    assert scanned == 82_138_753, scanned
    assert scanned == outside + invalid + retained
    overall_values = defaultdict(Counter)
    route_rows = []
    for (holiday, origin, destination, flight_type), values in route_values.items():
        overall_values[(holiday, flight_type)].update(values)
        median = frequency_median(values)
        route_rows.append({
            "holiday": holiday, "route": f"{origin}-{destination}", "startingAirport": origin,
            "destinationAirport": destination, "flightType": flight_type,
            "medianFare": median, "quoteCount": sum(values.values()),
        })
    available = {(r["holiday"], r["route"], r["flightType"]) for r in route_rows}
    for row in route_rows:
        row["hasBothFlightTypes"] = all((row["holiday"], row["route"], t) in available for t in ["Nonstop", "Connecting"])
    order = {label: i for i, label in enumerate(PERIODS)}
    route_rows.sort(key=lambda r: (order[r["holiday"]], r["route"], r["flightType"] != "Nonstop"))

    chart_rows = []
    comparisons = []
    for holiday in PERIODS:
        by_type = {}
        for flight_type in ["Nonstop", "Connecting"]:
            values = overall_values[(holiday, flight_type)]
            # Median is calculated from all retained quote prices, not from route medians.
            median = frequency_median(values)
            by_type[flight_type] = median
            chart_rows.append({"holiday": holiday, "flightType": flight_type, "medianFare": median, "quoteCount": sum(values.values())})
        gap = by_type["Nonstop"] - by_type["Connecting"]
        comparisons.append({"holiday": holiday, "nonstopMedianFare": by_type["Nonstop"], "connectingMedianFare": by_type["Connecting"], "nonstopPremiumUSD": round(gap, 3), "nonstopPremiumPct": gap / by_type["Connecting"] * 100})
    assert sum(r["quoteCount"] for r in chart_rows) == retained
    assert sum(r["quoteCount"] for r in route_rows) == retained
    assert len(chart_rows) == 8

    for name, rows in [("Q7_Tableau_chart.csv", chart_rows), ("Q7_route_comparison.csv", route_rows)]:
        with (output / name).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    website_data = {
        "source": "https://www.kaggle.com/datasets/dilwong/flightprices",
        "currency": "USD", "statistic": "median totalFare across observed quotes",
        "periods": PERIODS, "overall": chart_rows, "byRoute": route_rows,
        "comparisons": comparisons,
    }
    (output / "Q7_website_data.json").write_text(json.dumps(website_data, ensure_ascii=False, indent=2), encoding="utf-8")
    report = {
        "source": str(source), "sourceBytes": source.stat().st_size,
        "scannedRows": scanned, "retainedRows": retained, "outsidePeriodRows": outside,
        "invalidRowsInSelectedPeriods": invalid, "daysBeforeFlightMin": lead_min, "daysBeforeFlightMax": lead_max,
        "periods": PERIODS, "summaryRows": chart_rows, "comparisons": comparisons,
        "routeSummaryRows": len(route_rows),
        "files": {p.name: p.stat().st_size for p in output.glob("Q7_*.csv")},
    }
    (output / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
