# When Should I Book?

An animated, full-screen scrollytelling data story about airfares — Georgia Tech
Data Visualization group project (Jet2 Holiday team).

**Story in one line:** you can't predict the cheapest day to buy a flight, but you can
predict the days it gets more expensive — so book before the 21-day mark.

## View it

- Live site (GitHub Pages): https://jangkyuju.github.io/jet2-holiday-viz/
- Screencast video (3 min): _link to be added_
- Or open `index.html` directly in a browser. D3 v7.8.5 is bundled in `lib/d3.min.js`, so
  the charts run offline; only the Google web fonts come from the internet (the page falls
  back to system fonts without them).

## Story and views

| Scene | View | Author | Interaction |
|---|---|---|---|
| Where to? | Destination map from ATL: route width and color = average fare | Arrington Goss | Pick a destination (or "Pick one for me") to print the ticket; the story continues only after a pick |
| Watching the fare | Daily fare diary of real flights on the chosen route | Cynthia Zhou | Scroll fills the diary day by day; hover a day; follow four other flights |
| Your call | Buy-now-or-wait quiz | — | Two-button choice |
| Fares jump | Staircase: all flights, same-flight fare index (60 days out = 100) | Cynthia Zhou | Diaries collapse into the line; the four jumps are annotated as the line draws; toggle index / average fare; hover |
| Every route | Route × window heatmap, sorted by each route's cheapest day | Jangkyu Ju | **Linked view:** click a route to redraw the staircase; toggle 15 ATL routes / all 234 routes |
| The bet | Alluvial of fare bands at five checkpoints + odds grid | Sagarika Srinivasan | **Innovative view:** 1,000 real flights flow as dots; hover ribbons; click a band to follow those flights |
| Book by | Calendar countdown + book-by date | — | Enter a departure date |
| One more check | Nonstop vs. connecting plane race | Yuhan Hu | Toggle all routes / your route; race again |

Every scene is a sticky full-screen stage; scroll progress drives its animation. Users with
"reduce motion" turned on get the final, static state of each scene.

Non-obvious features:
- **Two scroll gates.** The story pauses at the map until you pick a destination (or "Pick one
  for me"), and at "Your call" until you answer Buy now / Wait.
- **The picked destination carries through the story**: diary flights, quiz fare, the
  highlighted heatmap route, and "Your route" in the nonstop race.
- **Brushing:** drag across the staircase in "Every route" to pick any range of days; the
  heatmap's "your pick" column and the headline number update.
- **Progress cue:** the bar at the top and the "n / 11" label at the bottom left show where
  you are in the story and when it ends.
- Hover any square, line, route or ribbon for exact values.

## Changes after the think-aloud test (Nov 17)

| # | Tester comment | Change |
|---|---|---|
| 1 | Staircase y-axis unclear, no $ on the index | Axis label "Fare index (60 days out = 100)" / "Average fare (USD)" |
| 2 | Diary → staircase transition confusing | Chart title explains the merge while it happens |
| 3 | Text under "Zoom out" unnecessary; wanted hover | Shorter copy; hover hint in the panel footer |
| 4 | Quiz pop-up wording confusing | Plainer titles that state the odds |
| 5 | Unsure whether the map shows all airports | Map title: "the 15 destinations in our data" |
| 6 | Too much scrolling; "when do I stop?" | Progress bar + "n / 11" label; each scene about 12% shorter |
| 7 | Route heatmap overwhelming | Copy says how to read it (left to right, blue vs. red) |
| 8 | Wanted flight details in the diary; baseline instead of previous day | Row labels show airline and nonstop / 1+ stop; tooltip adds change vs. 60 days out |

## Data

Expedia Flight Prices (Kaggle, [`dilwong/flightprices`](https://www.kaggle.com/datasets/dilwong/flightprices)):
82.1M one-way fare quotes from 16 U.S. airports, searched Apr 16 – Oct 5, 2022 (31 GB, not in this repo).
Every chart uses real data. Cleaned tables for each visualization are in
[`clean_data/`](clean_data/), with the cleaning steps in [`clean_data/README.md`](clean_data/README.md).

| View | Data shown | Analysis folder |
|---|---|---|
| Where to? | Average fare from ATL to 15 airports, all dates | `submissions/Arrington_Visualizations/` |
| Watching the fare | Labor Day flights on 15 ATL routes; 82% "barely moved" from 16,182 flights tracked every day | `submissions/cynthia-cz01-cz03/`, `submissions/jangkyu-full-dataset/` |
| Fares jump | Fare by days out (82.1M quotes) and same-flight index (64.5M one-day pairs) | `submissions/jangkyu-full-dataset/` |
| Every route | Route-level index, window changes and cheapest day for 234 routes | `submissions/jangkyu-jk3/` |
| The bet | Floor / Middle / Jumped at 60, 30, 21, 14, 7 days out for 482,975 flights (Sagarika's method) | `submissions/Sagarika_Visualizations/`, `submissions/jangkyu-ss5-full/` |
| One more check | Nonstop vs. connecting medians over all dates, overall and within ATL routes (Yuhan's method) | `submissions/yuhan-q7/`, `submissions/jangkyu-full-dataset/` |

The map covers flights from Atlanta only, so the origin is fixed to ATL.

## Files

- `index.html` — the built site (this is what GitHub Pages serves)
- `lib/d3.min.js` — D3 v7.8.5 (library, not our code; ISC license)
- `src/index.src.html` — page source (HTML, CSS, and D3 code)
- `src/map-data.js` — pre-projected U.S. outline and airport positions (from `us-atlas`)
- `src/prepare_data.mjs` — collects the analysis outputs in `submissions/` into `src/site-data.js`
- `src/build.mjs` — inlines the map and site data into the page
- `clean_data/` — cleaned data by visualization
- `submissions/` — each member's analysis, data, and code

To rebuild after an analysis output changes (run from the repo root):

```bash
node src/prepare_data.mjs
node src/build.mjs src/index.src.html /tmp/artifact.html index.html src/map-data.js src/site-data.js
python clean_data/build_clean_data.py
```

## Team

Jangkyu Ju (lead), Sagarika Srinivasan, Cynthia Zhou, Arrington Goss, Yuhan Hu.
