"""Step 1: fetch the raw files.

    ./venv/bin/python download.py   -> data/*, results/pull.json   (download.py wiki: only the Wikipedia step)

Netflix: netflix_titles.csv, 7,787 titles as of January 2021, the TidyTuesday 2021-04-20 copy
  (github.com/rfordatascience/tidytuesday) of the Kaggle dataset "Netflix Movies and TV Shows" by Shivam Bansal
  (kaggle.com/datasets/shivamb/netflix-shows), collected from the Flixable search engine. Kaggle's public metadata states the licence: CC0 Public Domain.
The Office (US) ratings: IMDb's official non-commercial datasets, https://datasets.imdbws.com/ (title.basics, title.episode, title.ratings; refreshed daily).
  Licence: personal and non-commercial use, local copies allowed, see https://developer.imdb.com/non-commercial-datasets/. This repository therefore publishes
  AGGREGATES only (season and group summaries, test results), never episode-by-episode IMDb rows. Information courtesy of IMDb (https://www.imdb.com).
  Cross-check: office_ratings.csv, the TidyTuesday 2020-03-17 snapshot of IMDb episode ratings (the origin, data.world, states no licence we could verify, so it is used only
  to measure how much ratings moved since March 2020 and only that aggregate is published).
Guest stars: the TVmaze API (api.tvmaze.com), show 526 (The Office, NBC), its main cast and every episode's guest cast. TVmaze's API terms: CC BY-SA, attribution required
  (https://www.tvmaze.com/api#licensing); 20 calls per 10 seconds, we stay under it. Wikipedia and Wikidata have no per-episode guest list, IMDb's title.principals only
  the ten top-billed credits (the regulars), and Fandom sits behind a bot challenge, so TVmaze is the one open source with a guest list per episode.
Notability of a guest: whether the name has an English Wikipedia article about a person (existence, the page is not a disambiguation page, and its Wikidata short description names an occupation),
  asked from the MediaWiki API (titles in batches of 50); only existence and the one-line description are used, no article text.
Nothing under data/ is committed; results/pull.json holds the URLs, sizes and sha256 of the files the results were computed from (IMDb replaces its files every day, so a new
download moves the Office numbers slightly).
"""
import hashlib
import json
import sys
import ssl
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import certifi

HERE = Path(__file__).parent
TT = "https://raw.githubusercontent.com/rfordatascience/tidytuesday/main/data"
UA = "research-portfolio (Rishit Raj Mathur)"
FILES = {"netflix_titles.csv": f"{TT}/2021/2021-04-20/netflix_titles.csv", "office_ratings.csv": f"{TT}/2020/2020-03-17/office_ratings.csv",
         **{f"{n}.tsv.gz": f"https://datasets.imdbws.com/{n}.tsv.gz" for n in ("title.basics", "title.episode", "title.ratings")}}
SHOW = 526
CTX = ssl.create_default_context(cafile=certifi.where())


def get(url, tries=5):
    for attempt in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), context=CTX, timeout=120).read()
        except OSError:
            if attempt == tries - 1: raise
            time.sleep(10 * (attempt + 1))                 # a 429 from TVmaze arrives as an HTTPError (an OSError): back off and retry


def wiki_names(keep):
    """Ask Wikipedia whether each guest-cast name is a person with an article (batches of 50 titles per call)."""
    guest = json.loads((HERE / "data" / "tvmaze_guestcast.json").read_text())
    names = sorted({c["person"]["name"] for v in guest.values() for c in v})
    out = []
    for i in range(0, len(names), 50):
        q = urllib.parse.urlencode({"action": "query", "format": "json", "formatversion": 2, "redirects": 1, "prop": "description|pageprops", "ppprop": "disambiguation", "titles": "|".join(names[i:i + 50])})
        out.append(json.loads(get("https://en.wikipedia.org/w/api.php?" + q))); time.sleep(1)
    keep("wikipedia_names.json", "https://en.wikipedia.org/w/api.php?action=query&prop=description|pageprops&titles=<50 names>&redirects=1", json.dumps(out).encode())


def main():
    (HERE / "data").mkdir(exist_ok=True); (HERE / "results").mkdir(exist_ok=True)
    pj = HERE / "results" / "pull.json"
    wiki_only = sys.argv[1:] == ["wiki"]                  # re-run just the Wikipedia step against the files already pulled
    info = json.loads(pj.read_text()) if wiki_only else {"pulled": date.today().isoformat(), "files": {}}

    def keep(name, url, raw):
        (HERE / "data" / name).write_bytes(raw)
        info["files"][name] = {"url": url, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

    if wiki_only:
        wiki_names(keep); pj.write_text(json.dumps(info, indent=2) + "\n"); return
    for name, url in FILES.items():
        keep(name, url, get(url))
    eps = json.loads(get(f"https://api.tvmaze.com/shows/{SHOW}/episodes?specials=1"))
    keep("tvmaze_episodes.json", f"https://api.tvmaze.com/shows/{SHOW}/episodes?specials=1", json.dumps(eps).encode())
    keep("tvmaze_cast.json", f"https://api.tvmaze.com/shows/{SHOW}/cast", get(f"https://api.tvmaze.com/shows/{SHOW}/cast"))
    guest = {}
    for e in eps:
        guest[str(e["id"])] = json.loads(get(f"https://api.tvmaze.com/episodes/{e['id']}/guestcast")); time.sleep(0.6)
    keep("tvmaze_guestcast.json", "https://api.tvmaze.com/episodes/{id}/guestcast (one call per episode id in tvmaze_episodes.json)", json.dumps(guest).encode())
    wiki_names(keep)
    pj.write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps({k: v["bytes"] for k, v in info["files"].items()}))


if __name__ == "__main__":
    main()
