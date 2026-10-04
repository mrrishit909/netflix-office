"""Step 5: the project's check. Recompute with different code, in plain Python straight from the downloaded files (csv, gzip, json, math, random, fractions and loops: no pandas, numpy or scipy), and compare with results/:

    ./venv/bin/python check.py

Netflix: the audit, the titles by year added, running time by release decade (with linear-interpolation quartiles), the 1990s questions, countries and genres.
The Office: the sample (IMDb episodes, the three dropped half-entries, the TVmaze merge, the guest-star rule), the audit, the season table, the finale and decline facts, the cross-check with the 2020 snapshot, and for each of the 7
specifications the observed differences, the stratified permutation p-values (the same random.Random streams and shuffle order as analyze.py, but each permuted statistic is an exact Fraction, so ties cannot flip), the null
quantiles, the bootstrap interval and the null histogram. Counts are compared exactly, everything else at a relative tolerance of 1e-8.
"""
import csv
import gzip
import json
import math
import random
import re
from collections import Counter, defaultdict
from datetime import datetime
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).parent
D, R = HERE / "data", HERE / "results"
P = "tt0386676"
NPERM, NBOOT = 10000, 5000
n_ok = 0


def same(label, got, want, rel=1e-8):
    global n_ok
    n_ok += 1
    try:
        want = float(want)
    except ValueError:
        assert str(got) == want, f"{label}: recount {got} != results {want}"; return
    assert abs(float(got) - want) <= rel * abs(want) + 1e-12, f"{label}: recount {got} != results {want}"


def table(name):
    return list(csv.DictReader(open(R / f"{name}.csv")))


def kv(name):
    return {r["check" if "check" in r else "key"]: r["value"] for r in table(name)}


def mean(v):
    return sum(v) / len(v)


def median(v):
    s = sorted(v); n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def quantile(v, p):
    s = sorted(v); pos = (len(s) - 1) * p; lo = int(math.floor(pos)); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


