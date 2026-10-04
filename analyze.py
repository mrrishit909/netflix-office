"""Steps 2-4: audit and analysis.   ./venv/bin/python analyze.py  -> results/*.csv   (about a minute)

Part A, Netflix (netflix_titles.csv, 7,787 titles, January 2021 snapshot): audit; titles by year added; movie running time by release decade (and the 1990s question: modal length, short action films); years between release and
  addition; countries and genres (a title counts once for every country or genre it lists, so shares add to more than 100%).
Part B, The Office (US): the sample is IMDb's episode list with its averageRating (title.episode, title.basics, title.ratings). IMDb has since added three separate "Part 2" entries for double-length episodes with under 2,000 votes each
  (every other episode has 5,000 or more); they split one broadcast, so they are dropped and the 188 remaining entries match the 188 of the 2020 TidyTuesday snapshot. Guest stars come from TVmaze (guest cast per episode, hour-long episodes
  split into two halves there: the halves are merged onto the one IMDb entry; three titles need an alias).
  GUEST-STAR RULE, written down before any rating was looked at: a person credited in an episode's TVmaze guest cast, not in the show's main cast, credited in at most 3 of the 188 episodes, who is NOTABLE = has an English Wikipedia
  article (not a disambiguation page) whose Wikidata one-line description names a performer (actor, actress, comedian, singer, musician, rapper, songwriter, host, presenter, personality) or who is credited as playing themselves.
  An episode is a "guest-star episode" if it has at least one such person. Alternatives fixed in advance: cap of 1 episode, cap of 5, and no notability test at all (any credit, cap 3, which flags most episodes).
  TEST: stratified permutation. T = mean(rating - season mean | guest-star episode) - mean(rating - season mean | other episode). The guest flags are shuffled within each season (random.Random, fixed seed per
  specification, 10,000 shuffles, seasons in ascending order, episodes in air order), p = (k+1)/(10,001) with k = shuffles with |T| >= |T observed| (tolerance 1e-11, ratings carry one decimal so ties are exact). The same is done without
  the season adjustment (shuffle over all episodes). The 95% interval is a percentile bootstrap of T (episodes resampled within season, 5,000 resamples). Specifications: the rule and its three alternatives; without season/series premieres,
  finales and long episodes (IMDb runtime of 40 minutes or more); seasons 1-7 (Michael Scott era) and 8-9 alone.
  IMDb rows are never written to results/: every Office table is a season or specification aggregate.
"""
import csv
import gzip
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
D, R = HERE / "data", HERE / "results"
P = "tt0386676"
NPERM, NBOOT, MINVOTES = 10000, 5000, 2000
PERF = re.compile(r"\b(actor|actress|comedian|singer|musician|rapper|songwriter|host|presenter|personality)\b", re.I)
ALIAS = {(5, "michaelscottpapercompany"): "themichaelscottpapercompany", (6, "managerandsalesman"): "themanagerandthesalesman", (9, "newguys"): "thenewguys"}
SPECS = ["primary", "cap1", "cap5", "any_credit", "no_specials", "seasons_1_7", "seasons_8_9"]


def put(name, rows, cols):
    pd.DataFrame(rows, columns=cols).to_csv(R / f"{name}.csv", index=False, float_format="%.10g")


