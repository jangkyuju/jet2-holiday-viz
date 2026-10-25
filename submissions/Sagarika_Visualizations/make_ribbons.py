import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))

candidates = [
    os.path.join(HERE, "expedia_flight_cleaned.csv"),
    os.path.join(HERE, "data", "expedia_flight_cleaned.csv"),
]

PATH = next((p for p in candidates if os.path.exists(p)), None)

if PATH is None:
    raise FileNotFoundError("Was not able to find the expedia_flight_cleaned.csv!")

OUT_DIR = os.path.dirname(PATH)

CHECKPOINTS = [60, 30, 21, 14, 7]
TOL = 2

df = pd.read_csv(PATH)

print("Reading:", PATH)
print("Rows:", len(df))
print("Periods in the file:,", df.period.unique())

snaps = []
for cp in CHECKPOINTS:
    s = df[(df.daysBefore - cp).abs() <= TOL].copy()
    s["dist"] = (s.daysBefore - cp).abs()
    s = s.sort_values("dist").drop_duplicates("legId")
    s["cp"] = cp
    snaps.append(s)
snap = pd.concat(snaps)

wide = (snap.pivot_table(index=["legId", "period"], columns = "cp", values = "minFare")
        .dropna())

print("\nFlights that have all 5 checkpoints: ", len(wide))
print(wide.reset_index().period.value_counts())

low = wide.min(axis=1)
ratio = wide.div(low, axis=0) - 1

states = ratio.apply(lambda col: pd.cut(
    col, [-1, 0.05, 0.10, 99],
    labels = ["Floor", "Middle", "Jumped"],
    include_lowest = True, right = False
))

links = []
for a, b in zip(CHECKPOINTS, CHECKPOINTS[1:]):
    t = (states.groupby([states[a], states[b]], observed=True)
         .size().reset_index(name = "count"))
    t.columns = ["from_state", "to_state", "count"]
    t["from_cp"], t["to_cp"] = a, b
    links.append(t)

links = pd.concat(links)[["from_cp", "from_state", "to_cp", "to_state", "count"]]

links.to_csv(os.path.join(OUT_DIR, "ribbon_widths.csv"), index = False)
states.reset_index().to_csv(os.path.join(OUT_DIR, "flight_states.csv"), index=False)
