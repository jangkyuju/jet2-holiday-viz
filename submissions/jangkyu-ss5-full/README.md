# SS5 on the full dataset (Sagarika's method, run by Jangkyu Ju)

Same definitions as `../Sagarika_Visualizations/make_ribbons.py`, applied to every flight in the
dataset instead of the 48 diary flights:

- Checkpoints 60, 30, 21, 14 and 7 days out; each flight's lowest daily fare on the day nearest each
  checkpoint, within ±2 days (exact day first, then the earlier day out).
- Flights with all five checkpoints: **482,975** (July 4: 28,297 · Labor Day: 34,259 · Non-holiday: 30,890;
  Memorial Day has none, because searches start 44 days before it).
- State at each checkpoint, relative to the flight's own lowest of its five prices:
  **Floor** < 5% above · **Middle** 5–10% · **Jumped** ≥ 10%.

## Results (all flights)

| Checkpoint | 60 | 30 | 21 | 14 | 7 |
|---|---|---|---|---|---|
| Floor | 34.5% | 37.0% | **39.8%** | 34.3% | 27.0% |
| Middle | 6.0% | 6.4% | 6.8% | 8.1% | 5.3% |
| Jumped | 59.5% | 56.5% | 53.4% | 57.6% | **67.8%** |

- The Floor band is widest at 21 days out, then shrinks.
- Of the flights at their floor on day 21, **72.5%** had jumped 10%+ by day 7; only 21.1% were still at the floor.
- By window: Labor Day is the sharpest (floor 48% at 21 days, 79% of those jumped by day 7).

## Files
- `data/ribbon_widths_*.csv` — transition counts between checkpoints (all flights and each window), same columns as Sagarika's file
- `data/ss5_summary.json` — state shares per checkpoint and the floor-at-21 outcomes
- `data/website_data.json` — counts plus a random sample of 1,000 flight paths (seed 42) for the site's dots
- `code/ss5_full.py` — the run (needs the DuckDB work file from `../jangkyu-full-dataset/code`)
