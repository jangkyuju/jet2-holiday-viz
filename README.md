# When Should We Book?

An animated, full-screen scrollytelling data story about airfares — Georgia Tech
Data Visualization group project (Jet2 Holiday team).

**Story in one line:** you can't predict the cheapest day to buy a flight, but you can
predict the days it gets more expensive — so book before the 21-day mark.

## View it

- Live site (GitHub Pages): https://jangkyuju.github.io/jet2-holiday-viz/
- Or open `index.html` directly in a browser. It loads D3 and fonts from the web; the
  submission zip includes a local copy of D3 so it also runs offline.

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

- `index.html` — the built site (single file; this is what GitHub Pages serves)
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
