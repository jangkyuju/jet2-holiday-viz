# Cynthia Zhou — CZ-01 Price Diary + CZ-03 The Staircase

**CZ-01 (Q2, Q15): what does checking a fare every day actually show you?**
**CZ-03 (Q1, Q2): does the median fare creep up or jump?**

## Files

- [Visualization](cz01_cz03.html): two linked views, open in a browser (works offline; keep `vendor/` next to it).
  Click a diary row to trace that flight on the staircase; drag across the staircase to narrow the diary; the period dropdown filters both.
- Screenshots: [default](screenshot_1_overview.png), [a flight picked](screenshot_2_linked.png), [days 21–7 brushed](screenshot_3_brushed.png), [interaction design](interaction_design.png).
- **Data (tables):**
  - [cz_staircase.csv](data/cz_staircase.csv): median / 25th / 75th percentile lowest fare and % of flights with 1–3 seats left, by period × days before departure (224 rows).
  - [cz_changes.csv](data/cz_changes.csv): % of fares that rose / fell 10%+ since the same flight's previous check, by period × day (218 rows, 11,318,332 checks).
  - [cz_diary.csv](data/cz_diary.csv): day-by-day lowest fare of 48 flights, 12 per period, one per route (2,393 rows).
  - [cz_site_diary.csv](data/cz_site_diary.csv): Labor Day, up to 8 flights per route for the site's diary scene (1872 flights on 234 routes).
- [Website data](website_data.json): the same numbers shaped for `src/index.src.html` (see below).
- [Verification](validation.json): the real export reproduces the Data Exploration figures (all checks pass).
- **Code:** [kaggle_export.py](code/kaggle_export.py) (Kaggle + DuckDB, 6 GB → CSVs), [build_charts.py](code/build_charts.py) (Python/Altair → the page), [make_submission.py](code/make_submission.py) (this folder).

## Definitions

Departure windows in 2022, inclusive: Memorial Day May 26–31; July 4 June 30–July 5; Labor Day September 1–6; Non-holiday June 9–14 and August 11–16 pooled — the same windows as Yuhan's Q7. Source: [Dillon Wong's Expedia Flight Prices](https://www.kaggle.com/datasets/dilwong/flightprices).

A fare is the lowest total fare for a flight (legId) on a search day. A change compares it with the same flight's previous search; gaps over 3 days are not compared. "Rose/fell 10%+" means the new fare is at least 10% above/below the previous one. Seats remaining of 0 is treated as missing. Diary flights are picked by rule (densest daily coverage first), not by hand.

## Swapping the real data into the site

`website_data.json` has two keys made for `src/index.src.html`:

**`KP` (CZ-03 staircase)** — same shape as the placeholder constant: `{ lab, jul, mem, non }`, each a list of `[daysBefore, medianFare]`, one point per day from 60 (Memorial Day: 44) to 1. `holidayCurve()` works unchanged:

```js
const KP = WEBSITE_DATA.KP;
```

**`SITE_DIARY` (CZ-01 diary)** — real Labor Day flights keyed by route `"ATL-BOS"`. A drop-in for `diaryRows()` that returns the same `{ name, days: [{ d, fare, ch, cls }] }` rows:

```js
const CLS = { r: 'rose', f: 'fell', '.': 'flat', ' ': 'flat', '-': 'none' };
function diaryRowsReal(origin, dest, page = 0, n = 4) {
  const list = WEBSITE_DATA.SITE_DIARY[`${origin}-${dest}`];
  if (!list || !list.length) return null;               // caller falls back to diaryRows()
  const start = (page * n) % list.length;
  return d3.range(Math.min(n, list.length)).map(k => {
    const i = (start + k) % list.length, fl = list[i];
    const days = fl.f.map((fare, j) => {
      const c = fl.c[j], prev = j ? fl.f[j - 1] : fare;
      return { d: 60 - j, fare, ch: (c === 'r' || c === 'f' || c === '.') ? fare / prev - 1 : 0, cls: CLS[c] };
    });
    return { name: `Flight ${i + 1}`, airline: fl.a, days };
  });
}
// in buildWatching():
// watch.flights = diaryRowsReal(state.origin, state.dest, state.diarySeed - 1)
//              || diaryRows(hash(state.origin + state.dest) + state.diarySeed * 9973, 4, base);
```

`cls: 'none'` (a morning with no check) draws as an empty cell with no outline. 234 of 234 routes have at least four flights.

**Copy on the site.** The staircase text says the Labor Day fare "bottoms out at $258 fourteen days before departure, then jumps $26 overnight". The real data matches it, so the text can stay.
