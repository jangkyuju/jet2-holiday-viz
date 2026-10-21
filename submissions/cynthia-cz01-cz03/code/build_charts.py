"""
Jet 2 Holiday — CZ-01 "Price Diary" + CZ-03 "The Staircase", two linked views.
Cynthia Zhou.

Python (Altair) -> Vega-Lite -> a self-contained HTML page. Run:

    ./.venv/bin/python src/build_charts.py

Reads data/cz_{diary,staircase,changes}.csv (the real Kaggle export). If those
are missing it falls back to data/sample/ and stamps a visible PLACEHOLDER
banner on the page, so a stand-in can never be mistaken for the real thing.

Writes into build/:
    cz01_cz03.html          the click-and-run page (data inlined, no server)
    cz01_cz03.light.vg.json the Vega-Lite spec, for embedding in the team site
    cz01_cz03.dark.vg.json  the same spec stepped for a dark surface
    screenshot_1_overview.png / screenshot_2_linked.png   for the process book
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import altair as alt
import pandas as pd

alt.data_transformers.disable_max_rows()

ROOT = Path(__file__).resolve().parent.parent
DATA, SAMPLE, BUILD = ROOT / "data", ROOT / "data" / "sample", ROOT / "build"
BUILD.mkdir(exist_ok=True)

FILES = ["cz_diary.csv", "cz_staircase.csv", "cz_changes.csv"]
USING_REAL = all((DATA / f).exists() for f in FILES)
SRC = DATA if USING_REAL else SAMPLE
if not all((SRC / f).exists() for f in FILES):
    raise SystemExit(
        f"Missing data. Expected {FILES} in {DATA} (real) or {SAMPLE} (placeholder).\n"
        "Run src/make_sample_data.py for placeholders, or follow src/kaggle_export.py."
    )
print(f"data source: {SRC}  ({'REAL' if USING_REAL else 'PLACEHOLDER'})")

# --------------------------------------------------------------------- theme --
# Roles, not raw hex, everywhere below. Values from the course palette: the
# diary is a 3-class DIVERGING encoding (blue <-> red, neutral gray midpoint);
# nothing else on the page spends a hue, so there is no third categorical slot
# to get confused with. Validated with validate_palette.js: red/blue/aqua pass
# every all-pairs check in both modes.
THEMES = {
    "light": dict(
        surface="#fcfcfb", plane="#f9f9f7",
        ink="#0b0b0b", ink2="#52514e", muted="#898781",
        grid="#e1e0d9", axis="#c3c2b7", band="#ebeae3",
        rose="#e34948", fell="#2a78d6", flat="#f0efec",
    ),
    "dark": dict(
        surface="#1a1a19", plane="#0d0d0d",
        ink="#f0efec", ink2="#c3c2b7", muted="#898781",
        grid="#2c2c2a", axis="#383835", band="#232322",
        rose="#e66767", fell="#3987e5", flat="#383835",
    ),
}

ROSE = "Rose 10%+"
FELL = "Fell 10%+"
FLAT = "Barely moved"
CLASS_ORDER = [FELL, FLAT, ROSE]          # diverging: cool pole -> neutral -> warm pole
PERIODS = ["Labor Day", "July 4", "Memorial Day", "Non-holiday"]
CUTOFFS = [21, 14, 7]                      # advance-purchase cutoffs
X_DOMAIN = [-0.6, 60.6]
PLOT_W = 760

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


# ---------------------------------------------------------------------- data --
def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    diary = pd.read_csv(SRC / "cz_diary.csv")
    stair = pd.read_csv(SRC / "cz_staircase.csv")
    chg = pd.read_csv(SRC / "cz_changes.csv")

    # 3-class change state. The 10% threshold is the one already used in the
    # process book's Chart 2, so the diary and that chart count the same events.
    def classify(p):
        if pd.isna(p):
            return None
        if p >= 10:
            return ROSE
        if p <= -10:
            return FELL
        return FLAT

    diary["change_class"] = diary["pct_change"].map(classify)
    # Expedia joins multi-leg carriers with "||" ("Delta||Delta"); show each carrier once
    diary["airline"] = diary["airline"].fillna("").astype(str).map(
        lambda a: " + ".join(dict.fromkeys(x.strip() for x in a.split("||") if x.strip())) or "Unknown")
    # inset the cell by 0.06 of a day on each side -> a surface gap, not a border
    diary["dLo"] = diary["daysBefore"] - 0.44
    diary["dHi"] = diary["daysBefore"] + 0.44
    diary["row_label"] = diary["route"]
    diary["is_first"] = diary["daysBefore"] == diary.groupby("legId")["daysBefore"].transform("max")
    diary = diary[diary["daysBefore"].between(0, 60)]

    stair = stair[stair["daysBefore"].between(0, 60)].copy()
    stair["is_first"] = stair["daysBefore"] == stair.groupby("period")["daysBefore"].transform("max")
    chg = chg[chg["daysBefore"].between(0, 60)].copy()
    return diary, stair, chg


def annotations(stair: pd.DataFrame) -> pd.DataFrame:
    """Three data-driven callouts per period, using the same rule as the team
    site's annotate(): the floor is the last day (closest to departure) on which
    the whole-dollar median sits at its minimum; the jump is the first overnight
    rise of 3% or more after it; the end is the day before departure. All read
    off the data, so they stay right whatever CSVs are loaded."""
    out = []
    for period, g in stair[stair["daysBefore"].between(1, 60)].groupby("period"):
        g = g.sort_values("daysBefore", ascending=False).reset_index(drop=True)
        whole = g["median_fare"].round()
        floor = g[whole == whole.min()].iloc[-1]
        last = g.iloc[-1]
        out.append(dict(period=period, kind="floor", daysBefore=int(floor["daysBefore"]),
                        median_fare=float(floor["median_fare"]),
                        label=f"floor ${floor['median_fare']:.0f}, {int(floor['daysBefore'])} days out"))
        after = g[g["daysBefore"] < floor["daysBefore"]]
        prev = float(floor["median_fare"])
        for r in after.itertuples():
            if r.median_fare / prev - 1 >= 0.03 and r.daysBefore != last["daysBefore"]:
                pct = (r.median_fare / prev - 1) * 100
                out.append(dict(period=period, kind="jump", daysBefore=int(r.daysBefore),
                                median_fare=float(r.median_fare), pct=float(pct),
                                label=f"+{pct:.0f}% overnight → ${r.median_fare:.0f}"))
                break
            prev = float(r.median_fare)
        rise = (last["median_fare"] / floor["median_fare"] - 1) * 100
        out.append(dict(period=period, kind="last", daysBefore=int(last["daysBefore"]),
                        median_fare=float(last["median_fare"]),
                        label=f"${last['median_fare']:.0f} the day before · +{rise:.0f}% above the floor"))
    return pd.DataFrame(out)


def headline_stats(chg: pd.DataFrame) -> dict:
    """Numbers for the stat tiles; weighted by number of checks, not by day."""
    w = chg["n"]
    return dict(
        pct_rise=(chg["pct_rise"] * w).sum() / w.sum(),
        pct_drop=(chg["pct_drop"] * w).sum() / w.sum(),
        pct_flat=(chg["pct_flat"] * w).sum() / w.sum(),
        n_checks=int(w.sum()),
        worst_rise_day=int(chg.loc[chg["pct_rise"].idxmax(), "daysBefore"]),
        worst_rise_val=float(chg["pct_rise"].max()),
        worst_rise_period=str(chg.loc[chg["pct_rise"].idxmax(), "period"]),
    )


def cutoff_note(day: int) -> str:
    """Say 'just past the N-day cutoff' only when the data actually puts it there."""
    for c in CUTOFFS:
        if 0 < c - day <= 2:
            return f", just past the {c}-day cutoff"
    return ""


# --------------------------------------------------------------------- chart --
def build(diary: pd.DataFrame, stair: pd.DataFrame, anno: pd.DataFrame,
          mode: str, preselect: str | None = None,
          prebrush: tuple[int, int] | None = None) -> alt.ConcatChart:
    t = THEMES[mode]
    # The y-range is fixed per travel period, from that period's middle-half band.
    # It follows the dropdown but never moves when a flight is clicked, so the
    # staircase holds still while you compare flights against it. A picked
    # flight that leaves the band is clamped to the edge; its tooltip keeps the
    # true fare.
    def rng_for(g):
        lo, hi = g["p25_fare"].min(), g["p75_fare"].max()
        pad = (hi - lo) * 0.08
        return [float((lo - pad) // 25 * 25), float(((hi + pad) // 25 + 1) * 25)]
    ranges = {p: rng_for(g) for p, g in stair.groupby("period")}
    expr = " : ".join(f"periodSel === '{p}' ? {r}" for p, r in ranges.items())
    y_domain = alt.ExprRef(expr=f"{expr} : {next(iter(ranges.values()))}")

    color = alt.Color(
        "change_class:N",
        scale=alt.Scale(domain=CLASS_ORDER, range=[t["fell"], t["flat"], t["rose"]]),
        legend=alt.Legend(title="Change since the previous day's check",
                          orient="none", legendX=0, legendY=-32, direction="horizontal",
                          titleLimit=320, symbolType="square", symbolSize=170,
                          titleOrient="left", titlePadding=10),
    )
    x_shared = alt.Scale(domain=X_DOMAIN, reverse=True, nice=False, zero=False)

    # a bound dropdown, placed above both views: one filter row, one slice
    period = alt.param(
        name="periodSel", value="Labor Day",
        bind=alt.binding_select(options=PERIODS, name="Travel period", element="#period-filter"),
    )
    IN_PERIOD = "datum.period === periodSel"

    # Two params on the same click so the overlay can require a pick (empty=False)
    # while the dimming treats "nothing picked" as "show everything" (empty=True).
    pick_args = dict(fields=["legId"], on="click", clear="dblclick", toggle=False)
    value = [{"legId": preselect}] if preselect else alt.Undefined
    dim = alt.selection_point(name="dim", empty=True, value=value, **pick_args)
    pick = alt.selection_point(name="pick", empty=False, value=value, **pick_args)
    window = alt.selection_interval(name="window", encodings=["x"],
                                    value={"x": list(prebrush)} if prebrush else alt.Undefined,
                                    mark=alt.BrushConfig(fill=t["ink2"], fillOpacity=0.08,
                                                         stroke=t["ink2"], strokeWidth=1))

    # ---------------------------------------------------- CZ-01 price diary ---
    diary_base = (alt.Chart(diary).transform_filter(IN_PERIOD)
                  .add_params(period, dim, pick))
    # one definition of each positional channel, reused by every diary layer --
    # a layer that redeclares the axis as None would wipe the shared axis.
    X_DIARY = alt.X("dLo:Q", scale=x_shared, title=None,
                    axis=alt.Axis(grid=False, labels=False, ticks=False, domain=False))
    Y_DIARY = alt.Y("row_label:N", sort="ascending", title=None,
                    scale=alt.Scale(paddingInner=0.22),
                    axis=alt.Axis(domain=False, ticks=False, labelFontSize=11,
                                  labelColor=t["ink2"], labelPadding=8, labelLimit=90))
    cells = diary_base.mark_rect().encode(
        x=X_DIARY, x2="dHi:Q", y=Y_DIARY,
        color=color,
        opacity=(alt.when(dim, window).then(alt.value(1.0))
                 .when(window).then(alt.value(0.34))
                 .otherwise(alt.value(0.10))),
        tooltip=[
            alt.Tooltip("route:N", title="Route"),
            alt.Tooltip("airline:N", title="Airline"),
            alt.Tooltip("searchDate:N", title="Checked on"),
            alt.Tooltip("daysBefore:Q", title="Days before departure"),
            alt.Tooltip("minFare:Q", title="Lowest fare", format="$,.0f"),
            alt.Tooltip("pct_change:Q", title="Change vs. last check", format="+.1f"),
            alt.Tooltip("change_class:N", title="Counted as"),
            alt.Tooltip("seatsAtMinFare:Q", title="Seats left at that fare"),
        ],
    )
    # a hairline ring marks the row you picked, so identity is not opacity-only
    picked_row = (diary_base.transform_filter(pick)
                  .transform_aggregate(n="count()", groupby=["legId", "row_label"])).mark_rect(
        fill=None, stroke=t["ink"], strokeWidth=1.4, cornerRadius=2,
    ).encode(x=alt.value(0), x2=alt.value(PLOT_W), y=Y_DIARY)

    diary_chart = (alt.layer(cells, picked_row)
                   .properties(width=PLOT_W, height=alt.Step(16),
                               title=alt.Title(
                                   "CZ-01 · The price diary — one row is one real flight, one cell is one morning you checked",
                                   subtitle=["Almost every cell is grey: on a typical morning the fare you are watching barely moves.",
                                             "Click a row to follow that flight on the chart below. Drag across the chart below to narrow",
                                             "the diary to a booking window. Double-click anywhere to clear."],
                                   anchor="start", fontSize=15, subtitleFontSize=11.5,
                                   color=t["ink"], subtitleColor=t["muted"], offset=50)))

    # ------------------------------------------------- CZ-03 the staircase ---
    stair_base = alt.Chart(stair).transform_filter(IN_PERIOD)
    x_stair = alt.X("daysBefore:Q", scale=x_shared,
                    title="Days before departure            (departure day at the right edge)",
                    axis=alt.Axis(values=[60, 50, 40, 30, 21, 14, 7, 0], grid=False,
                                  labelFontSize=11, labelColor=t["ink2"],
                                  titleFontSize=11.5, titleColor=t["muted"],
                                  titleFontWeight="normal", domainColor=t["axis"],
                                  tickColor=t["axis"]))
    y_fare = alt.Y("median_fare:Q", title="Lowest fare (USD)",
                   scale=alt.Scale(domain=y_domain, zero=False, nice=False, clamp=True),
                   axis=alt.Axis(format="$,.0f", grid=True, gridColor=t["grid"],
                                 domain=False, ticks=False,
                                 labelFontSize=11, labelColor=t["ink2"],
                                 titleFontSize=11.5, titleColor=t["muted"],
                                 titleFontWeight="normal"))

    iqr = stair_base.mark_area(color=t["band"], interpolate="step-after", line=False).encode(
        x=x_stair, y=alt.Y("p25_fare:Q", title=None), y2="p75_fare:Q")
    cutoff_rules = (alt.Chart(pd.DataFrame({"d": CUTOFFS})).mark_rule(
        color=t["muted"], strokeWidth=1, opacity=0.55)
        .encode(x=alt.X("d:Q", scale=x_shared, title=None, axis=None)))
    cutoff_text = (alt.Chart(pd.DataFrame({"d": CUTOFFS, "lab": [f"{d}-day cutoff" for d in CUTOFFS]}))
                   .mark_text(align="right", baseline="top", dx=-4, dy=4, fontSize=9.5,
                              color=t["muted"], angle=0, font=FONT)
                   .encode(x=alt.X("d:Q", scale=x_shared, title=None, axis=None),
                           y=alt.value(4), text="lab:N"))
    median_label = (stair_base.transform_filter("datum.is_first")
                    .mark_text(align="left", dx=4, dy=-12, fontSize=10.5, font=FONT,
                               color=t["ink2"], fontWeight="bold")
                    .encode(x=x_stair, y=y_fare, text=alt.value("median of all flights")))
    median_line = stair_base.mark_line(
        color=t["ink2"], strokeWidth=2.4, interpolate="step-after").encode(x=x_stair, y=y_fare)

    # nearest-point crosshair: a value is readable without a tooltip too
    hover = alt.selection_point(name="hover", on="pointerover", nearest=True,
                                encodings=["x"], empty=False, clear="pointerout")
    hover_rule = stair_base.mark_rule(color=t["axis"], strokeWidth=1).encode(
        x=x_stair, opacity=alt.when(hover).then(alt.value(0.9)).otherwise(alt.value(0))
    ).add_params(hover)
    hover_dot = stair_base.mark_point(filled=True, size=70, color=t["ink2"],
                                      stroke=t["surface"], strokeWidth=2).encode(
        x=x_stair, y=y_fare,
        opacity=alt.when(hover).then(alt.value(1)).otherwise(alt.value(0)),
        tooltip=[alt.Tooltip("daysBefore:Q", title="Days before departure"),
                 alt.Tooltip("median_fare:Q", title="Median lowest fare", format="$,.0f"),
                 alt.Tooltip("p25_fare:Q", title="25th percentile", format="$,.0f"),
                 alt.Tooltip("p75_fare:Q", title="75th percentile", format="$,.0f"),
                 alt.Tooltip("pct_low_seats:Q", title="% of flights with 1-3 seats left", format=".0f"),
                 alt.Tooltip("n_flights:Q", title="Flights observed", format=",")])

    anno_base = alt.Chart(anno).transform_filter(IN_PERIOD)
    anno_dot = anno_base.mark_point(filled=True, size=58, color=t["ink"],
                                    stroke=t["surface"], strokeWidth=2).encode(
        x=alt.X("daysBefore:Q", scale=x_shared, title=None, axis=None), y="median_fare:Q")
    # dx/dy/align are mark properties, not encoding channels, so each callout
    # placement is its own thin layer. The last-day label points inward so the
    # view bounds stay equal to the diary's and the two plots keep aligning.
    def anno_layer(kind: str, **mark):
        base = (anno_base.transform_filter(f"datum.kind === '{kind}'")
                .encode(x=alt.X("daysBefore:Q", scale=x_shared, title=None, axis=None),
                        y=alt.Y("median_fare:Q", title=None), text="label:N"))
        style = dict(fontSize=10.5, font=FONT, fontWeight="bold", **mark)
        # a surface-coloured halo underneath keeps the label legible when a
        # picked flight's line runs through it
        halo = base.mark_text(color=t["surface"], stroke=t["surface"],
                              strokeWidth=4, strokeJoin="round", **style)
        return alt.layer(halo, base.mark_text(color=t["ink"], **style))

    anno_floor = anno_layer("floor", align="right", dx=-9, dy=19)
    anno_jump = anno_layer("jump", align="right", dx=-9, dy=-15)
    anno_last = anno_layer("last", align="right", dx=-9, dy=-28)

    # ------- the link: the one flight you picked, drawn against the median ----
    sel_line = (alt.Chart(diary).transform_filter(IN_PERIOD).transform_filter(pick)
                .mark_line(color=t["ink"], strokeWidth=1.5, interpolate="step-after",
                           opacity=0.9)
                .encode(x=alt.X("daysBefore:Q", scale=x_shared, title=None, axis=None),
                        y=alt.Y("minFare:Q", title=None)))
    sel_pts = (alt.Chart(diary).transform_filter(IN_PERIOD).transform_filter(pick)
               .mark_point(filled=True, size=46, stroke=t["surface"], strokeWidth=1.5)
               .encode(x=alt.X("daysBefore:Q", scale=x_shared, title=None, axis=None),
                       y=alt.Y("minFare:Q", title=None), color=color,
                       tooltip=[alt.Tooltip("route:N", title="Route"),
                                alt.Tooltip("daysBefore:Q", title="Days before departure"),
                                alt.Tooltip("minFare:Q", title="Lowest fare", format="$,.0f"),
                                alt.Tooltip("pct_change:Q", title="Change vs. last check", format="+.1f")]))
    sel_label = (alt.Chart(diary).transform_filter(IN_PERIOD).transform_filter(pick)
                 .transform_filter("datum.is_first")
                 .mark_text(align="left", dx=6, dy=17, fontSize=10.5, font=FONT,
                            fontWeight="bold", color=t["ink"])
                 .encode(x=alt.X("daysBefore:Q", scale=x_shared, title=None, axis=None),
                         y=alt.Y("minFare:Q", title=None),
                         text=alt.Text("route:N")))

    # labels after the picked flight, so its line and dots never cover them
    stair_chart = (alt.layer(iqr, cutoff_rules, cutoff_text, median_line,
                             sel_line, sel_pts, median_label, sel_label,
                             anno_dot, anno_floor, anno_jump, anno_last,
                             hover_rule, hover_dot)
                   .add_params(window)
                   .resolve_scale(y="shared")
                   .properties(width=PLOT_W, height=300,
                               title=alt.Title(
                                   "CZ-03 · The staircase — the median lowest fare holds, then jumps",
                                   subtitle=["Shaded band = the middle half of fares. Thick line = the median.",
                                             "Thin line with dots = the one flight you picked above, each dot coloured by that morning's move.",
                                             "Vertical hairlines = the 21-, 14- and 7-day advance-purchase cutoffs."],
                                   anchor="start", fontSize=15, subtitleFontSize=11.5,
                                   color=t["ink"], subtitleColor=t["muted"], offset=10)))

    return (alt.concat(diary_chart, stair_chart, columns=1, align={"row": "none", "column": "all"}, spacing=30)
            .configure(font=FONT, background=t["surface"])
            .configure_view(stroke=None)
            .configure_axis(labelFont=FONT, titleFont=FONT)
            .configure_legend(labelFont=FONT, titleFont=FONT, labelFontSize=11,
                              titleFontSize=11, labelColor=t["ink2"], titleColor=t["muted"])
            .configure_title(font=FONT, subtitleFont=FONT)
            .configure_concat(spacing=30))


# ---------------------------------------------------------------- html page --
def table_view(stair: pd.DataFrame, diary: pd.DataFrame) -> str:
    """The WCAG-clean twin: every encoded value is also readable as text."""
    s = stair.sort_values(["period", "daysBefore"], ascending=[True, False])
    rows = "\n".join(
        f"<tr><td>{r.period}</td><td>{r.daysBefore}</td><td>${r.median_fare:,.0f}</td>"
        f"<td>${r.p25_fare:,.0f} – ${r.p75_fare:,.0f}</td><td>{r.pct_low_seats:.0f}%</td>"
        f"<td>{r.n_flights:,}</td></tr>" for r in s.itertuples())

    g = diary.dropna(subset=["change_class"]).groupby(["period", "route", "airline"])
    summ = g.agg(days=("change_class", "size"),
                 rose=("change_class", lambda c: (c == ROSE).sum()),
                 fell=("change_class", lambda c: (c == FELL).sum())).reset_index()
    ends = (diary.sort_values("daysBefore")
            .groupby(["period", "route"])["minFare"].agg(first="last", last="first").reset_index())
    summ = summ.merge(ends, on=["period", "route"]).sort_values(["period", "route"])
    rows2 = "\n".join(
        f"<tr><td>{r.period}</td><td>{r.route}</td><td>{r.airline}</td><td>{r.days}</td>"
        f"<td>{r.rose}</td><td>{r.fell}</td><td>{r.days - r.rose - r.fell}</td>"
        f"<td>${r.first:,.0f}</td><td>${r.last:,.0f}</td></tr>" for r in summ.itertuples())

    return f"""
