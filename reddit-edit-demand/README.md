# reddit-edit-demand

Scrape real "please edit my photo" requests from Reddit to learn **what people
actually want edited** — a demand-weighted, time-aware taxonomy for designing an
image-editing benchmark.

## Why this exists

Benchmark category lists (Artificial Analysis, KontextBench) are *capability*
taxonomies: add / remove / modify object, edit text, change style. They describe
what a model *can* do, not what people *ask* for. A demo scrape showed the gap
immediately: "remove this object/person" alone is ~⅓–⅖ of all requests, while
**photo restoration**, **quality/upscale**, and **"put these two people in one
photo together"** (often a deceased loved one) are high-volume real categories
with no home in those lists. This tool collects the requests so the benchmark
can weight categories by demand instead of guessing.

## Data sources

- **Arctic-Shift archive API** (backbone) — public, no key, reaches back to 2016.
  Reddit's own API can't (it caps at ~1000 posts per listing).
- **Official Reddit API** (optional) — only tops up the freshest month. Off
  unless you pass `--use-reddit-api` *and* provide credentials. See `.env.example`.
  (This is the classic script-app flow at reddit.com/prefs/apps — **not** Devvit,
  which only builds apps that run inside Reddit and can't bulk-export data.)

## Usage

```bash
# 1. collect raw posts -> data/raw_posts.jsonl (resumable; safe to Ctrl-C and rerun)
python reddit_edit_demand.py scrape                      # all default subs, 2016-01..now, cap 300/month
python reddit_edit_demand.py scrape --cap 500 --start-month 2020-01

# 2. clean -> output/clean.csv (derives cohort, paid, ai_ok, n_images, is_removed)
python reddit_edit_demand.py clean --format csv          # or parquet/both (parquet needs pyarrow)

# 3. categorize -> output/category_report.md + category_counts.csv
python reddit_edit_demand.py categorize

# 4. coverage / flair / paid-vs-free diagnostics
python reddit_edit_demand.py stats
```

### Offline smoke test (no network)

A tiny committed fixture lets you exercise the pipeline without scraping:

```bash
python reddit_edit_demand.py clean      --data-dir sample --output-dir output --format csv
python reddit_edit_demand.py categorize --output-dir output --examples 3
python reddit_edit_demand.py stats      --data-dir sample
```

## How it works

- **Subreddits** (default): `PhotoshopRequest`, `estoration`, `picrequests`,
  `editmyphoto`, `PhotoShopRequests`. Override with `--subreddits a,b,c`.
- **Coverage**: continuous monthly from `--start-month` to now. Every post is
  tagged with its `year_month`; cohorts are derived at clean-time
  (`≤2021` → `pre_ai`, `≥2024` → `post_ai`, `2022–23` → `transition`), so you can
  re-bucket or plot a monthly trend without re-scraping.
- **Per-(subreddit, month) cap** (`--cap`, default 300) keeps the time series
  even so one busy sub/month can't dominate.
- **Resumable**: progress is checkpointed to `data/reddit_edit_state.json` after
  every page; completed `(sub, month)` cells are skipped on rerun and partial
  ones resume from their saved cursor. Dedup is by post id.
- **Capture**: text/metadata only — title, selftext, flair, dates, score,
  comments, permalink, and image **URLs** (never downloads images).
- **Categories** live in [`category_rules.py`](category_rules.py): a transparent,
  priority-ordered keyword rule set (first match wins). Edit it and re-run
  `categorize` — the report prints example titles per category so you can audit
  the bucketing.

## Caveat on counts

Because each `(sub, month)` is capped, category counts are demand **samples**
chosen for fair month-to-month comparison, **not absolute volumes**. Busy recent
months are truncated; quiet old months fall short of the cap. For
absolute-volume questions, raise `--cap` or read the pre-cap per-month coverage
from `stats`.

## Note

Personal research tool. The script, rules, README, and the tiny `sample/`
fixture are committed; scraped `data/` and `output/` are gitignored and not
shared. Not part of the published SDK — tool-only deps live in
`requirements.txt`, not the SDK's `pyproject.toml`.
