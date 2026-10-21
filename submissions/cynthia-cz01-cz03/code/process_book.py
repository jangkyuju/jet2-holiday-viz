"""
Writes docs/process_book_section.md: Cynthia's paste-ready section for the
"Prototype Phase 1 & 2" chapter of the process book.

Every number in it is computed from the same CSVs the charts are drawn from, so
re-running the build after the real Kaggle export keeps text and figures in
step. While the build is on placeholder data, the file says so at the top and
marks each number that will change.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def write(out: Path, *, stats: dict, anno: pd.DataFrame, diary: pd.DataFrame,
          stair: pd.DataFrame, chg: pd.DataFrame, using_real: bool,
          cutoff_note) -> None:
    mark = "" if using_real else " ⟨placeholder⟩"

    def n(x, fmt="{:,.0f}"):
        return fmt.format(x) + mark

    def pct(x):
        return f"{x:.0f}%{mark}"

    lab = anno[anno.period == "Labor Day"].set_index("kind")
    floor, jump, last = (lab.loc[k] if k in lab.index else None for k in ("floor", "jump", "last"))
    per_flight = diary.groupby("legId").size()
    flights = diary.groupby("period")["legId"].nunique()
    worst = (f"{pct(stats['worst_rise_val'])} of fares rose 10% or more on the worst single "
             f"morning ({stats['worst_rise_period']}, {stats['worst_rise_day']} days out"
             f"{cutoff_note(stats['worst_rise_day'])})")

    head = "" if using_real else (
        "> **DRAFT ON PLACEHOLDER DATA.** Numbers marked ⟨placeholder⟩ come from "
        "`data/sample/`. Run `src/kaggle_export.py` on Kaggle, put the three CSVs in "
        "`data/`, run `src/build_charts.py` again, and this file is rewritten with the "
        "real numbers and the marks disappear. Do not paste this version.\n\n")

    labor_line = ""
    if floor is not None and last is not None:
        labor_line = (
            f"For Labor Day the median lowest fare bottoms out at {n(floor.median_fare, '${:,.0f}')} "
            f"{int(floor.daysBefore)} days before departure"
            + (f", jumps {pct(jump.pct)} overnight to {n(jump.median_fare, '${:,.0f}')} "
               f"at {int(jump.daysBefore)} days" if jump is not None else "")
            + f", and reaches {n(last.median_fare, '${:,.0f}')} the day before departure, "
              f"{pct((last.median_fare / floor.median_fare - 1) * 100)} above the floor. ")

    text = f"""{head}# Prototype Phase 1 & 2 (Weeks 8–9)

## Cynthia Zhou — CZ-01 Price Diary + CZ-03 The Staircase (two linked views)

**Status: complete and polished.** This is the first finished visualization in our
prototype. It is built in Python with Altair and rendered in the browser as
Vega-Lite 6, so it runs from one HTML file and drops into the team site as one
`<div>` plus a JSON spec. It covers two of the final-project requirements on its
own: an innovative view (CZ-01) and a linked interaction between two views
(CZ-01 ↔ CZ-03).

[Insert build/screenshot_1_overview.png]
*Figure 1. Default state: Labor Day, nothing picked.*

[Insert build/screenshot_2_linked.png]
*Figure 2. A flight is picked in the diary; its own fare is traced on the staircase.*

[Insert build/screenshot_3_brushed.png]
*Figure 3. Days 21 to 7 are brushed on the staircase; the diary keeps only those columns.*

### Data cleaning

Clean data: [LINK TO THE THREE CSVs — Google Drive folder]

The Expedia file (`dilwong/flightprices` on Kaggle, about 6 GB) is too large to ship,
so it is reduced in a Kaggle notebook with DuckDB (`src/kaggle_export.py`):

1. Keep the five flight-date windows the team has used since Data Exploration:
   Memorial Day (May 26–31), July 4 (Jun 30–Jul 5), Labor Day (Sep 1–6), and two
   ordinary weeks as a baseline (Jun 9–14, Aug 11–16).
2. Collapse to one row per flight per search day: the lowest total fare, and the
   seats remaining at that fare (a value of 0 is treated as missing).
3. Compare each row with the same flight's previous search. Gaps over 3 days are
   dropped, so every "change" is a day-to-day change.
4. Write three small files:
   - `cz_staircase.csv` — median, 25th and 75th percentile lowest fare and the share
     of flights with 1–3 seats left, by period and days before departure
     ({n(len(stair))} rows).
   - `cz_changes.csv` — share of fares that rose or fell 10% or more since the
     previous check, by period and day ({n(len(chg))} rows, from
     {n(stats['n_checks'])} same-flight checks).
   - `cz_diary.csv` — the day-by-day fare of {n(diary.legId.nunique())} individual
     flights ({n(len(diary))} rows).

