"""
Assemble Cynthia's folder for the team repo: submissions/cynthia-cz01-cz03/

    .venv/bin/python src/make_submission.py

Refuses to run on placeholder data: the team repo gets real numbers or nothing.
Steps: rebuild the charts from data/, write website_data.json (shaped for the
team site's KP constant and diary scene), write validation.json (the real data
must reproduce the Data Exploration figures), copy everything into
submission/cynthia-cz01-cz03/, and write its README.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"
OUT = ROOT / "submission" / "cynthia-cz01-cz03"
CSV = ["cz_staircase.csv", "cz_changes.csv", "cz_diary.csv", "cz_site_diary.csv"]
KEY = {"Labor Day": "lab", "July 4": "jul", "Memorial Day": "mem", "Non-holiday": "non"}

# Figures already published in the process book's Data Exploration section.
# The real export uses the same rules, so it has to land on these.
EXPLORATION = {
    "Labor Day median lowest fare, 60 days out": ("Labor Day", 60, 290),
    "Labor Day median lowest fare, 14 days out (the floor)": ("Labor Day", 14, 258),
    "Labor Day median lowest fare, 13 days out (after the jump)": ("Labor Day", 13, 284),
    "Labor Day median lowest fare, 1 day out": ("Labor Day", 1, 371),
    "July 4 median lowest fare, 60 days out": ("July 4", 60, 379),
}


def website_data(stair: pd.DataFrame, site: pd.DataFrame) -> dict:
    """Drop-in data for the team site (src/index.src.html)."""
    kp = {}
    for period, g in stair[stair.daysBefore.between(1, 60)].groupby("period"):
        g = g.sort_values("daysBefore", ascending=False)
        kp[KEY[period]] = [[int(d), int(round(v))] for d, v in zip(g.daysBefore, g.median_fare)]

    # One flight = 60 fares (60 days out -> 1 day out) and a 60-char class string:
    #   r rose 10%+   f fell 10%+   . barely moved
    #   ' ' checked, but no previous check within 3 days to compare with
    #   - not checked that morning (fare carried over so tooltips stay numeric)
    code = {"rose": "r", "fell": "f", "flat": "."}
    diary: dict[str, list] = {}
    for (route, leg), g in site.groupby(["route", "legId"], sort=False):
        by_day = g.set_index("daysBefore")
        fares, cls, last = [], [], None
        first = float(by_day.sort_index(ascending=False)["minFare"].iloc[0])
        for d in range(60, 0, -1):
            if d in by_day.index:
                row = by_day.loc[d]
                last = float(row.minFare)
                fares.append(int(round(last)))
                cls.append(code.get(row.cls, " ") if isinstance(row.cls, str) else " ")
            else:
                fares.append(int(round(last if last is not None else first)))
                cls.append("-")
        airline = " + ".join(dict.fromkeys(a.strip() for a in str(g.airline.iloc[0]).split("||") if a.strip()))
        diary.setdefault(route, []).append(
            {"a": airline or "Unknown", "ns": bool(g.isNonStop.iloc[0]), "f": fares, "c": "".join(cls)})

    return {
        "source": "Expedia Flight Prices (Kaggle dilwong/flightprices), one-way fares searched 2022-04-16..2022-10-05",
        "built_by": "Cynthia Zhou, src/make_submission.py",
        "KP": kp,
        "SITE_DIARY_note": ("Labor Day flights per route 'ORIG-DEST', densest first. f = lowest fare "
                            "60..1 days out; c = class per day: r rose 10%+, f fell 10%+, . barely moved, "
                            "' ' no comparable previous check, - not checked (fare carried over)."),
        "SITE_DIARY": diary,
    }


def validation(stair: pd.DataFrame, diary: pd.DataFrame, chg: pd.DataFrame,
               site: pd.DataFrame, wd: dict) -> dict:
    checks = []
    for name, (period, day, expected) in EXPLORATION.items():
        row = stair[(stair.period == period) & (stair.daysBefore == day)]
        got = float(row.median_fare.iloc[0]) if len(row) else None
        ok = got is not None and abs(got - expected) <= 1.0
        checks.append({"check": name, "expected": expected,
                       "got": None if got is None else round(got, 2), "pass": ok})
    lab = {d: v for d, v in wd["KP"].get("lab", [])}
    team_copy = {"floor": 258, "jump_dollars": 26}
    floor_day = min(lab, key=lambda d: (lab[d], d)) if lab else None
    return {
        "exploration_figures_reproduced": all(c["pass"] for c in checks),
        "checks": checks,
        "team_site_copy": {
            "text_on_site": "bottoms out at $258 fourteen days before departure, then jumps $26 overnight",
            "real_floor": None if floor_day is None else {"days_before": floor_day, "fare": lab[floor_day]},
            "real_next_day": None if floor_day is None or floor_day - 1 not in lab else
            {"days_before": floor_day - 1, "fare": lab[floor_day - 1],
             "jump_dollars": lab[floor_day - 1] - lab[floor_day]},
            "matches": (floor_day == 14 and lab.get(14) == team_copy["floor"]
                        and lab.get(13, 0) - lab.get(14, 0) == team_copy["jump_dollars"]),
        },
        "counts": {
            "staircase_rows": len(stair), "changes_rows": len(chg),
            "same_flight_checks": int(chg.n.sum()),
            "diary_flights": int(diary.legId.nunique()), "diary_rows": len(diary),
            "site_diary_routes": len(wd["SITE_DIARY"]),
            "site_diary_flights": sum(len(v) for v in wd["SITE_DIARY"].values()),
            "site_diary_routes_with_4plus_flights": sum(len(v) >= 4 for v in wd["SITE_DIARY"].values()),
        },
    }


README = """# Cynthia Zhou — CZ-01 Price Diary + CZ-03 The Staircase