# ---------------------------------------------------------------- Part A: Netflix
def netflix():
    d = pd.read_csv(D / "netflix_titles.csv")
    d["added"] = pd.to_datetime(d["date_added"].str.strip(), format="%B %d, %Y")
    d["ya"] = d["added"].dt.year
    d["mins"] = d["duration"].str.extract(r"(\d+) min")[0].astype(float)
    d["gap"] = d["ya"] - d["release_year"]
    m = d["type"] == "Movie"
    aud = [("rows", len(d)), ("movies", int(m.sum())), ("tv_shows", int((~m).sum())), ("duplicate_show_id", int(d["show_id"].duplicated().sum())),
           ("duplicate_title_type_year", int(d.duplicated(["title", "type", "release_year"]).sum())), ("missing_director", int(d["director"].isna().sum())), ("missing_cast", int(d["cast"].isna().sum())),
           ("missing_country", int(d["country"].isna().sum())), ("missing_date_added", int(d["date_added"].isna().sum())), ("missing_rating", int(d["rating"].isna().sum())),
           ("date_added_with_leading_space", int(d["date_added"].dropna().str.startswith(" ").sum())), ("first_date_added", str(d["added"].min().date())), ("last_date_added", str(d["added"].max().date())),
           ("added_before_release_year", int((d["gap"] < 0).sum())), ("movies_without_minutes", int((m & d["mins"].isna()).sum())), ("tv_without_season_count", int((~m & ~d["duration"].str.contains("Season")).sum())),
           ("release_year_min", int(d["release_year"].min())), ("release_year_max", int(d["release_year"].max())),
           ("titles_added_2008_2015", int(d["ya"].between(2008, 2015).sum())), ("titles_added_2016_2020", int(d["ya"].between(2016, 2020).sum())), ("titles_added_2021", int((d["ya"] == 2021).sum())),
           ("max_titles_in_one_year_2008_2015", int(d[d["ya"].between(2008, 2015)].groupby("ya").size().max()))]
    put("netflix_audit", aud, ["check", "value"])
    ok = d[d["gap"] >= 0]
    rows = []
    for y in range(2016, 2021):
        a, g = d[d["ya"] == y], ok[ok["ya"] == y]
        gm, gt = g[g["type"] == "Movie"]["gap"], g[g["type"] == "TV Show"]["gap"]
        rows.append((y, len(a), int((a["type"] == "Movie").sum()), int((a["type"] == "TV Show").sum()), (a["type"] == "Movie").mean(), gm.median(), gt.median(), (gm <= 1).mean(), (gt <= 1).mean(), (g["release_year"] >= y - 1).mean(), len(g)))
    put("netflix_year", rows, ["year_added", "titles", "movies", "tv_shows", "movie_share", "median_gap_movies", "median_gap_tv", "movies_within_1y", "tv_within_1y", "all_within_1y", "titles_with_gap"])
    mv = d[m & d["mins"].notna()].copy(); mv["decade"] = mv["release_year"] // 10 * 10
    rows = [(int(k), len(g), g["mins"].median(), g["mins"].mean(), g["mins"].quantile(0.25), g["mins"].quantile(0.75)) for k, g in mv.groupby("decade")]
    put("netflix_decade", rows, ["decade", "movies", "median_min", "mean_min", "p25_min", "p75_min"])
    s90 = mv[mv["decade"] == 1990]; act = s90[s90["listed_in"].str.contains("Action & Adventure")]
    vc = s90["mins"].value_counts(); modes = sorted(vc[vc == vc.max()].index)
    gen = d["listed_in"].str.split(", ").explode().str.strip()
    sm = [("movies_1990s", len(s90)), ("mode_min_1990s", modes[0]), ("modes_tied_1990s", len(modes)), ("mode_count_1990s", int(vc.max())), ("median_min_1990s", s90["mins"].median()), ("mean_min_1990s", s90["mins"].mean()),
          ("action_adventure_1990s", len(act)), ("action_adventure_under_90_1990s", int((act["mins"] < 90).sum())),
          ("median_min_all_movies", mv["mins"].median()), ("share_released_2015_plus", (d["release_year"] >= 2015).mean()), ("share_released_before_2000", (d["release_year"] < 2000).mean()),
          ("movies_2010s_median_min", mv[mv["decade"] == 2010]["mins"].median()), ("movies_1980s_median_min", mv[mv["decade"] == 1980]["mins"].median()),
          ("median_gap_all", ok["gap"].median()), ("titles_with_gap", len(ok))]
    put("netflix_summary", sm, ["key", "value"])
    b = (s90["mins"] // 10 * 10).astype(int).value_counts()
    put("netflix_hist90", [(lo, int(b.get(lo, 0))) for lo in range(int(b.index.min()), int(b.index.max()) + 10, 10)], ["bin_lo", "movies"])
    c = d.dropna(subset=["country"]).copy(); c["c"] = c["country"].str.split(",")
    c = c.explode("c"); c["c"] = c["c"].str.strip(); c = c[c["c"] != ""]
    top = list(c.groupby("c")["show_id"].nunique().sort_values(ascending=False, kind="stable").index[:6])
    rows = []
    for y in range(2016, 2021):
        den = d[(d["ya"] == y) & d["country"].notna()]["show_id"].nunique()
        for k in top:
            n = c[(c["ya"] == y) & (c["c"] == k)]["show_id"].nunique(); rows.append((k, y, n, den, n / den))
    put("netflix_country", rows, ["country", "year_added", "titles", "titles_with_country", "share"])
    g = d.copy(); g["g"] = g["listed_in"].str.split(","); g = g.explode("g"); g["g"] = g["g"].str.strip()
    topg = list(g.groupby("g")["show_id"].nunique().sort_values(ascending=False, kind="stable").index[:9])
    rows = []
    for k in topg:
        a = g[(g["ya"].isin([2016, 2017])) & (g["g"] == k)]["show_id"].nunique(); b = g[(g["ya"].isin([2019, 2020])) & (g["g"] == k)]["show_id"].nunique()
        na, nb = int(d["ya"].isin([2016, 2017]).sum()), int(d["ya"].isin([2019, 2020]).sum())
        rows.append((k, g[g["g"] == k]["show_id"].nunique(), a, na, a / na, b, nb, b / nb))
    put("netflix_genre", rows, ["genre", "titles_all", "titles_2016_17", "n_2016_17", "share_2016_17", "titles_2019_20", "n_2019_20", "share_2019_20"])


# ---------------------------------------------------------------- Part B: The Office
def tsv(name):
    with gzip.open(D / name, "rt", encoding="utf-8") as f:
        r = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE); next(r)
        yield from r


