# Did guest stars lift The Office's ratings?

Two entertainment data sets, one analysis: how Netflix's catalogue is made up (movie running time by decade, how old titles are when they are added, countries and genres), and whether the episodes of The Office (US) with guest stars were rated higher than the others of the same season. Five questions:
- how did the mix of the Netflix catalogue change over 2016 to 2020 (movies against TV shows, countries, genres);
- how long are its movies, by release decade, and what is the typical length of a 1990s movie;
- how old is a title when Netflix adds it, and has that changed for movies and TV shows;
- did The Office's guest-star episodes rate higher than the other episodes of the same season, tested by shuffling the guest flags within seasons;
- how uncertain is that answer, does it survive other definitions of a guest star, and what about the finale and the last seasons' decline.

The questions follow DataCamp's guided project "Investigating Netflix Movies and Guest Stars in The Office" (Python, advanced), answered with a permutation test and a hand-written recount. The page with the results and the charts is the build log:

Build log: https://mrrishit909.github.io/projects/netflix-office/

## Data

- **Netflix titles:** `netflix_titles.csv`, 7,787 titles listed on Netflix as of January 2021 (collected from the third-party Flixable search engine), the TidyTuesday 2021-04-20 copy (https://github.com/rfordatascience/tidytuesday) of the Kaggle dataset "Netflix Movies and TV Shows" by Shivam Bansal (https://www.kaggle.com/datasets/shivamb/netflix-shows). Kaggle's public metadata states the licence: CC0 Public Domain.
- **The Office ratings:** IMDb's official non-commercial datasets (https://datasets.imdbws.com/: `title.episode`, `title.basics`, `title.ratings`; refreshed daily). Licence: personal and non-commercial use (https://developer.imdb.com/non-commercial-datasets/), so this repository publishes aggregates only, never episode-by-episode IMDb rows. Information courtesy of IMDb (https://www.imdb.com). The TidyTuesday 2020-03-17 `office_ratings.csv` (a March 2020 IMDb snapshot whose origin states no licence we could verify) is used only to measure how far ratings have moved since, and only that aggregate is published.
- **Guest stars:** the TVmaze API (https://www.tvmaze.com/api), show 526: the main cast and each episode's guest cast. TVmaze's licence is CC BY-SA, with attribution; the guest-derived counts and tests here are shared under the same terms. Whether a guest is notable comes from the MediaWiki API (does the name have an English Wikipedia article about a performer; only existence and the Wikidata one-line description are used). Wikipedia's season pages and Wikidata have no systematic per-episode guest list, IMDb's `title.principals` carries only the top-billed cast of each episode (the regulars), and the Office fan wiki sits behind a bot challenge, so TVmaze is the one open source with a guest list per episode.
- The files are about 296 MB, fetched by `download.py` (checksums in `results/pull.json`), not committed. IMDb replaces its files every day, so a new download moves the Office numbers slightly.

```
./venv/bin/pip install pandas numpy matplotlib certifi      # in a venv
./venv/bin/python download.py    # data/*   (a few minutes, mostly the IMDb files)
./venv/bin/python analyze.py     # results/*   (about 40 seconds)
./venv/bin/python check.py       # about 25 seconds
./venv/bin/python charts.py
```

## Steps

1. **Download** the Netflix and IMDb files, the TVmaze episodes, main cast and guest casts, and the Wikipedia lookups of every guest name, with checksums.
2. **Audit.** Netflix: duplicates, missing values, the window of `date_added`, titles added before they were released. The Office: IMDb lists 191 entries; 3 recent "Part 2" entries with under 2,000 votes each split one broadcast and are dropped, leaving the 188 that the 2020 snapshot also has; TVmaze splits hour-long episodes in two and the halves are merged back (three titles need an alias).
3. **Netflix tables.** Titles by year added (2016 to 2020 only: earlier years hold 145 surviving titles in all), movie running time by release decade, the 1990s question, years between release and addition, countries and genres (a title counts once for every country or genre it lists).
4. **The guest-star rule, fixed before any rating was looked at.** A person credited in an episode's TVmaze guest cast, not in the main cast, credited in at most 3 of the 188 episodes, who either has an English Wikipedia article (not a disambiguation page) whose one-line description names a performer, or plays themselves. An episode with at least one such person is a guest-star episode: 109 of 188. Alternatives fixed in advance: guests in one episode only (71 episodes), up to five (122), and no notability test at all (159, which flags most episodes).
5. **The test.** T = the mean of (rating minus season mean) over guest-star episodes minus the same over the others. The guest flags are shuffled within each season 10,000 times (`random.Random`, a fixed seed per specification), p = (k+1)/10,001; the same without the season adjustment; a 95% interval from 5,000 bootstrap resamples within seasons. Seven specifications: the rule, its three alternatives, without season premieres, finales and episodes of 40 minutes or more, and seasons 1 to 7 and 8 to 9 alone.
6. **Check.** `check.py` recomputes everything in plain Python (csv, gzip, json, math, random and fractions: no pandas, numpy or scipy): 545 numbers, the permutation counts exact (every permuted statistic is an exact fraction, so ties cannot flip), the rest to a relative tolerance of 1e-8.
7. **Charts.**

## Results

- **The Office: no lift from guest stars.** Within a season, the 109 guest-star episodes were rated +0.005 stars against the 79 others (95% bootstrap interval -0.13 to +0.14; shuffling within seasons gives p = 0.96, and 95% of shuffles fall between -0.16 and +0.15). Without the season adjustment it is -0.035 (p = 0.72), so the seasons' different guest shares (from 46% to 78%) do not hide a lift.
- **It holds under other definitions, with limited power.** The adjusted difference runs from -0.09 to +0.05 across the seven specifications, and the smallest p-value is 0.22 (without premieres, finales and long episodes: -0.09, interval -0.23 to +0.04). The shuffles imply a standard error of about 0.08 stars, so a true effect would need to be about 0.22 stars to be detected 80% of the time: smaller effects cannot be ruled out with 188 episodes.
- **The last seasons fell.** Seasons 8 and 9 average 7.53 stars against 8.35 for seasons 2 to 5; 44 of the 47 episodes of seasons 8 and 9 are below the seasons 2 to 5 mean. Season 3 is the best (8.43) and season 8 the worst (7.39). Guest-star episodes were 78% of season 9, the most of any season, and season 9 is among the lowest rated.
- **The finale.** The series finale ranks 1 by rating (tied with 1 other episode), 2.1 stars above its season's mean, and drew 4 times the median episode's votes: a fans' event, not an ordinary episode, which is why one specification drops premieres and finales.
- **Ratings are a moving target.** Against the March 2020 snapshot, the 188 episodes' ratings have moved by 0.21 stars on average (only 7% unchanged, the largest move 0.5) and their vote counts are a median 3.6 times larger.
- **Netflix movies got shorter.** Median running time by release decade: 142 minutes for the 1960s (22 movies), 104 for the 1980s, 108 for the 1990s and the 2000s, 96 for the 2010s (3,951 movies) and 94 for the 2020s.
- **The 1990s question.** The most common single length of the 194 1990s movies is 94 minutes, but only 8 of them have it; the median is 108 and the mean 114. Of 50 action and adventure movies of the decade, 8 run under 90 minutes.
- **Movies are added older, TV shows newer.** The share of movies released in the year they were added or the year before fell from 75% (added 2016) to 45% (2020); for TV shows it rose from 50% to 77%. The movie share of what was added was 58% in 2016 and 65% in 2020.
- **Countries and genres.** The US share of titles that list a country was 48% for 2016, 39% for 2018 and 47% for 2020; India's rose from 3% to 23% in 2018 and fell back to 11%. Comparing titles added in 2016-17 with 2019-20, documentaries fell from 16.5% to 7.4% of titles, comedies rose from 14.4% to 21.0% and dramas from 21.8% to 27.5%.

## Not done, and caveats

- **IMDb ratings are user votes**, not critics' scores, they keep moving, and a fan-favourite episode attracts more votes. Nothing here says why an episode is rated as it is.
- **The guest-star flag is a proxy.** TVmaze's guest list is community-kept (5 episodes have none); "notable" means a Wikipedia article about a performer, matched by name, so a namesake actor can slip in and a real celebrity without an article is missed. Nothing was corrected by hand. Casting is not random: guests cluster in special episodes, which the season adjustment and the no-premieres-or-finales specification only partly address. The result is an association in 188 episodes, not a causal effect, and effects below about 0.2 stars cannot be excluded.
- **No dose-response** (how many guests, how famous), no episode-position model, no vote-weighting, and no use of the episode scripts or reviews.
- **The Netflix file is a January 2021 snapshot of titles still on the service**, from a third-party listing (Flixable), not from Netflix: titles removed earlier are missing, so trends by year added are survivor trends. Years before 2016 hold 145 titles in all (at most 88 in a year) and 2021 is January only, so only 2016 to 2020 is compared.
- 12 titles were added before their release year (excluded from the gap statistics), 10 have no date added, 507 no country; 88 dates carry a leading space (trimmed). Countries and genres are lists: a title counts once for each, so shares add to more than 100%, and "International" is a catch-all genre. "Action" means the genre "Action & Adventure".
- The sample is 188 IMDb entries, most hour-long episodes counting once; TVmaze lists 202 regular episodes because it splits them in two, so counts of "episodes" differ between sources.
- Nothing from the data is committed, only summaries; the IMDb, TVmaze and Netflix terms are as above.
