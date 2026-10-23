"""Before/after charts: each teammate's result next to the full-dataset redo."""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "out", "redo")
SUB = os.path.join(HERE, "..", "deploy", "submissions")
NAVY, RED, BLUE, GREY, INK, MUTED = "#003a70", "#d0263c", "#2a6fd0", "#a3adbd", "#0a1f3c", "#6f7c90"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlesize": 11})

def cutoffs(ax):
    for d in (21, 14, 7):
        ax.axvline(d, color=MUTED, ls=":", lw=1)
    ax.set_xlim(61, 0); ax.set_xlabel("Days before departure")

# ---------------- Cynthia ----------------
c1 = pd.read_csv(os.path.join(R, "cz_c1_every_quote.csv"))
c2 = pd.read_csv(os.path.join(R, "cz_c2_matched_changes.csv"))
c3 = pd.read_csv(os.path.join(R, "cz_c3a_cohort_staircase.csv"))
lowh = pd.read_csv(os.path.join(R, "cz_c3b_low_day_hist_full60.csv"))
wait = pd.read_csv(os.path.join(R, "cz_c3c_wait_outcomes.csv"))

fig, ax = plt.subplots(2, 2, figsize=(14, 9))
a = ax[0, 0]
lab = c1[c1.period == "Labor Day"]
a.plot(lab.dbf, lab.median_fare, drawstyle="steps-post", color=GREY, lw=2.5, label="BEFORE: Labor Day median, all quotes (Cynthia)")
co = c3[c3.period == "All flights"]
a.plot(co.dbf, co.median_fare, drawstyle="steps-post", color=NAVY, lw=2, label="AFTER: same 16,182 flights every day")
a.set_ylabel("Median lowest fare (USD)"); a.legend(frameon=False, fontsize=9, loc="upper left")
a.set_title("CZ-03 staircase: the steps survive when the flights are held fixed"); cutoffs(a)

a = ax[0, 1]
for p, c in (("All flights", NAVY), ("Labor Day", RED), ("July 4", "#e8a33d"), ("Non-holiday", GREY)):
    d = c2[c2.period == p]
    a.plot(d.dbf, d.pct_rose10, color=c, lw=2 if p == "All flights" else 1.2, label=p)