def split_title(t):
    t = t.replace("’", "'").strip(); m = re.search(r"(?:\s*\(([12])\)|[:,]?\s+Part\s+([12]))$", t); part = None
    if m: part = int(m.group(1) or m.group(2)); t = t[:m.start()]
    return re.sub(r"[^a-z0-9]", "", t.lower()), part


def build_office():
    epi = {r[0]: (int(r[2]), int(r[3])) for r in tsv("title.episode.tsv.gz") if r[1] == P}
    bas = {r[0]: r for r in tsv("title.basics.tsv.gz") if r[0] in epi}
    rat = {r[0]: r for r in tsv("title.ratings.tsv.gz") if r[0] in epi}
    dropped = [t for t in epi if int(rat[t][2]) < MINVOTES]
    assert len(dropped) == 3 and all(re.search(r"Part 2", bas[t][2]) for t in dropped)
    gone = {(epi[t][0], split_title(bas[t][2])[0]) for t in dropped}
    eps = []
    for t, (s, e) in sorted(epi.items(), key=lambda kv: kv[1]):
        if t in dropped: continue
        b, p = split_title(bas[t][2])
        if p == 1 and (s, b) in gone: p = None                 # its second half was dropped: this entry stands for the whole broadcast
        eps.append(dict(t=t, s=s, e=e, name=bas[t][2], b=b, p=p, rt=int(round(float(rat[t][1]) * 10)), v=int(rat[t][2]), run=int(bas[t][7]) if bas[t][7] != "\\N" else 0))
    tv = [x for x in json.load(open(D / "tvmaze_episodes.json")) if x["type"] == "regular"]
    gc = json.load(open(D / "tvmaze_guestcast.json")); mains = {c["person"]["id"] for c in json.load(open(D / "tvmaze_cast.json"))}
    key = defaultdict(list)
    for x in tv:
        b, p = split_title(x["name"]); key[(x["season"], b)].append((p, x))
    used = set()
    for ep in eps:
        m = [x for q, x in key.get((ep["s"], ALIAS.get((ep["s"], ep["b"]), ep["b"])), []) if ep["p"] is None or q == ep["p"]]
        assert m, ep; used |= {x["id"] for x in m}
        ep["cr"] = {}
        for x in m:
            for c in gc[str(x["id"])]: ep["cr"].setdefault(c["person"]["id"], c)
    assert used == {x["id"] for x in tv}
    cnt = Counter(pid for ep in eps for pid in ep["cr"])
    w = json.load(open(D / "wikipedia_names.json")); names = sorted({c["person"]["name"] for v in gc.values() for c in v}); info = {}
    for b, bn in zip(w, [names[i:i + 50] for i in range(0, len(names), 50)]):
        q = b["query"]; nm = {x["from"]: x["to"] for x in q.get("normalized", [])}; rd = {x["from"]: x["to"] for x in q.get("redirects", [])}; pg = {p["title"]: p for p in q["pages"]}
        for n in bn:
            t = nm.get(n, n); t = rd.get(t, t); p = pg[t]
            info[n] = ((not p.get("missing", False)) and "disambiguation" not in p.get("pageprops", {}), p.get("description") or "")

    def notable(c):
        ok, desc = info[c["person"]["name"]]
        return ok and (bool(PERF.search(desc)) or bool(c["self"]))
    for ep in eps:
        cr = ep["cr"]
        def flag(cap, need_notable):
            return int(any(p not in mains and cnt[p] <= cap and (notable(c) or not need_notable) for p, c in cr.items()))
        ep["primary"], ep["cap1"], ep["cap5"], ep["any_credit"] = flag(3, True), flag(1, True), flag(5, True), flag(3, False)
    return eps, dict(tv=len(tv), dropped=len(dropped), mains=len(mains), persons=len(names), notable_persons=sum(1 for n in names if info[n][0] and PERF.search(info[n][1])), empty=sum(1 for ep in eps if not ep["cr"]),
                     cnt=cnt, gc_persons=len({p for ep in eps for p in ep["cr"]}))


