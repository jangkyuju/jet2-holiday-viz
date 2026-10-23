# Jangkyu Ju — full-dataset analysis

Re-runs the team's analyses on the whole Expedia dataset (82.1M quotes, 6.0M flights, 235 routes,
searches Apr 16 – Oct 5, 2022), using the largest population each question allows:

| Question | Population |
|---|---|
| Fare level, seats left | every quote (82.1M) |
| Overnight rises / drops, fare index | every same-flight pair checked exactly one day apart (64.5M) |
| Following one flight for 60 days (diary shares, low-point timing, odds of waiting) | flights observed on every day they could have been searched (16,182; all depart Aug 25–31, 69% nonstop) |
| Nonstop vs. connecting, strictest | same route, same flight date, same search day (1.7M choices) |

## Key results

- **Staircase holds for all flights.** Same-flight index (60 days out = 100): 101.5 at 21 days, then
  +3.1% at 20, +7.6% at 13, +9.1% at 5 and +6.4% at 1 → 137.4. About 80% of the rise happens on those four nights.
  Every airline, origin, month and weekday shows the spikes (`data/jump_robustness.csv`).
- **82% of daily checks barely move** (<10%); 10.3% rise 10%+, 7.9% fall 10%+.
- **78% of flights hit their lowest fare more than 21 days out.** Waiting from 44 to 21 days out is a coin flip
  (45% cheaper, 32% pricier); waiting from 22 to 7 days out leaves 70% pricier.
- **Nonstop vs. connecting:** −38% pooled → −14% within route → −7% (nonstop cheaper 62% of the time) for the same choice.
- **Destinations:** Arrington's ATL means reproduce exactly; SFO beats OAK by a $145 median, LGA is usually the cheapest NYC airport.

## Files

- `data/` — result tables (`curve_by_days_out.csv` feeds the site's Steps chart; `cz_c3b_diary_shares.csv` feeds the 82%)
- `charts/` — before/after comparisons with each teammate's result
- `code/` — DuckDB scripts. They expect the Kaggle file converted to Parquet (`profile_dataset.py` does this once).