**CZ-01 (Q2, Q15): what does checking a fare every day actually show you?**
**CZ-03 (Q1, Q2): does the median fare creep up or jump?**

## Files

- [Visualization](cz01_cz03.html): two linked views, open in a browser (works offline; keep `vendor/` next to it).
  Click a diary row to trace that flight on the staircase; drag across the staircase to narrow the diary; the period dropdown filters both.
- Screenshots: [default](screenshot_1_overview.png), [a flight picked](screenshot_2_linked.png), [days 21–7 brushed](screenshot_3_brushed.png), [interaction design](interaction_design.png).
- **Data (tables):**
  - [cz_staircase.csv](data/cz_staircase.csv): median / 25th / 75th percentile lowest fare and % of flights with 1–3 seats left, by period × days before departure ({stair_rows} rows).
  - [cz_changes.csv](data/cz_changes.csv): % of fares that rose / fell 10%+ since the same flight's previous check, by period × day ({chg_rows} rows, {checks:,} checks).
  - [cz_diary.csv](data/cz_diary.csv): day-by-day lowest fare of {diary_flights} flights, 12 per period, one per route ({diary_rows:,} rows).
  - [cz_site_diary.csv](data/cz_site_diary.csv): Labor Day, up to 8 flights per route for the site's diary scene ({site_flights} flights on {site_routes} routes).
- [Website data](website_data.json): the same numbers shaped for `src/index.src.html` (see below).
- [Verification](validation.json): the real export reproduces the Data Exploration figures ({verdict}).
- **Code:** [kaggle_export.py](code/kaggle_export.py) (Kaggle + DuckDB, 6 GB → CSVs), [build_charts.py](code/build_charts.py) (Python/Altair → the page), [make_submission.py](code/make_submission.py) (this folder).

## Definitions