def stat_adj(rt, fl, ss):
    """mean residual (rating minus season mean) of flagged episodes minus the others; None if a group is empty."""
    rt, fl, ss = np.asarray(rt, float), np.asarray(fl, bool), np.asarray(ss)
    res = rt.copy()
    for s in set(ss): res[ss == s] -= rt[ss == s].mean()
    return None if fl.all() or not fl.any() else (res[fl].mean() - res[~fl].mean()) / 10


def run_spec(name, rows, flagkey):
    rows = sorted(rows, key=lambda r: (r["s"], r["e"])); ss = np.array([r["s"] for r in rows]); rt = np.array([r["rt"] for r in rows], float); fl = np.array([r[flagkey] for r in rows])
    seasons = sorted(set(ss)); idx = {s: np.where(ss == s)[0] for s in seasons}
    obs, raw = stat_adj(rt, fl, ss), (rt[fl == 1].mean() - rt[fl == 0].mean()) / 10
    rng = random.Random(f"netflix-office|{name}|adj"); null, k = [], 0
    for _ in range(NPERM):
        f = np.zeros(len(rows), int)
        for s in seasons:
            l = list(fl[idx[s]]); rng.shuffle(l); f[idx[s]] = l
        t = stat_adj(rt, f, ss); null.append(t); k += abs(t) >= abs(obs) - 1e-11
    rng = random.Random(f"netflix-office|{name}|raw"); kr = 0
    for _ in range(NPERM):
        l = list(fl); rng.shuffle(l); f = np.array(l); t = (rt[f == 1].mean() - rt[f == 0].mean()) / 10; kr += abs(t) >= abs(raw) - 1e-11
    rng = random.Random(f"netflix-office|{name}|boot"); bs = []
    for _ in range(NBOOT):
        pick = np.concatenate([idx[s][[rng.randrange(len(idx[s])) for _ in range(len(idx[s]))]] for s in seasons])
        t = stat_adj(rt[pick], fl[pick], ss[pick])
        if t is not None: bs.append(t)
    bs.sort(); nulls = sorted(null)
    return dict(spec=name, n=len(rows), n_guest=int(fl.sum()), n_other=int((1 - fl).sum()), guest_share=fl.mean(), raw_diff=raw, raw_p=(kr + 1) / (NPERM + 1), adj_diff=obs, adj_p=(k + 1) / (NPERM + 1), perm_k=int(k),
                null_lo=nulls[int(0.025 * NPERM)], null_hi=nulls[int(0.975 * NPERM)], ci_lo=bs[int(0.025 * len(bs))], ci_hi=bs[min(int(0.975 * len(bs)), len(bs) - 1)], boots=len(bs)), null


