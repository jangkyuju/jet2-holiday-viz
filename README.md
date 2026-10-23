# When Should We Book?

An animated, full-screen scrollytelling data story about holiday airfares — Georgia Tech
Data Visualization group project (Jet2 Holiday team).

**Story in one line:** you can't predict the cheapest day to buy a flight, but you can
predict the days it gets more expensive — so book before the 21-day mark.

## View it

- Live site (GitHub Pages): https://jangkyuju.github.io/jet2-holiday-viz/
- Or open `index.html` directly in a browser (needs internet for the fonts and the D3 CDN).

## Story and views

| Scene | View | Sketch | Interaction |
|---|---|---|---|
| Where to? | Destination fare map | AG01 | Pick an origin, click a destination to fly there |
| Watching the fare | Daily fare diary | CZ-01 | Scroll fills the diary day by day; hover for fares |
| Your call | Buy-now-or-wait quiz | — | Two-button choice |
| Fares jump | Median-fare staircase | CZ-03 | Diaries collapse into the line; holiday tabs; hover |
| Every route | Route × window heatmap | JK3 | **Linked view:** click a route to redraw the staircase |
| The bet | Alluvial of fare bands + odds grid | SS5 | **Innovative view:** 1,000 flight dots flow; hover ribbons, click a band to follow it |
| Book by | Calendar countdown + book-by date | CZ-09 | Enter a departure date |
| Nonstop vs connecting | Plane race / bars | YH-02 | Holiday tabs, race again |

Every scene is a sticky full-screen stage; scroll progress drives its animation. Users with
"reduce motion" turned on get the final, static state of each scene.

## Files

- `index.html` — the built site (single file; this is what GitHub Pages serves)
- `src/index.src.html` — page source (HTML, CSS, and D3 code)
- `src/map-data.js` — pre-projected U.S. outline and airport positions (from `us-atlas`)
- `src/prepare_data.mjs` — collects the team's `submissions/` into `src/site-data.js`
- `src/build.mjs` — inlines the map and site data into the page
- `submissions/` — each member's analysis, data, and code

To rebuild after a submission changes (run from the repo root):

```bash
node src/prepare_data.mjs
node src/build.mjs src/index.src.html /tmp/artifact.html index.html src/map-data.js src/site-data.js
```

## Data

Expedia Flight Prices (Kaggle, `dilwong/flightprices`): one-way fares searched
Apr 16 – Oct 5, 2022 for Memorial Day, July 4, Labor Day, and a non-holiday baseline.

| View | Status | Source |
|---|---|---|
| AG01 map | Real: average fare from ATL to 15 airports | `submissions/Arrington_Visualizations/atl_airport_fares.csv` |
| CZ-01 diary | Real: Labor Day flights, 15 ATL routes | `submissions/cynthia-cz01-cz03/website_data.json` (`SITE_DIARY`) |
| CZ-03 staircase | Real: median lowest fare by day, 4 periods | same file (`KP`) |
| YH-02 nonstop race | Real: overall and same-route medians | `submissions/yuhan-q7/Q7_website_data.json` |
| JK3 route rows | Placeholder (All-routes row is real) | `ROUTES` in `src/index.src.html` |
| SS5 fare-band flows | Placeholder | `FLIGHTS` in `src/index.src.html` |

The map currently covers flights from Atlanta only, so the origin is fixed to ATL.

## Team

Jangkyu Ju (lead), Sagarika Srinivasan, Cynthia Zhou, Arrington Goss, Yuhan Hu.