d = c2[c2.period == "All flights"]
a.plot(d.dbf, d.pct_fell10, color=BLUE, lw=1.5, ls="--", label="All flights: fell 10%+")
a.set_ylabel("% of flights, vs. same flight one day earlier"); a.legend(frameon=False, fontsize=9)
a.set_title("CZ-01 diary: rises spike at 20, 13, 5, 1 days out
drops never spike"); cutoffs(a)

a = ax[1, 0]
h = lowh.set_index("low_day").reindex(range(1, 61), fill_value=0)
cols = [BLUE if d > 21 else RED for d in h.index]
a.bar(h.index, 100 * h.flights / h.flights.sum(), color=cols, width=0.8)
share = 100 * h.loc[22:60, "flights"].sum() / h.flights.sum()
a.text(45, a.get_ylim()[1] * 0.85, f"{share:.0f}% of flights hit their lowest\nfare more than 21 days out", color=BLUE, fontsize=10, ha="center")
a.set_ylabel("% of flights"); a.set_title("NEW: when each flight's lowest fare first appeared"); cutoffs(a)

a = ax[1, 1]
w = wait[wait.buy_at.isin([44, 22])].copy()
w["label"] = w.apply(lambda r: f"buy {int(r.buy_at)}d out, wait to {int(r.wait_until)}d", axis=1)
y = range(len(w))
a.barh(y, w.pct_cheaper, color=BLUE, label="got cheaper")
a.barh(y, w.pct_same, left=w.pct_cheaper, color="#e6ebf2", label="same")
a.barh(y, w.pct_pricier, left=w.pct_cheaper + w.pct_same, color=RED, label="got pricier")
for i, (_, r) in enumerate(w.iterrows()):
    a.text(r.pct_cheaper + r.pct_same + r.pct_pricier / 2, i, f"{r.pct_pricier:.0f}%", va="center", ha="center", color="white", fontsize=9, fontweight="bold")
    a.text(r.pct_cheaper / 2, i, f"{r.pct_cheaper:.0f}%", va="center", ha="center", color="white", fontsize=9, fontweight="bold")
a.set_yticks(list(y)); a.set_yticklabels(w.label); a.invert_yaxis(); a.set_xlim(0, 100)
a.set_xlabel("% of the same 16,182 flights"); a.legend(frameon=False, fontsize=9, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.32))
a.set_title("NEW: odds of waiting (same flights)
Waiting until day 21 is a coin flip; after 21 you lose")
fig.suptitle("Cynthia (CZ-01, CZ-03): before vs. full-dataset redo", fontsize=14, fontweight="bold", x=0.01, ha="left")
fig.tight_layout(); fig.savefig(os.path.join(R, "compare_cynthia.png"), dpi=120); plt.close(fig)

# ---------------- Yuhan ----------------
pooled = pd.read_csv(os.path.join(R, "q7_1_pooled.csv"))
route = pd.read_csv(os.path.join(R, "q7_2_same_route.csv"))
choice = pd.read_csv(os.path.join(R, "q7_3_same_choice.csv"))
bydbf = pd.read_csv(os.path.join(R, "q7_3b_same_choice_by_days_out.csv"))
total = choice.loc[choice.choices.idxmax()]
allroute = route[route.period == "All flights"]
fig, ax = plt.subplots(1, 3, figsize=(15, 4.8), gridspec_kw={"width_ratios": [1.1, 1.2, 1.2]})
a = ax[0]
levels = ["BEFORE\npooled medians\n(Yuhan)", "same route\n(215 routes)", "AFTER\nsame route, date,\nsearch day (1.7M)"]
pct = [pooled.loc[pooled.period == "All flights", "nonstop_pct"].iloc[0], allroute.pct.median(), total.median_pct_diff]
a.bar(levels, pct, color=[GREY, "#7d97c4", NAVY], width=0.6)
for i, v in enumerate(pct):
    a.text(i, v - 1.5, f"{v:.0f}%", ha="center", va="top", fontsize=12, fontweight="bold", color=INK)
a.axhline(0, color=INK, lw=1); a.set_ylabel("Nonstop vs. connecting, median % difference"); a.set_ylim(min(pct) - 8, 3)
a.set_title("The nonstop discount shrinks as the comparison gets fair")
a = ax[1]
share = [100, 100 * (allroute.pct < 0).mean(), total.pct_nonstop_cheaper]
a.bar(levels, share, color=[GREY, "#7d97c4", NAVY], width=0.6)
for i, v in enumerate(share):
    a.text(i, v + 1.5, f"{v:.0f}%" if i else "every period", ha="center", fontsize=12, fontweight="bold", color=INK)
a.set_ylim(0, 110); a.set_ylabel("% of comparisons where nonstop was cheaper")
a.set_title("...but nonstop still wins most of the time")
a = ax[2]
a.plot(bydbf.dbf, bydbf.pct_nonstop_cheaper, color=NAVY, lw=2)
a2 = a.twinx(); a2.spines["right"].set_visible(True)
a2.plot(bydbf.dbf, bydbf.median_pct_diff, color=RED, lw=1.5, ls="--")
a.set_ylabel("% nonstop cheaper (solid)", color=NAVY); a2.set_ylabel("median % difference (dashed)", color=RED)
a.set_title("NEW: the nonstop edge fades near departure"); cutoffs(a)
fig.suptitle("Yuhan (YH-02): before vs. full-dataset redo", fontsize=14, fontweight="bold", x=0.01, ha="left")
fig.tight_layout(); fig.savefig(os.path.join(R, "compare_yuhan.png"), dpi=120); plt.close(fig)

# ---------------- Arrington ----------------
st = pd.read_csv(os.path.join(SUB, "Arrington_Visualizations", "atl_state_fares.csv")).sort_values("avg_fare")
routes = pd.read_csv(os.path.join(R, "ag01_1_routes.csv"))
near = pd.read_csv(os.path.join(R, "ag01_3_nearby_airports.csv"))
atl = routes[(routes.orig == "ATL") & (routes.period == "All flights")].sort_values("median_fare")
fig, ax = plt.subplots(1, 3, figsize=(16, 5.6), gridspec_kw={"width_ratios": [1, 1, 1.3]})
a = ax[0]
a.barh(st.state, st.avg_fare, color=GREY); a.invert_yaxis()
for i, (_, r) in enumerate(st.iterrows()):
    a.text(r.avg_fare + 5, i, f"${r.avg_fare:.0f}", va="center", fontsize=9)
a.set_title("BEFORE (Arrington): mean fare from ATL by state"); a.set_xlabel("Mean fare (USD)")
a = ax[1]
a.barh(atl.dest, atl.median_fare, color=NAVY, label="median"); a.invert_yaxis()
a.scatter(atl.mean_fare, range(len(atl)), color=RED, zorder=3, s=18, label="mean (Arrington's measure)")
for i, (_, r) in enumerate(atl.iterrows()):
    a.text(max(r.median_fare, r.mean_fare) + 8, i, f"${r.median_fare:.0f}", va="center", fontsize=9)
a.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2); a.set_xlabel("Fare (USD)")
a.set_title("AFTER: median by airport from ATL\n(CA splits into LAX / SFO / OAK)")
a = ax[2]
allp = near[near.period == "All flights"]
ba = allp[allp.metro == "Bay Area"].sort_values("saving_usd")
ny = allp[allp.metro == "New York"].copy()
ny["lo"] = ny[["EWR", "JFK", "LGA"]].min(axis=1); ny["hi"] = ny[["EWR", "JFK", "LGA"]].max(axis=1); ny = ny.sort_values("saving_usd")
yb = range(len(ba)); yn = [len(ba) + 1 + i for i in range(len(ny))]
a.hlines(yb, ba.SFO, ba.OAK, color=GREY, lw=2); a.scatter(ba.SFO, yb, color=BLUE, zorder=3, label="cheaper airport"); a.scatter(ba.OAK, yb, color=RED, zorder=3, label="pricier airport")
a.hlines(yn, ny.lo, ny.hi, color=GREY, lw=2); a.scatter(ny.lo, yn, color=BLUE, zorder=3); a.scatter(ny.hi, yn, color=RED, zorder=3)
a.set_yticks(list(yb) + yn); a.set_yticklabels([f"{o} → SFO vs OAK" for o in ba.orig] + [f"{o} → {c} vs {p}" for o, c, p in zip(ny.orig, ny.cheapest, ny.priciest)], fontsize=8)
a.set_xlabel("Median fare (USD)"); a.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
a.set_title("NEW (Q5): nearby airports, all origins\nBay Area: SFO beats OAK by $145 (median)")
fig.suptitle("Arrington (AG01): before vs. full-dataset redo", fontsize=14, fontweight="bold", x=0.01, ha="left")
fig.tight_layout(); fig.savefig(os.path.join(R, "compare_arrington.png"), dpi=120); plt.close(fig)
print("saved")