<details class="tv"><summary>Table view — CZ-03, median lowest fare by period and days before departure
({len(s):,} rows)</summary>
<div class="tw"><table><thead><tr><th>Travel period</th><th>Days before departure</th>
<th>Median lowest fare</th><th>Middle half of fares</th><th>Flights with 1–3 seats left</th>
<th>Flights observed</th></tr></thead><tbody>{rows}</tbody></table></div></details>

<details class="tv"><summary>Table view — CZ-01, the {len(summ)} diary flights and how often each one moved
</summary>
<div class="tw"><table><thead><tr><th>Travel period</th><th>Route</th><th>Airline</th>
<th>Mornings checked</th><th>Rose 10%+</th><th>Fell 10%+</th><th>Barely moved</th>
<th>Fare at the start</th><th>Fare on departure day</th></tr></thead>
<tbody>{rows2}</tbody></table></div></details>"""


def page(spec_light: dict, spec_dark: dict, stats: dict, stair: pd.DataFrame,
         diary: pd.DataFrame, using_real: bool) -> str:
    banner = "" if using_real else """
  <p class="warn"><strong>PLACEHOLDER DATA.</strong> These charts are wired to
  <code>data/sample/</code>, generated by <code>src/make_sample_data.py</code> to match the
  real marginals reported in the process book. The individual flight paths are not real
  flights. Drop the three CSVs from <code>src/kaggle_export.py</code> into <code>data/</code>
  and re-run the build to replace them.</p>"""

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>When to Book — The Price Diary</title>
<style>
  :root {{
    color-scheme: light;
    --surface-1:#fcfcfb; --plane:#f9f9f7; --text-primary:#0b0b0b;
    --text-secondary:#52514e; --muted:#898781; --grid:#e1e0d9;
    --border:rgba(11,11,11,.10); --rose:#e34948; --fell:#2a78d6;
    --warn-bg:#fff4e5; --warn-line:#eda100; --warn-ink:#5a4100;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:where(:not([data-theme="light"])) {{
      color-scheme: dark;
      --surface-1:#1a1a19; --plane:#0d0d0d; --text-primary:#f0efec;
      --text-secondary:#c3c2b7; --muted:#898781; --grid:#2c2c2a;
      --border:rgba(255,255,255,.10); --rose:#e66767; --fell:#3987e5;
      --warn-bg:#2a2109; --warn-line:#c98500; --warn-ink:#f0d9a0;
    }}
  }}
  :root[data-theme="dark"] {{
    color-scheme: dark;
    --surface-1:#1a1a19; --plane:#0d0d0d; --text-primary:#f0efec;
    --text-secondary:#c3c2b7; --muted:#898781; --grid:#2c2c2a;
    --border:rgba(255,255,255,.10); --rose:#e66767; --fell:#3987e5;
    --warn-bg:#2a2109; --warn-line:#c98500; --warn-ink:#f0d9a0;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:40px 16px 72px; background:var(--plane);
    color:var(--text-primary);
    font:15px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif; }}
  main {{ max-width:960px; margin:0 auto; }}
  .eyebrow {{ font-size:11.5px; letter-spacing:.09em; text-transform:uppercase;
    color:var(--muted); margin:0 0 10px; }}
  h1 {{ font-size:30px; line-height:1.2; margin:0 0 12px; letter-spacing:-.01em; }}
  .lede {{ font-size:17px; color:var(--text-secondary); margin:0 0 4px; max-width:68ch; }}
  .byline {{ font-size:12.5px; color:var(--muted); margin:18px 0 0; }}
  .warn {{ background:var(--warn-bg); border:1px solid var(--warn-line); color:var(--warn-ink);
    padding:12px 14px; border-radius:8px; font-size:13px; margin:22px 0 0; }}
  .tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
    gap:12px; margin:30px 0 8px; }}
  .tile {{ background:var(--surface-1); border:1px solid var(--border);
    border-radius:10px; padding:16px 18px; }}
  .tile .v {{ font-size:30px; font-weight:650; letter-spacing:-.02em; line-height:1.1; }}
  .tile .k {{ font-size:12px; color:var(--muted); margin-top:6px; }}
  .tile .sw {{ display:inline-block; width:10px; height:10px; border-radius:2px;
    margin-right:6px; vertical-align:baseline; }}
  .card {{ background:var(--surface-1); border:1px solid var(--border);
    border-radius:12px; padding:22px 20px 14px; margin:22px 0; overflow-x:auto; }}
  .toolbar {{ display:flex; gap:10px; align-items:center; justify-content:space-between;
    flex-wrap:wrap; margin:0 0 18px; padding-bottom:14px; border-bottom:1px solid var(--grid); }}
  .hint {{ font-size:12.5px; color:var(--muted); }}
  button {{ font:inherit; font-size:12.5px; padding:6px 12px; border-radius:7px;
    border:1px solid var(--border); background:var(--surface-1);
    color:var(--text-secondary); cursor:pointer; min-height:32px; }}
  button:hover {{ background:var(--plane); }}
  h2 {{ font-size:19px; margin:38px 0 8px; }}
  p {{ max-width:72ch; }}
  .tv {{ margin:14px 0; font-size:13px; }}
  .tv summary {{ cursor:pointer; color:var(--text-secondary); padding:8px 0;
    min-height:32px; }}
  .tw {{ max-height:360px; overflow:auto; border:1px solid var(--border);
    border-radius:8px; }}
  table {{ border-collapse:collapse; width:100%; font-size:12.5px;
    font-variant-numeric:tabular-nums; }}
  th,td {{ text-align:left; padding:6px 10px; border-bottom:1px solid var(--grid);
    white-space:nowrap; }}
  th {{ position:sticky; top:0; background:var(--surface-1); color:var(--muted);
    font-weight:600; }}
  #period-filter .vega-bind {{ display:flex; align-items:center; gap:10px; }}
  #period-filter .vega-bind-name {{ font-size:12.5px; color:var(--text-secondary); font-weight:600; }}
  #period-filter select {{ font:inherit; font-size:13px; min-height:32px; padding:4px 10px;
    border-radius:7px; border:1px solid var(--border); background:var(--surface-1);
    color:var(--text-primary); }}
  .vega-embed {{ display:block; }}
  footer {{ font-size:12.5px; color:var(--muted); margin-top:40px;
    border-top:1px solid var(--border); padding-top:16px; }}
  code {{ font-size:.92em; background:var(--plane); padding:1px 4px; border-radius:3px; }}
</style></head>
<body>
<main>
  <p class="eyebrow">Jet 2 Holiday · Prototype Phase 1 &amp; 2 · CZ-01 + CZ-03</p>
  <h1>You cannot predict the morning a fare gets cheap.<br>You can predict the morning it gets expensive.</h1>
  <p class="lede">Checking a fare every day feels like doing something. Over 60 days of
  real Expedia searches it is mostly noise — until a few specific mornings, which arrive
  on a schedule the airline already published.</p>
  <p class="byline">Cynthia Zhou · Expedia Flight Prices (one-way fares searched 16 Apr – 5 Oct 2022)</p>
  {banner}

  <div class="tiles">
    <div class="tile"><div class="v">{stats['pct_flat']:.0f}%</div>
      <div class="k"><span class="sw" style="background:var(--grid)"></span>of mornings the fare
      barely moved (under 10% either way)</div></div>
    <div class="tile"><div class="v">{stats['pct_rise']:.0f}%</div>
      <div class="k"><span class="sw" style="background:var(--rose)"></span>of mornings it rose
      10% or more</div></div>
    <div class="tile"><div class="v">{stats['pct_drop']:.0f}%</div>
      <div class="k"><span class="sw" style="background:var(--fell)"></span>of mornings it fell
      10% or more</div></div>
    <div class="tile"><div class="v">{stats['worst_rise_val']:.0f}%</div>
      <div class="k">rose 10%+ on the worst single morning ({stats['worst_rise_period']},
      {stats['worst_rise_day']} days out{cutoff_note(stats['worst_rise_day'])})</div></div>
  </div>
  <p class="hint">Based on {stats['n_checks']:,} same-flight day-over-day price checks.</p>

  <div class="card">
    <div class="toolbar">
      <div id="period-filter"></div>
      <button id="theme" type="button">Dark / light</button>
    </div>
    <div id="viz"></div>
  </div>

  {table_view(stair, diary)}

  <h2>What the two views are doing</h2>
  <p><strong>CZ-01, the diary (top)</strong> is the hook. Each row is one flight that was
  really searchable every morning for about two months; each cell is one of those mornings,
  coloured only by whether the lowest fare moved 10% or more. The field is almost entirely
  grey. That is the finding: a traveller refreshing a fare has, on most days, nothing to
  react to.</p>
  <p><strong>CZ-03, the staircase (bottom)</strong> is the answer. Pooling the same flights
  into a median shows the structure the diary hides: the fare holds roughly flat, bottoms
  out, and then steps up — and the steps land next to the 21-, 14- and 7-day
  advance-purchase cutoffs, which is why the same mornings light up red across unrelated
  routes.</p>
  <p><strong>The link between them</strong> is the point of putting them together. Clicking
  a diary row draws that one flight's own fare path on top of the median, with its dots
  carrying the diary's red/blue/grey coding. You get to see a single traveller's experience
  and the population pattern on one pair of axes: the individual path is jagged and
  unhelpful, the median is a staircase, and both are the same data.</p>

  <footer>Built in Python with Altair; rendered as Vega-Lite 6 in the browser. Clean data:
  <code>data/cz_diary.csv</code>, <code>data/cz_staircase.csv</code>,
  <code>data/cz_changes.csv</code> — exported by <code>src/kaggle_export.py</code> from the
  Kaggle dataset <code>dilwong/flightprices</code>. Fares are the lowest total fare per
  flight per search day; a change is measured against the same flight's previous search
  within 3 days.</footer>
</main>
<script>
  const SPECS = {{ light: {json.dumps(spec_light)}, dark: {json.dumps(spec_dark)} }};
  const opts = {{ actions:{{export:true, source:false, compiled:false, editor:false}},
                  renderer:"canvas" }};
  function current() {{
    const stamp = document.documentElement.getAttribute("data-theme");
    if (stamp) return stamp;
    return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }}
  let view = null;
  function draw() {{
    vegaEmbed("#viz", SPECS[current()], opts).then(r => {{ view = r.view; }})
      .catch(e => {{ document.getElementById("viz").textContent = "Chart failed to load: " + e; }});
  }}
  // click-and-run: the libraries ship beside the page in vendor/, so it opens
  // offline from a zip; the CDN is the fallback if the page was copied alone.
  const LIBS = [
    ["vendor/vega.min.js",       "https://cdnjs.cloudflare.com/ajax/libs/vega/6.1.2/vega.min.js"],
    ["vendor/vega-lite.min.js",  "https://cdnjs.cloudflare.com/ajax/libs/vega-lite/6.1.0/vega-lite.min.js"],
    ["vendor/vega-embed.min.js", "https://cdnjs.cloudflare.com/ajax/libs/vega-embed/7.0.2/vega-embed.min.js"],
  ];
  const load = (src) => new Promise((ok, fail) => {{
    const s = document.createElement("script");
    s.src = src; s.onload = ok; s.onerror = () => {{ s.remove(); fail(); }};
    document.head.appendChild(s);
  }});
  (async () => {{
    for (const [local, cdn] of LIBS) {{
      try {{ await load(local); }} catch {{ await load(cdn); }}
    }}
    draw();
  }})().catch(() => {{
    document.getElementById("viz").textContent =
      "Could not load the charting library. Keep the vendor/ folder next to this page, or open it with an internet connection.";
  }});
  document.getElementById("theme").addEventListener("click", () => {{
    document.documentElement.setAttribute("data-theme",
      current() === "dark" ? "light" : "dark");
    if (window.vegaEmbed) draw();
  }});
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {{
    if (!document.documentElement.getAttribute("data-theme") && window.vegaEmbed) draw();
  }});
</script>
</body></html>"""