# ------------------------------------------------------------------ Netflix
def netflix():
    rows = list(csv.DictReader(open(D / "netflix_titles.csv", encoding="utf-8")))
    for r in rows:
        r["ya"] = datetime.strptime(r["date_added"].strip(), "%B %d, %Y").year if r["date_added"] else None
        r["ry"] = int(r["release_year"]); r["gap"] = r["ya"] - r["ry"] if r["ya"] else None
        mm = re.match(r"(\d+) min", r["duration"]); r["mins"] = int(mm.group(1)) if mm else None; r["movie"] = r["type"] == "Movie"
    a = kv("netflix_audit"); n = len(rows)
    dates = sorted(datetime.strptime(r["date_added"].strip(), "%B %d, %Y") for r in rows if r["date_added"])
    chk = {"rows": n, "movies": sum(r["movie"] for r in rows), "tv_shows": sum(not r["movie"] for r in rows), "duplicate_show_id": n - len({r["show_id"] for r in rows}),
           "duplicate_title_type_year": n - len({(r["title"], r["type"], r["release_year"]) for r in rows}), "missing_director": sum(r["director"] == "" for r in rows), "missing_cast": sum(r["cast"] == "" for r in rows),
           "missing_country": sum(r["country"] == "" for r in rows), "missing_date_added": sum(r["date_added"] == "" for r in rows), "missing_rating": sum(r["rating"] == "" for r in rows),
           "date_added_with_leading_space": sum(r["date_added"].startswith(" ") for r in rows), "added_before_release_year": sum(1 for r in rows if r["gap"] is not None and r["gap"] < 0),
           "movies_without_minutes": sum(r["movie"] and r["mins"] is None for r in rows), "tv_without_season_count": sum((not r["movie"]) and "Season" not in r["duration"] for r in rows),
           "release_year_min": min(r["ry"] for r in rows), "release_year_max": max(r["ry"] for r in rows), "titles_added_2008_2015": sum(1 for r in rows if r["ya"] and 2008 <= r["ya"] <= 2015),
           "titles_added_2016_2020": sum(1 for r in rows if r["ya"] and 2016 <= r["ya"] <= 2020), "titles_added_2021": sum(1 for r in rows if r["ya"] == 2021),
           "max_titles_in_one_year_2008_2015": max(Counter(r["ya"] for r in rows if r["ya"] and 2008 <= r["ya"] <= 2015).values()),
           "first_date_added": str(dates[0].date()), "last_date_added": str(dates[-1].date())}
    for k, v in chk.items(): same(f"netflix_audit {k}", v, a[k])
    ok = [r for r in rows if r["gap"] is not None and r["gap"] >= 0]
    for t in table("netflix_year"):
        y = int(t["year_added"]); al = [r for r in rows if r["ya"] == y]; g = [r for r in ok if r["ya"] == y]; gm = [r["gap"] for r in g if r["movie"]]; gt = [r["gap"] for r in g if not r["movie"]]
        for k, v in (("titles", len(al)), ("movies", sum(r["movie"] for r in al)), ("tv_shows", sum(not r["movie"] for r in al)), ("movie_share", sum(r["movie"] for r in al) / len(al)), ("median_gap_movies", median(gm)),
                     ("median_gap_tv", median(gt)), ("movies_within_1y", sum(x <= 1 for x in gm) / len(gm)), ("tv_within_1y", sum(x <= 1 for x in gt) / len(gt)), ("all_within_1y", sum(r["ry"] >= y - 1 for r in g) / len(g)), ("titles_with_gap", len(g))):
            same(f"netflix_year {y} {k}", v, t[k])
    mv = [r for r in rows if r["movie"] and r["mins"] is not None]; dec = defaultdict(list)
    for r in mv: dec[r["ry"] // 10 * 10].append(r["mins"])
    t = table("netflix_decade"); assert [int(x["decade"]) for x in t] == sorted(dec), "decades differ"
    for x in t:
        v = dec[int(x["decade"])]
        for k, w in (("movies", len(v)), ("median_min", median(v)), ("mean_min", mean(v)), ("p25_min", quantile(v, .25)), ("p75_min", quantile(v, .75))): same(f"netflix_decade {x['decade']} {k}", w, x[k])
    s90 = [r for r in mv if 1990 <= r["ry"] <= 1999]; c90 = Counter(r["mins"] for r in s90); top = max(c90.values()); modes = sorted(m for m, c in c90.items() if c == top)
    act = [r for r in s90 if "Action & Adventure" in r["listed_in"]]
    s = kv("netflix_summary")
    for k, v in (("movies_1990s", len(s90)), ("mode_min_1990s", modes[0]), ("modes_tied_1990s", len(modes)), ("mode_count_1990s", top), ("median_min_1990s", median([r["mins"] for r in s90])), ("mean_min_1990s", mean([r["mins"] for r in s90])),
                 ("action_adventure_1990s", len(act)), ("action_adventure_under_90_1990s", sum(r["mins"] < 90 for r in act)), ("median_min_all_movies", median([r["mins"] for r in mv])),
                 ("share_released_2015_plus", sum(r["ry"] >= 2015 for r in rows) / n), ("share_released_before_2000", sum(r["ry"] < 2000 for r in rows) / n), ("movies_2010s_median_min", median(dec[2010])),
                 ("movies_1980s_median_min", median(dec[1980])), ("median_gap_all", median([r["gap"] for r in ok])), ("titles_with_gap", len(ok))):
        same(f"netflix_summary {k}", v, s[k])
    hb = Counter(r["mins"] // 10 * 10 for r in s90); th = table("netflix_hist90")
    assert [int(x["bin_lo"]) for x in th] == list(range(min(hb), max(hb) + 10, 10)), "histogram bins differ"
    for x in th: same(f"netflix_hist90 {x['bin_lo']}", hb.get(int(x["bin_lo"]), 0), x["movies"])
    lists = lambda col, r: sorted({x.strip() for x in r[col].split(",") if x.strip()})
    cc = Counter(c for r in rows for c in lists("country", r)); topc = [c for c, _ in sorted(cc.items(), key=lambda kv_: (-kv_[1], kv_[0]))[:6]]
    tc = table("netflix_country"); assert [x["country"] for x in tc[:6]] == topc, "top countries differ"
    for x in tc:
        y = int(x["year_added"]); yr = [r for r in rows if r["ya"] == y]; den = sum(r["country"] != "" for r in yr); nn = sum(x["country"] in lists("country", r) for r in yr)
        same(f"netflix_country {x['country']} {y} titles", nn, x["titles"]); same("netflix_country den", den, x["titles_with_country"]); same("netflix_country share", nn / den, x["share"])
    gcn = Counter(g for r in rows for g in lists("listed_in", r)); topg = [g for g, _ in sorted(gcn.items(), key=lambda kv_: (-kv_[1], kv_[0]))[:9]]
    tg = table("netflix_genre"); assert [x["genre"] for x in tg] == topg, "top genres differ"
    ra, rb = [r for r in rows if r["ya"] in (2016, 2017)], [r for r in rows if r["ya"] in (2019, 2020)]
    for x in tg:
        g = x["genre"]; na = sum(g in lists("listed_in", r) for r in ra); nb = sum(g in lists("listed_in", r) for r in rb)
        for k, v in (("titles_all", gcn[g]), ("titles_2016_17", na), ("n_2016_17", len(ra)), ("share_2016_17", na / len(ra)), ("titles_2019_20", nb), ("n_2019_20", len(rb)), ("share_2019_20", nb / len(rb))): same(f"netflix_genre {g} {k}", v, x[k])


# ------------------------------------------------------------------ The Office
def tsv(name):
    with gzip.open(D / name, "rt", encoding="utf-8") as f:
        for line in f:
            yield line.rstrip("\n").split("\t")


def parse_title(t):
    t = t.replace("’", "'").strip(); part = None
    m = re.match(r"^(.*?)(?:\s*\((\d)\)|[:,]?\s+Part\s+(\d))$", t)
    if m: t, part = m.group(1), int(m.group(2) or m.group(3))
    return "".join(ch for ch in t.lower() if ch.isalnum() and ch.isascii()), part


def office():
    epi = {}
    for r in tsv("title.episode.tsv.gz"):
        if r[1] == P: epi[r[0]] = (int(r[2]), int(r[3]))
    info = {}
    for r in tsv("title.basics.tsv.gz"):
        if r[0] in epi: info[r[0]] = [r[2], r[7]]
    for r in tsv("title.ratings.tsv.gz"):
        if r[0] in epi: info[r[0]] += [r[1], int(r[2])]
    small = [t for t in epi if info[t][3] < 2000]; assert len(small) == 3 and all("Part 2" in info[t][0] for t in small)
    gone = {(epi[t][0], parse_title(info[t][0])[0]) for t in small}
    eps = []
    for t in sorted((t for t in epi if t not in small), key=lambda t: epi[t]):
        b, p = parse_title(info[t][0])
        if p == 1 and (epi[t][0], b) in gone: p = None
        eps.append({"s": epi[t][0], "e": epi[t][1], "b": b, "p": p, "rt": round(float(info[t][2]) * 10), "v": info[t][3], "run": 0 if info[t][1] == "\\N" else int(info[t][1])})
    tv = [x for x in json.load(open(D / "tvmaze_episodes.json")) if x["type"] == "regular"]; gc = json.load(open(D / "tvmaze_guestcast.json")); mains = {c["person"]["id"] for c in json.load(open(D / "tvmaze_cast.json"))}
    alias = {(5, "michaelscottpapercompany"): "themichaelscottpapercompany", (6, "managerandsalesman"): "themanagerandthesalesman", (9, "newguys"): "thenewguys"}; used = set()
    for ep in eps:
        want = alias.get((ep["s"], ep["b"]), ep["b"]); ep["cr"] = {}
        found = [x for x in tv if x["season"] == ep["s"] and parse_title(x["name"])[0] == want and (ep["p"] is None or parse_title(x["name"])[1] == ep["p"])]
        assert found; used |= {x["id"] for x in found}
        for x in found:
            for c in gc[str(x["id"])]:
                if c["person"]["id"] not in ep["cr"]: ep["cr"][c["person"]["id"]] = c
    assert used == {x["id"] for x in tv}
    cnt = Counter(p for ep in eps for p in ep["cr"]); names = sorted({c["person"]["name"] for v in gc.values() for c in v}); art = {}
    for b, i in zip(json.load(open(D / "wikipedia_names.json")), range(0, len(names), 50)):
        q = b["query"]; frm = {}
        for k in ("normalized", "redirects"):
            for x in q.get(k, []): frm.setdefault(k, {})[x["from"]] = x["to"]
        pages = {p["title"]: p for p in q["pages"]}
        for nme in names[i:i + 50]:
            t = frm.get("normalized", {}).get(nme, nme); t = frm.get("redirects", {}).get(t, t); pg = pages[t]
            art[nme] = (not pg.get("missing", False) and "disambiguation" not in pg.get("pageprops", {}), pg.get("description") or "")
    perf = re.compile(r"\b(actor|actress|comedian|singer|musician|rapper|songwriter|host|presenter|personality)\b", re.I)
    def notable(c): ok, desc = art[c["person"]["name"]]; return ok and (perf.search(desc) is not None or c["self"] is True)
    for ep in eps:
        def fl(cap, need): return int(any(p not in mains and cnt[p] <= cap and (not need or notable(c)) for p, c in ep["cr"].items()))
        ep["primary"], ep["cap1"], ep["cap5"], ep["any_credit"] = fl(3, 1), fl(1, 1), fl(5, 1), fl(3, 0)
    n = len(eps); a = kv("office_audit")
    tt = list(csv.DictReader(open(D / "office_ratings.csv"))); ttk = {}
    for r in tt:
        b, p = parse_title(r["title"]); ttk[(int(r["season"]), b, p)] = r
    drift, ratio = [], []
    for ep in eps:
        r = ttk.get((ep["s"], ep["b"], ep["p"])) or ttk.get((ep["s"], ep["b"], None)) or ttk.get((ep["s"], ep["b"].replace("andthe", "and"), ep["p"]))
        if r: drift.append(abs(ep["rt"] / 10 - float(r["imdb_rating"]))); ratio.append(ep["v"] / float(r["total_votes"]))
    chk = {"imdb_episode_entries": len(epi), "dropped_low_vote_part2_entries": len(small), "episodes_in_sample": n, "tvmaze_regular_episodes": len(tv), "tvmaze_main_cast": len(mains), "tvmaze_guest_cast_persons": len(cnt),
           "episodes_with_empty_guest_cast": sum(not ep["cr"] for ep in eps), "guest_names_checked_on_wikipedia": len(names), "names_with_performer_article": sum(1 for x in names if art[x][0] and perf.search(art[x][1])),
           "tidytuesday_rows": len(tt), "tidytuesday_matched": len(drift), "tt_mean_abs_rating_change_since_2020": mean(drift), "tt_share_rating_unchanged": sum(x < 1e-9 for x in drift) / len(drift), "tt_max_abs_rating_change": max(drift),
           "tt_median_votes_ratio_now_vs_2020": median(ratio)}
    for k in ("primary", "cap1", "cap5", "any_credit"): chk[f"episodes_flagged_{k}"] = sum(ep[k] for ep in eps)
    for k, v in chk.items(): same(f"office_audit {k}", v, a[k])
    for t in table("office_seasons"):
        g = [ep for ep in eps if ep["s"] == int(t["season"])]; r = [ep["rt"] / 10 for ep in g]; m = mean(r); gu = [ep["rt"] / 10 for ep in g if ep["primary"]]; ot = [ep["rt"] / 10 for ep in g if not ep["primary"]]
        for k, v in (("episodes", len(g)), ("mean_rating", m), ("sd_rating", math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1))), ("mean_votes", mean([ep["v"] for ep in g])), ("guest_episodes", len(gu)), ("guest_share", len(gu) / len(g)),
                     ("mean_guest", mean(gu)), ("mean_other", mean(ot))): same(f"office_seasons {t['season']} {k}", v, t[k])
    last = max(eps, key=lambda e: (e["s"], e["e"])); sm = {s: mean([ep["rt"] for ep in eps if ep["s"] == s]) / 10 for s in range(1, 10)}; m25 = mean([ep["rt"] for ep in eps if 2 <= ep["s"] <= 5]) / 10
    s = kv("office_summary")
    for k, v in (("finale_rank_by_rating", 1 + sum(ep["rt"] > last["rt"] for ep in eps)), ("finale_tied_at_that_rank", sum(ep["rt"] == last["rt"] for ep in eps)), ("finale_minus_season_mean", last["rt"] / 10 - sm[9]),
                 ("season9_mean_without_finale", mean([ep["rt"] for ep in eps if ep["s"] == 9 and ep is not last]) / 10), ("finale_votes_vs_median_episode_votes", last["v"] / median([ep["v"] for ep in eps])),
                 ("mean_seasons_2_to_5", m25), ("mean_seasons_8_to_9", mean([ep["rt"] for ep in eps if ep["s"] >= 8]) / 10), ("best_season", max(sm, key=sm.get)), ("worst_season", min(sm, key=sm.get)),
                 ("episodes_below_season_2_to_5_mean_in_8_9", sum(1 for ep in eps if ep["s"] >= 8 and ep["rt"] / 10 < m25)), ("episodes_8_9", sum(ep["s"] >= 8 for ep in eps))):
        same(f"office_summary {k}", v, s[k])

    def special(ep):
        es = [e["e"] for e in eps if e["s"] == ep["s"]]; return ep["e"] in (min(es), max(es)) or ep["run"] >= 40
    sets = {"primary": (eps, "primary"), "cap1": (eps, "cap1"), "cap5": (eps, "cap5"), "any_credit": (eps, "any_credit"), "no_specials": ([e for e in eps if not special(e)], "primary"),
            "seasons_1_7": ([e for e in eps if e["s"] <= 7], "primary"), "seasons_8_9": ([e for e in eps if e["s"] >= 8], "primary")}
    tests = {t["spec"]: t for t in table("office_tests")}; assert list(tests) == list(sets), "specifications differ"
    for name, (rows, key) in sets.items():
        rows = sorted(rows, key=lambda r: (r["s"], r["e"])); seasons = sorted({r["s"] for r in rows}); by = {s: ([r["rt"] for r in rows if r["s"] == s], [r[key] for r in rows if r["s"] == s]) for s in seasons}
        flags = [r[key] for r in rows]; rts = [r["rt"] for r in rows]; ng = sum(flags); no = len(rows) - ng; w = Fraction(1, ng) + Fraction(1, no)
        C = sum(sum(by[s][1]) * Fraction(sum(by[s][0]), len(by[s][0])) for s in seasons); obs = sum(x for x, f in zip(rts, flags) if f) - C
        rawobs = sum(x for x, f in zip(rts, flags) if f) * w - Fraction(sum(rts), no)
        rng = random.Random(f"netflix-office|{name}|adj"); k, nulls = 0, []
        for _ in range(NPERM):
            tot = 0
            for s in seasons:
                l = by[s][1][:]; rng.shuffle(l); tot += sum(x for x, f in zip(by[s][0], l) if f)
            dev = tot - C; k += abs(dev) >= abs(obs); nulls.append(dev)
        rng = random.Random(f"netflix-office|{name}|raw"); kr = 0
        for _ in range(NPERM):
            l = flags[:]; rng.shuffle(l); kr += abs(sum(x for x, f in zip(rts, l) if f) * w - Fraction(sum(rts), no)) >= abs(rawobs)
        rng = random.Random(f"netflix-office|{name}|boot"); bs = []
        for _ in range(NBOOT):
            samp = []
            for s in seasons:
                lst = list(zip(*by[s])); ns = len(lst); dr = [lst[rng.randrange(ns)] for _ in range(ns)]; mu = mean([x for x, f in dr]); samp += [(x - mu, f) for x, f in dr]
            g = [x for x, f in samp if f]; o = [x for x, f in samp if not f]
            if g and o: bs.append((mean(g) - mean(o)) / 10)
        bs.sort(); nulls.sort(); t = tests[name]
        for kk, v in (("n", len(rows)), ("n_guest", ng), ("n_other", no), ("guest_share", ng / len(rows)), ("raw_diff", float(rawobs) / 10), ("raw_p", (kr + 1) / (NPERM + 1)), ("adj_diff", float(obs * w) / 10), ("adj_p", (k + 1) / (NPERM + 1)),
                      ("perm_k", k), ("null_lo", float(nulls[int(0.025 * NPERM)] * w) / 10), ("null_hi", float(nulls[int(0.975 * NPERM)] * w) / 10), ("ci_lo", bs[int(0.025 * len(bs))]),
                      ("ci_hi", bs[min(int(0.975 * len(bs)), len(bs) - 1)]), ("boots", len(bs))):
            same(f"office_tests {name} {kk}", v, t[kk])
        if name == "primary":
            hist = [0] * 41
            for dev in nulls: hist[int(math.floor((round(float(dev * w) / 10, 9) + 0.5125) / 0.025))] += 1
            for i, x in enumerate(table("office_null")): same(f"office_null bin {i}", hist[i], x["count"])


def main():
    netflix(); office()
    print(f"check.py: {n_ok} recomputed numbers agree with results/")


if __name__ == "__main__":
    main()