The diary flights are chosen by a rule, not by hand: in each period, the 12 most
densely observed flights, one per route, that were still listed within a week of
departure. Each was checked on {n(per_flight.min())} to {n(per_flight.max())} separate
mornings. Memorial Day has {n(flights.get('Memorial Day', 0))} flights and a shorter
diary because the searches only start on April 16, 44 days before it.

### Where it sits in the story

The two views are the first two beats of our arc. **CZ-01 is the hook:** it shows
what fare-watching actually feels like. {pct(stats['pct_flat'])} of mornings the fare
barely moved, {pct(stats['pct_rise'])} of mornings it rose 10% or more, and
{pct(stats['pct_drop'])} of mornings it fell 10% or more. The diary is a grey field
with scattered colour, which is the point: a traveller refreshing a fare has
nothing to react to on most days.

**CZ-03 is the second rising insight** (prices move in steps). {labor_line}The steps
sit next to the 21-, 14- and 7-day advance-purchase cutoffs, and {worst}. That sets up
JK3 (the same late rise on every route) and SS5 (the odds a traveller faces if they
wait), which come next in our sequence.

### Innovative view design — CZ-01, the price diary

**What is new about it.** Every other fare-over-time chart we sketched (JK1, AG08, my
own Data Exploration Chart 1) averages thousands of flights into one smooth line.
Nobody books the average. The diary shows individual flights unaveraged, one cell
per morning, so the reader sees the experience of watching a fare before seeing the
statistic. It works like a calendar heatmap crossed with small multiples, and it is
tied to the aggregate view below it so the reader can move between one flight and
all of them.

**Encoding.**

| Channel | Encodes | Notes |
|---|---|---|
| Row | one flight (labelled with its route) | sorted A–Z so a reader can find their route |
| Column | days before departure, 60 on the left, 0 on the right | same x-scale as CZ-03, so a diary column sits directly above the same day on the staircase |
| Colour | change since the previous morning: fell 10%+ / barely moved / rose 10%+ | diverging blue–grey–red; same 10% threshold as Chart 2 so the counts agree |
| Opacity | selection state | picked row and brushed days stay at 100% |
| Ring | the picked flight | so identity never depends on opacity alone |

**What changed from the sketch, and why.**

- *One row became twelve per period.* A single row could be dismissed as one
  unlucky flight. Twelve flights on twelve routes show the grey field is normal.
- *Three classes, not a continuous colour scale.* A continuous scale invites
  readers to study 2% wiggles. The message is "did anything happen that you could
  act on", which is a yes/no question per morning.
- *Blue for falls, red for rises, grey for neither.* Two hues that read as opposite
  with a neutral middle. The pair passes a colour-vision-deficiency check
  (the course palette's validator), and the legend and table view carry the
  same information without colour.
- *It got a partner.* The sketch stood alone. Linking it to CZ-03 means the reader
  can always ask "and what did the average do that day?"

**Alternatives we considered.** A sparkline per flight shows the size of each move
but loses the "nothing happened today" reading. A horizon chart per flight is
compact but too hard for a general audience, which is who we are designing for.
One averaged diary row would lose the point of the view.

### Interaction design

[Insert build/interaction_design.png]
*Figure 4. Interaction design. One filter scopes both views; two links run between
them, one in each direction.*

1. **Travel-period dropdown (filter, above both views).** Both views redraw for the
   period. The staircase's y-range re-pins to that period's band, and stays put
   while you click flights.
2. **Click a diary row (link CZ-01 → CZ-03).** The row gets a ring and the other rows
   dim. That flight's own fare is drawn on the staircase as a thin line whose dots
   carry the diary's red/blue/grey coding, labelled with its route. You see one
   traveller's jagged path against the median on one pair of axes.
3. **Drag across the staircase (link CZ-03 → CZ-01).** Diary cells outside the dragged
   days fade. Because the two views share one x-scale, the brushed window and the
   surviving diary columns line up vertically. Brushing 21 to 7 days shows where the
   red cells cluster.
4. **Hover.** A diary cell shows route, airline, search date, fare, % change and seats
   left. The staircase shows a crosshair with the median, the middle half of fares
   and the share of flights with 1–3 seats left.
5. **Double-click** clears the pick and the brush.
6. **Dark/light toggle.** The dark version uses its own palette steps checked
   against the dark background, not an inverted copy.

Accessibility: both views have a table view underneath (every value readable as
text), the three change classes have a legend, and the picked flight is marked by
a ring and a route label, not by colour alone.

### How to run it

Open `build/cz01_cz03.html` in a browser. The Vega libraries are in `build/vendor/`,
so it works offline. To rebuild from the data:
`.venv/bin/python src/build_charts.py`.

### Next steps

- Put the view into the team's scrolling page as the opening section.
- Hand the picked-flight state to SS5 so the odds view can start from the flight
  the reader chose.
- Possibly add CZ-07 (share of fares jumping 10%+ by day, with the cutoffs marked)
  as a third view linked to the same brush.
"""
    out.parent.mkdir(exist_ok=True)
    out.write_text(text)