# ----------------------------------------------------------------------- run --
def main() -> None:
    diary, stair, chg = load()
    anno = annotations(stair)
    stats = headline_stats(chg)

    spec_light = build(diary, stair, anno, "light").to_dict()
    spec_dark = build(diary, stair, anno, "dark").to_dict()
    (BUILD / "cz01_cz03.light.vg.json").write_text(json.dumps(spec_light, indent=1))
    (BUILD / "cz01_cz03.dark.vg.json").write_text(json.dumps(spec_dark, indent=1))

    html = page(spec_light, spec_dark, stats, stair, diary, USING_REAL)
    (BUILD / "cz01_cz03.html").write_text(html)

    # stills for the process book: one plain, one with a flight already picked
    import vl_convert as vlc
    (BUILD / "screenshot_1_overview.png").write_bytes(
        vlc.vegalite_to_png(json.dumps(spec_light), scale=2))
    lead = (diary[diary.period == "Labor Day"].sort_values("route")
            if (diary.period == "Labor Day").any() else diary)
    leg = lead["legId"].iloc[0]
    linked = build(diary, stair, anno, "light", preselect=leg).to_dict()
    (BUILD / "screenshot_2_linked.png").write_bytes(
        vlc.vegalite_to_png(json.dumps(linked), scale=2))
    brushed = build(diary, stair, anno, "light", prebrush=(21, 7)).to_dict()
    (BUILD / "screenshot_3_brushed.png").write_bytes(
        vlc.vegalite_to_png(json.dumps(brushed), scale=2))

    # the clean data the process book links to, beside the page
    out_data = BUILD / "data"
    out_data.mkdir(exist_ok=True)
    shutil.copytree(ROOT / "src" / "vendor", BUILD / "vendor", dirs_exist_ok=True)
    for f in FILES:
        shutil.copy(SRC / f, out_data / f)

    print(f"\nwrote {BUILD}/")
    for p in sorted(BUILD.rglob("*")):
        if p.is_file():
            print(f"  {p.relative_to(BUILD)!s:34s} {p.stat().st_size/1024:8.1f} KB")
    # import the sibling module by location, so the build works however it is launched
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import process_book
    process_book.write(ROOT / "docs" / "process_book_section.md", stats=stats, anno=anno,
                       diary=diary, stair=stair, chg=chg, using_real=USING_REAL,
                       cutoff_note=cutoff_note)
    print(f"\npreselected flight for screenshot 2: {leg}")
    print(f"process book section: {ROOT / 'docs' / 'process_book_section.md'}")


if __name__ == "__main__":
    main()