Departure windows in 2022, inclusive: Memorial Day May 26–31; July 4 June 30–July 5; Labor Day September 1–6; Non-holiday June 9–14 and August 11–16 pooled — the same windows as Yuhan's Q7. Source: [Dillon Wong's Expedia Flight Prices](https://www.kaggle.com/datasets/dilwong/flightprices).

A fare is the lowest total fare for a flight (legId) on a search day. A change compares it with the same flight's previous search; gaps over 3 days are not compared. "Rose/fell 10%+" means the new fare is at least 10% above/below the previous one. Seats remaining of 0 is treated as missing. Diary flights are picked by rule (densest daily coverage first), not by hand.

## Swapping the real data into the site

`website_data.json` has two keys made for `src/index.src.html`:

**`KP` (CZ-03 staircase)** — same shape as the placeholder constant: `{{ lab, jul, mem, non }}`, each a list of `[daysBefore, medianFare]`, one point per day from 60 (Memorial Day: 44) to 1. `holidayCurve()` works unchanged:

```js
const KP = WEBSITE_DATA.KP;
```

**`SITE_DIARY` (CZ-01 diary)** — real Labor Day flights keyed by route `"ATL-BOS"`. A drop-in for `diaryRows()` that returns the same `{{ name, days: [{{ d, fare, ch, cls }}] }}` rows:

```js
const CLS = {{ r: 'rose', f: 'fell', '.': 'flat', ' ': 'flat', '-': 'none' }};
function diaryRowsReal(origin, dest, page = 0, n = 4) {{
  const list = WEBSITE_DATA.SITE_DIARY[`${{origin}}-${{dest}}`];
  if (!list || !list.length) return null;               // caller falls back to diaryRows()
  const start = (page * n) % list.length;
  return d3.range(Math.min(n, list.length)).map(k => {{
    const i = (start + k) % list.length, fl = list[i];
    const days = fl.f.map((fare, j) => {{
      const c = fl.c[j], prev = j ? fl.f[j - 1] : fare;
      return {{ d: 60 - j, fare, ch: (c === 'r' || c === 'f' || c === '.') ? fare / prev - 1 : 0, cls: CLS[c] }};
    }});
    return {{ name: `Flight ${{i + 1}}`, airline: fl.a, days }};
  }});
}}
// in buildWatching():
// watch.flights = diaryRowsReal(state.origin, state.dest, state.diarySeed - 1)
//              || diaryRows(hash(state.origin + state.dest) + state.diarySeed * 9973, 4, base);
```

`cls: 'none'` (a morning with no check) draws as an empty cell with no outline. {coverage_note}

**Copy on the site.** The staircase text says the Labor Day fare "bottoms out at $258 fourteen days before departure, then jumps $26 overnight". {copy_note}
"""


def main() -> None:
    preview = "--preview" in sys.argv
    missing = [f for f in CSV if not (DATA / f).exists()]
    if missing and not preview:
        raise SystemExit(f"Real data missing in {DATA}: {missing}\n"
                         "Run src/kaggle_export.py on Kaggle first. Refusing to package placeholder data.")
    src = DATA if not missing else Path(sys.argv[sys.argv.index("--preview") + 1])

    sys.path.insert(0, str(HERE))
    import build_charts  # noqa: E402  (rebuilds build/ from data/)
    if not preview:
        assert build_charts.USING_REAL, "build_charts did not pick up the real data"
    build_charts.main()

    stair = pd.read_csv(src / "cz_staircase.csv")
    chg = pd.read_csv(src / "cz_changes.csv")
    diary = pd.read_csv(src / "cz_diary.csv")
    site = pd.read_csv(src / "cz_site_diary.csv")
    wd = website_data(stair, site)
    val = validation(stair, diary, chg, site, wd)

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "data").mkdir(parents=True)
    (OUT / "code").mkdir()
    build = ROOT / "build"
    shutil.copy(build / "cz01_cz03.html", OUT)
    shutil.copytree(build / "vendor", OUT / "vendor")
    for png in ["screenshot_1_overview.png", "screenshot_2_linked.png",
                "screenshot_3_brushed.png", "interaction_design.png"]:
        shutil.copy((ROOT / "docs" / png) if png == "interaction_design.png" else (build / png), OUT)
    for f in CSV:
        shutil.copy(src / f, OUT / "data" / f)
    for f in ["kaggle_export.py", "build_charts.py", "process_book.py", "make_submission.py"]:
        shutil.copy(HERE / f, OUT / "code" / f)
    shutil.copy(ROOT / "requirements.txt", OUT / "code" / "requirements.txt")
    (OUT / "website_data.json").write_text(json.dumps(wd, separators=(",", ":")))
    (OUT / "validation.json").write_text(json.dumps(val, indent=2))

    c = val["counts"]
    tc = val["team_site_copy"]
    if tc["matches"]:
        copy_note = "The real data matches it, so the text can stay."
    elif tc["real_floor"] and tc["real_next_day"]:
        copy_note = (f"With the real data the floor is ${tc['real_floor']['fare']} at "
                     f"{tc['real_floor']['days_before']} days and the next day is "
                     f"${tc['real_next_day']['fare']} ({tc['real_next_day']['jump_dollars']:+d}); "
                     "the text and the quiz's \"$258 today\" should follow these numbers.")
    else:
        copy_note = "Check it against `KP.lab` after swapping the data in."
    short = c["site_diary_routes"] - c["site_diary_routes_with_4plus_flights"]
    coverage_note = (f"{c['site_diary_routes_with_4plus_flights']} of {c['site_diary_routes']} routes have "
                     "at least four flights" + (f"; {short} have fewer, so the function shows what there is "
                                                "and the fallback covers routes with none." if short else "."))
    (OUT / "README.md").write_text(README.format(
        stair_rows=c["staircase_rows"], chg_rows=c["changes_rows"], checks=c["same_flight_checks"],
        diary_flights=c["diary_flights"], diary_rows=c["diary_rows"],
        site_flights=c["site_diary_flights"], site_routes=c["site_diary_routes"],
        verdict="all checks pass" if val["exploration_figures_reproduced"] else "SOME CHECKS FAIL — see file",
        coverage_note=coverage_note, copy_note=copy_note))

    print(f"\nwrote {OUT}")
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and "vendor" not in p.parts:
            print(f"  {str(p.relative_to(OUT)):34s} {p.stat().st_size/1024:9.1f} KB")
    print("\nvalidation:", "PASS" if val["exploration_figures_reproduced"] else "FAIL")
    for ch in val["checks"]:
        print(f"  {'ok ' if ch['pass'] else 'BAD'} {ch['check']}: expected {ch['expected']}, got {ch['got']}")
    print("team-site copy matches real data:", tc["matches"])


if __name__ == "__main__":
    main()
