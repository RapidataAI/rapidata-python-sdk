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
python reddit_edit_demand.py categorize --general-only      # exclude dedicated subs (de-bias)
python reddit_edit_demand.py categorize --subreddits picrequests,PhotoshopRequest

# 4. coverage / flair / paid-vs-free diagnostics
python reddit_edit_demand.py stats
```

### Offline smoke test (no network)

A tiny committed fixture lets you exercise the pipeline without scraping:

```bash
python reddit_edit_demand.py clean      --data-dir sample --output-dir output --format csv
python reddit_edit_demand.py categorize --output-dir output --examples 3
python reddit_edit_demand.py stats      --data-dir sample
# business taxonomy over the same fixture:
python reddit_edit_demand.py categorize --output-dir output --examples 3 --taxonomy business \
    --subreddits DesignRequests,DesignJobs,forhire,realestatephotography,AmazonSeller
```

## Business demand benchmark (`--taxonomy business`)

The consumer subs answer *what people want edited*. A parallel run answers *what
businesses want done* — logo placement, vectorizing logos, ecommerce product
photos, virtual staging, mockups, ad creative, packaging, text/copy placement.
Same pipeline, same cohorts, same report; only the subreddits and the rule set
([`business_category_rules.py`](business_category_rules.py)) change. Pass
`--taxonomy business` to `categorize`/`stats`.

```bash
# scrape stays taxonomy-agnostic -- just point it at the business subs
python reddit_edit_demand.py scrape --data-dir data-business \
    --subreddits DesignRequests,DesignJobs,forhire,realestatephotography,AmazonSeller
python reddit_edit_demand.py clean  --data-dir data-business --output-dir output-business --format csv
python reddit_edit_demand.py categorize --taxonomy business --output-dir output-business
# de-biased + edits-only (apples-to-apples with the consumer edit-only mix):
python reddit_edit_demand.py categorize --taxonomy business --output-dir output-business \
    --general-only --edits-only
```

- **Subreddits**: `DesignRequests` is the backbone request sub (the r/PhotoshopRequest
  analog); `DesignJobs` + `forhire` add volume but are **supply-heavy** — a post
  there only counts as demand if it reads as the buyer hiring (`SUPPLY_HEAVY_SUBS`
  + `HIRING_RE`), so freelancers advertising (`[For Hire] I can make your logo`)
  are dropped. `realestatephotography` (single-purpose → `SUBREDDIT_DEFAULT`,
  droppable via `--general-only`) and `AmazonSeller` are niche amplifiers for thin
  edit categories (virtual staging, ecommerce photos).
- **Edit vs create** (`is_edit`): business demand is dominated by create-from-scratch
  work (logo/flyer/packaging design). Every request is tagged edit-of-existing-asset
  vs create-from-scratch (`EDIT_CATEGORIES`); the report shows the full mix **and** an
  edits-only view, and `--edits-only` restricts the whole report to the consumer-comparable
  edit subset.
- **Expanded supply/showcase filtering**: `EXCLUDE_FLAIRS` and `SHOWCASE_RE` are
  widened with freelancer vocabulary (`for hire`, `commissions open`, `offering
  design`, `$X/hr`, ...) because business subs are full of people *offering*
  services, the inverse of demand.

> ⚠️ **Reddit is a weak proxy for business demand.** Real businesses commission on
> Fiverr / Upwork / 99designs, not Reddit; Reddit business requests skew toward
> hobbyists, micro-businesses, students, and free/portfolio asks. Read the category
> **mix** as directional — absolute volumes and the consumer↔business comparison are
> biased toward low-budget work. (Marketplace data would be a better v2 source but
> sits outside this Reddit/Arctic-Shift pipeline and carries ToS constraints.)

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

## De-biasing the weights (`--general-only`)

r/estoration is a *dedicated* restoration community, so pooling it with the
general subs amplifies the restoration category. `--general-only` (on
`categorize` and `stats`) drops single-purpose subs (the keys of
`SUBREDDIT_DEFAULT`) so you see what people bring to a *general* editing
community — where object removal leads. Report both: pooled shows total demand,
general-only shows the de-biased per-request mix. `--subreddits a,b` restricts
to an explicit list.

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
