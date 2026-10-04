"""Step 6: charts.   ./venv/bin/python charts.py -> charts/00_cover.png, 01_seasons.png, 02_permutation.png, 03_catalogue.png, 04_durations.png, 05_countries_genres.png

Only results/ is read: the Office charts show season and specification aggregates, never episode-by-episode IMDb ratings."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
R = HERE / "results"
INK, DIM, GRID, BG, BLUE, ORANGE, GRAY, GREEN = "#f2f2f0", "#8a8a87", "#1d1d1d", "#0b0b0b", "#3987e5", "#d95926", "#9a9a96", "#3aa876"
plt.rcParams.update({"figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG, "text.color": INK,
                     "axes.edgecolor": "#3a3a3a", "axes.labelcolor": DIM, "xtick.color": DIM, "ytick.color": DIM,
                     "axes.grid": True, "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 1,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "font.family": ["Helvetica Neue", "Arial", "DejaVu Sans"], "font.size": 11, "axes.titlesize": 13,
                     "axes.titlelocation": "left", "axes.titlepad": 12})
YR = pd.read_csv(R / "netflix_year.csv"); DE = pd.read_csv(R / "netflix_decade.csv"); H90 = pd.read_csv(R / "netflix_hist90.csv"); CO = pd.read_csv(R / "netflix_country.csv"); GE = pd.read_csv(R / "netflix_genre.csv")
NS = pd.read_csv(R / "netflix_summary.csv").set_index("key")["value"]; SE = pd.read_csv(R / "office_seasons.csv"); TE = pd.read_csv(R / "office_tests.csv").set_index("spec"); NU = pd.read_csv(R / "office_null.csv")
OS = pd.read_csv(R / "office_summary.csv").set_index("key")["value"]
LABEL = {"primary": "the rule (guest in at most 3 episodes, notable)", "cap1": "one-episode guests only", "cap5": "guests in up to 5 episodes", "any_credit": "any guest credit, no notability test",
         "no_specials": "without premieres, finales, long episodes", "seasons_1_7": "seasons 1-7 only", "seasons_8_9": "seasons 8-9 only"}


def save(fig, name):
    fig.tight_layout(); fig.savefig(HERE / "charts" / name, dpi=150); plt.close(fig)


def catalogue(axes):
    ax = axes[0]; x = np.arange(len(YR)); ax.bar(x, YR["movies"], color=BLUE, width=0.62, label="movies"); ax.bar(x, YR["tv_shows"], bottom=YR["movies"], color=ORANGE, width=0.62, label="TV shows")
    for xi, m, t in zip(x, YR["movies"], YR["tv_shows"]): ax.text(xi, m + t + 30, f"{m + t:,}", ha="center", fontsize=9, color=INK)
    ax.set_xticks(x); ax.set_xticklabels(YR["year_added"]); ax.set_ylim(0, 2500); ax.set_ylabel("titles in the January 2021 catalogue"); ax.grid(axis="x", visible=False); ax.legend(frameon=False, labelcolor=INK, fontsize=9, loc="upper left")
    ax.set_title("Titles by year added (still there in 2021)", fontsize=12)
    ax = axes[1]; ax.plot(YR["year_added"], 100 * YR["movies_within_1y"], color=BLUE, linewidth=2.6, marker="o", label="movies"); ax.plot(YR["year_added"], 100 * YR["tv_within_1y"], color=ORANGE, linewidth=2.6, marker="o", label="TV shows")
    ax.set_ylim(0, 100); ax.set_xticks(YR["year_added"]); ax.set_ylabel("% released in the year added or the one before"); ax.legend(frameon=False, labelcolor=INK, fontsize=9, loc="lower left"); ax.set_title("How new is what gets added?", fontsize=12)


def durations(axes):
    ax = axes[0]; d = DE[DE["decade"] >= 1960]; x = np.arange(len(d))
    ax.bar(x, d["median_min"], color=BLUE, width=0.6); ax.vlines(x, d["p25_min"], d["p75_min"], color=INK, linewidth=1.6)
    for xi, m, n, hi in zip(x, d["median_min"], d["movies"], d["p75_min"]): ax.text(xi, hi + 5, f"n={n:,}", ha="center", fontsize=8.5, color=INK)
    ax.set_xticks(x); ax.set_xticklabels([f"{int(v)}s" for v in d["decade"]], fontsize=9); ax.set_ylim(0, 205); ax.set_ylabel("running time, minutes (median, middle half)"); ax.grid(axis="x", visible=False)
    ax.set_title("Movies are getting shorter, by release decade", fontsize=12)
    ax = axes[1]; mode = int(NS["mode_min_1990s"]); c = [ORANGE if lo <= mode < lo + 10 else BLUE for lo in H90["bin_lo"]]
    ax.bar(H90["bin_lo"] + 5, H90["movies"], width=9, color=c); ax.axvline(NS["median_min_1990s"], color=GREEN, linestyle="--", linewidth=1.4); ax.text(NS["median_min_1990s"] + 3, H90["movies"].max() * 0.98, f"median {NS['median_min_1990s']:.0f}", color=GREEN, fontsize=9, va="top")
    ax.set_xlabel("minutes (10-minute bins; orange: most common length, 94)"); ax.set_ylabel("1990s movies"); ax.grid(axis="x", visible=False); ax.set_title(f"The {int(NS['movies_1990s'])} movies of the 1990s: no one length", fontsize=12)


def countries_genres(axes):
    ax = axes[0]; cols = {"United States": BLUE, "India": ORANGE, "United Kingdom": GREEN}
    last = {}
    for k in CO["country"].unique():
        d = CO[CO["country"] == k]; c = cols.get(k, "#5a5a58"); ax.plot(d["year_added"], 100 * d["share"], color=c, linewidth=2.6 if k in cols else 1.4, marker="o", markersize=4); last[k] = 100 * d["share"].iloc[-1]
    ypos, floor = {}, -99
    for k in sorted(last, key=last.get): ypos[k] = max(last[k], floor + 2.3); floor = ypos[k]       # nudge the end-of-line labels apart
    for k in last: ax.text(2020.12, ypos[k], k.replace("United Kingdom", "UK").replace("United States", "US"), fontsize=8.5, color=cols.get(k, DIM), va="center")
    ax.set_xlim(2015.8, 2021.2); ax.set_xticks(range(2016, 2021)); ax.set_ylim(0, 55); ax.set_ylabel("% of titles that list a country"); ax.set_title("Where titles come from, by year added", fontsize=12)
    ax = axes[1]; d = GE.iloc[::-1].reset_index(drop=True); y = np.arange(len(d))
    for yi, a, b in zip(y, d["share_2016_17"], d["share_2019_20"]): ax.plot([100 * a, 100 * b], [yi, yi], color="#3a3a3a", linewidth=1.6, zorder=1)
    ax.scatter(100 * d["share_2016_17"], y, s=48, color=GRAY, zorder=3, label="added 2016-17"); ax.scatter(100 * d["share_2019_20"], y, s=48, color=BLUE, zorder=3, label="added 2019-20")
    ax.set_yticks(y); ax.set_yticklabels(d["genre"], fontsize=8.5); ax.set_xlim(0, 35); ax.set_xlabel("% of titles added that list the genre"); ax.grid(axis="y", visible=False); ax.legend(frameon=False, labelcolor=INK, fontsize=9, loc="lower right"); ax.set_title("The nine biggest genres", fontsize=12)


def seasons(axes):
    ax = axes[0]; x = SE["season"]; ax.bar(x, SE["mean_rating"], color="#2a2a2a", width=0.62, edgecolor="#3a3a3a")
    ax.scatter(x, SE["mean_guest"], s=52, color=BLUE, zorder=3, label="guest-star episodes"); ax.scatter(x, SE["mean_other"], s=52, color=ORANGE, marker="D", zorder=3, label="other episodes")
    for xi, m in zip(x, SE["mean_rating"]): ax.text(xi, 6.0, f"{m:.2f}", ha="center", fontsize=8.5, color=INK)
    ax.set_ylim(5.8, 9); ax.set_xticks(range(1, 10)); ax.set_xlabel("season"); ax.set_ylabel("mean IMDb rating (axis starts at 5.8)"); ax.legend(frameon=False, labelcolor=INK, fontsize=9, loc="upper right"); ax.set_title("Season means, split by guest-star episodes", fontsize=12)
    ax = axes[1]; d = SE.copy(); diff = d["mean_guest"] - d["mean_other"]; ax.scatter(d["season"], diff, s=d["episodes"] * 9, color=BLUE, zorder=3, alpha=0.9)
    ax.axhline(0, color=DIM, linewidth=0.9); ax.axhline(TE.loc["primary", "adj_diff"], color=GREEN, linestyle="--", linewidth=1.3)
    for s, v, n in zip(d["season"], diff, d["episodes"]): ax.text(s, v + (0.075 if v >= 0 else -0.075), f"n={n}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8, color=DIM)
    ax.set_xticks(range(1, 10)); ax.set_xlabel("season"); ax.set_ylabel("guest-star episodes minus others (stars)"); ax.set_ylim(-0.5, 0.5); ax.set_title("The gap, season by season (dashed: pooled)", fontsize=12)


def permutation(axes):
    ax = axes[0]; mid = (NU["bin_lo"] + NU["bin_hi"]) / 2; t = TE.loc["primary"]
    ax.bar(mid, NU["count"], width=0.024, color="#4a4a48"); ax.axvspan(t["null_lo"], t["null_hi"], color=BLUE, alpha=0.12, label="95% of shuffles")
    ax.axvline(t["adj_diff"], color=ORANGE, linewidth=2.4, label=f"observed {t['adj_diff']:+.3f}"); ax.set_xlim(-0.4, 0.4); ax.set_xlabel("guest minus other, shuffled within seasons (stars)"); ax.set_ylabel("shuffles (of 10,000)")
    ax.legend(frameon=False, labelcolor=INK, fontsize=9, loc="upper left"); ax.set_title("If guest stars did nothing: what chance alone gives", fontsize=12)
    ax = axes[1]; order = list(TE.index)[::-1]; y = np.arange(len(order))
    for yi, k in zip(y, order):
        r = TE.loc[k]; ax.plot([r["ci_lo"], r["ci_hi"]], [yi, yi], color="#7a7a77", linewidth=2.2, zorder=2); ax.scatter([r["adj_diff"]], [yi], s=52, color=BLUE if k == "primary" else GRAY, zorder=3)
    ax.axvline(0, color=DIM, linewidth=0.9); ax.set_yticks(y); ax.set_yticklabels([LABEL[k] for k in order], fontsize=8.2); ax.set_xlim(-0.45, 0.45); ax.set_xlabel("season-adjusted difference (stars, 95% interval)"); ax.grid(axis="y", visible=False)
    ax.set_title("Seven ways to define it: all straddle zero", fontsize=12)


def main():
    (HERE / "charts").mkdir(exist_ok=True)
    t = TE.loc["primary"]
    fig = plt.figure(figsize=(14, 8)); g = fig.add_gridspec(1, 2, width_ratios=[1.1, 1]); a = fig.add_subplot(g[0]); b = fig.add_subplot(g[1])
    se = SE; x = se["season"]; a.bar(x, se["mean_rating"], color="#2a2a2a", width=0.62, edgecolor="#3a3a3a")
    a.scatter(x, se["mean_guest"], s=70, color=BLUE, zorder=3, label="guest-star episodes"); a.scatter(x, se["mean_other"], s=70, color=ORANGE, marker="D", zorder=3, label="other episodes")
    for xi, m in zip(x, se["mean_rating"]): a.text(xi, 6.0, f"{m:.2f}", ha="center", fontsize=10, color=INK)
    a.set_ylim(5.8, 9); a.set_xticks(range(1, 10)); a.set_xlabel("season"); a.set_ylabel("mean IMDb rating (axis starts at 5.8)"); a.legend(frameon=False, labelcolor=INK, fontsize=10.5, loc="upper right"); a.set_title("The Office: season means split by guest-star episodes", fontsize=14)
    order = list(TE.index)[::-1]; y = np.arange(len(order))
    for yi, k in zip(y, order):
        r = TE.loc[k]; b.plot([r["ci_lo"], r["ci_hi"]], [yi, yi], color="#7a7a77", linewidth=2.6, zorder=2); b.scatter([r["adj_diff"]], [yi], s=70, color=BLUE if k == "primary" else GRAY, zorder=3)
    b.axvline(0, color=DIM, linewidth=0.9); b.set_yticks(y); b.set_yticklabels([LABEL[k] for k in order], fontsize=10); b.set_xlim(-0.45, 0.45); b.set_xlabel("season-adjusted difference, stars (95% bootstrap interval)"); b.grid(axis="y", visible=False)
    b.set_title("Guest-star episodes minus others, seven definitions", fontsize=14)
    fig.suptitle(f"Guest stars did not lift The Office's ratings: {t['adj_diff']:+.2f} stars within a season (95% interval {t['ci_lo']:+.2f} to {t['ci_hi']:+.2f}),\nwhile seasons 8-9 averaged {OS['mean_seasons_2_to_5'] - OS['mean_seasons_8_to_9']:.1f} stars below seasons 2-5",
                 x=0.01, ha="left", fontsize=19, color=INK, y=0.985)
    fig.tight_layout(rect=(0, 0, 1, 0.90)); fig.savefig(HERE / "charts" / "00_cover.png", dpi=100); plt.close(fig)
    for name, fn, h in (("01_seasons.png", seasons, 3.9), ("02_permutation.png", permutation, 4.0), ("03_catalogue.png", catalogue, 3.9), ("04_durations.png", durations, 3.9), ("05_countries_genres.png", countries_genres, 4.1)):
        fig, axes = plt.subplots(1, 2, figsize=(10, h)); fn(axes); save(fig, name)


if __name__ == "__main__":
    main()