def office():
    eps, meta = build_office()
    tt = pd.read_csv(D / "office_ratings.csv")
    tkey = {(int(r.season), split_title(r.title)[0], split_title(r.title)[1]): r for r in tt.itertuples()}
    drift, votes, matched = [], [], 0
    for ep in eps:
        r = tkey.get((ep["s"], ep["b"], ep["p"])) or tkey.get((ep["s"], ep["b"], None)) or tkey.get((ep["s"], ep["b"].replace("andthe", "and"), ep["p"]))
        if r is None: continue
        matched += 1; drift.append(abs(ep["rt"] / 10 - r.imdb_rating)); votes.append(ep["v"] / r.total_votes)
    n = len(eps); aud = [("imdb_episode_entries", n + meta["dropped"]), ("dropped_low_vote_part2_entries", meta["dropped"]), ("episodes_in_sample", n), ("tvmaze_regular_episodes", meta["tv"]), ("tvmaze_main_cast", meta["mains"]),
                         ("tvmaze_guest_cast_persons", meta["gc_persons"]), ("episodes_with_empty_guest_cast", meta["empty"]), ("guest_names_checked_on_wikipedia", meta["persons"]), ("names_with_performer_article", meta["notable_persons"]),
                         ("tidytuesday_rows", len(tt)), ("tidytuesday_matched", matched), ("tt_mean_abs_rating_change_since_2020", float(np.mean(drift))), ("tt_share_rating_unchanged", float(np.mean([x < 1e-9 for x in drift]))),
                         ("tt_max_abs_rating_change", float(np.max(drift))), ("tt_median_votes_ratio_now_vs_2020", float(np.median(votes)))]
    for k in ("primary", "cap1", "cap5", "any_credit"): aud.append((f"episodes_flagged_{k}", sum(ep[k] for ep in eps)))
    put("office_audit", aud, ["check", "value"])
    rows = []
    for s in sorted({ep["s"] for ep in eps}):
        g = [ep for ep in eps if ep["s"] == s]; gu = [ep["rt"] for ep in g if ep["primary"]]; ot = [ep["rt"] for ep in g if not ep["primary"]]; rr = [ep["rt"] / 10 for ep in g]
        rows.append((s, len(g), np.mean(rr), np.std(rr, ddof=1), np.mean([ep["v"] for ep in g]), len(gu), len(gu) / len(g), np.mean(gu) / 10 if gu else np.nan, np.mean(ot) / 10 if ot else np.nan))
    put("office_seasons", rows, ["season", "episodes", "mean_rating", "sd_rating", "mean_votes", "guest_episodes", "guest_share", "mean_guest", "mean_other"])
    last = max(eps, key=lambda e: (e["s"], e["e"])); allr = sorted([ep["rt"] for ep in eps], reverse=True)
    s9 = [ep["rt"] for ep in eps if ep["s"] == 9 and ep is not last]
    sm = {s: np.mean([ep["rt"] for ep in eps if ep["s"] == s]) / 10 for s in range(1, 10)}
    sp = [("finale_rank_by_rating", 1 + sum(1 for r in allr if r > last["rt"])), ("finale_tied_at_that_rank", sum(1 for r in allr if r == last["rt"])), ("finale_minus_season_mean", last["rt"] / 10 - sm[9]),
          ("season9_mean_without_finale", np.mean(s9) / 10), ("finale_votes_vs_median_episode_votes", last["v"] / float(np.median([ep["v"] for ep in eps]))),
          ("mean_seasons_2_to_5", np.mean([ep["rt"] for ep in eps if 2 <= ep["s"] <= 5]) / 10), ("mean_seasons_8_to_9", np.mean([ep["rt"] for ep in eps if ep["s"] >= 8]) / 10),
          ("best_season", max(sm, key=sm.get)), ("worst_season", min(sm, key=sm.get)), ("episodes_below_season_2_to_5_mean_in_8_9", sum(1 for ep in eps if ep["s"] >= 8 and ep["rt"] / 10 < np.mean([e["rt"] for e in eps if 2 <= e["s"] <= 5]) / 10)),
          ("episodes_8_9", sum(1 for ep in eps if ep["s"] >= 8))]
    put("office_summary", sp, ["key", "value"])
    # specifications
    def flag_special(ep):
        grp = [e for e in eps if e["s"] == ep["s"]]
        return ep["e"] == min(e["e"] for e in grp) or ep["e"] == max(e["e"] for e in grp) or ep["run"] >= 40
    sets = {"primary": (eps, "primary"), "cap1": (eps, "cap1"), "cap5": (eps, "cap5"), "any_credit": (eps, "any_credit"), "no_specials": ([e for e in eps if not flag_special(e)], "primary"),
            "seasons_1_7": ([e for e in eps if e["s"] <= 7], "primary"), "seasons_8_9": ([e for e in eps if e["s"] >= 8], "primary")}
    out, null0 = [], None
    for name in SPECS:
        r, null = run_spec(name, *sets[name]); out.append(r)
        if name == "primary": null0 = null
    put("office_tests", [[r[k] for k in out[0]] for r in out], list(out[0]))
    edges = np.linspace(-0.5125, 0.5125, 42); h = np.histogram(np.round(null0, 9), bins=edges)[0]    # 41 bins of width 0.025 centred on multiples of 0.025
    put("office_null", [(edges[i], edges[i + 1], int(h[i])) for i in range(41)], ["bin_lo", "bin_hi", "count"])
    print(json.dumps({"primary": out[0]}, default=float))


def main():
    R.mkdir(exist_ok=True)
    netflix(); office()
    print("analyze.py: wrote", ", ".join(sorted(p.name for p in R.glob("*.csv"))))


if __name__ == "__main__":
    main()
