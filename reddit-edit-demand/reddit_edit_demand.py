#!/usr/bin/env python3
"""Scrape Reddit "please edit my photo" requests to learn what people actually
want edited -- a demand-weighted, time-aware taxonomy for an image-editing
benchmark.

Capability taxonomies (Artificial Analysis / KontextBench: add / remove /
modify / text / style) describe what a model *can* do. They do not match what
people *ask* for: a quick look at r/PhotoshopRequest shows "remove this person"
is a third-to-half of all requests, while photo restoration and "put these two
people in one picture" -- huge real categories -- have no home in those lists.
This tool collects real requests so the benchmark can weight categories by
demand instead of guessing.

Backbone source is the public Arctic-Shift archive API (no key, full history).
The official Reddit API is an OPTIONAL enrichment for the freshest month only;
it is off unless you pass --use-reddit-api and have credentials in .env.

Pipeline (each subcommand is idempotent / resumable):

    # 1. collect raw posts -> data/raw_posts.jsonl  (+ resumable state file)
    python reddit_edit_demand.py scrape

    # 2. clean -> output/clean.{csv,parquet}  (derives cohort/paid/ai_ok/...)
    python reddit_edit_demand.py clean --format csv

    # 3. categorize -> output/category_report.md + category_counts.csv
    python reddit_edit_demand.py categorize

    # 4. coverage / flair / paid-vs-free diagnostics
    python reddit_edit_demand.py stats

A tiny offline smoke test (no network) runs steps 2-4 against sample/:
    python reddit_edit_demand.py clean --data-dir sample --output-dir output --format csv

NOTE on counts: scrape caps each (subreddit, month) at --cap so the time series
stays even. The category counts are therefore demand *samples* for fair
month-to-month comparison, NOT absolute volumes. Raise --cap for absolute work.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from types import ModuleType
from typing import Iterable, cast

import requests

from category_rules import compile_rules


def load_taxonomy(name: str) -> ModuleType:
    """Return the rule module for the selected taxonomy.

    Both modules export the same names (RULES, FLAIR_RULES, SUBREDDIT_DEFAULT,
    EXCLUDE_FLAIRS, SHOWCASE_RE). The business module additionally exports
    EDIT_CATEGORIES / DEMAND_RE / UNGATED_SUBS; callers probe those with getattr
    so the consumer taxonomy is unaffected.
    """
    if name == "business":
        import business_category_rules as mod

        return mod
    import category_rules as mod

    return mod


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
DEFAULT_SUBREDDITS = [
    "PhotoshopRequest",
    "estoration",
    "picrequests",
    "editmyphoto",
    "PhotoShopRequests",
]

# Business/commercial demand subs (pass via --subreddits; scrape stays taxonomy-
# agnostic). A wide net for coverage: DesignRequests is the pure request board
# (ungated); everything else is demand-gated at categorize time (DEMAND_RE) so
# the supply/showcase/discussion that dominates these subs is dropped and only
# genuine asks count. Slice with --subreddits / --general-only for cleaner mixes.
BUSINESS_SUBREDDITS = [
    # request / gig boards
    "DesignRequests",
    "DesignJobs",
    "forhire",
    "slavelabour",
    "HungryArtists",
    # design communities (showcase/discussion-heavy -> demand-gated)
    "logodesign",
    "graphic_design",
    "photoshop",
    "Design",
    "logo",
    # business-owner / commercial
    "smallbusiness",
    "Entrepreneur",
    "ecommerce",
    "shopify",
    "AmazonSeller",
    "Etsy",
    "marketing",
    "advertising",
    # niche image-specific + creator economy
    "realestatephotography",
    "Twitch",
    "NewTubers",
    "podcasting",
]

ARCTIC_BASE = "https://arctic-shift.photon-reddit.com/api/posts/search"
USER_AGENT = "rapidata-edit-demand-study/1.0 (benchmark taxonomy research)"
REQUEST_SLEEP = 0.5  # polite gap between Arctic-Shift calls (seconds)
MAX_LIMIT = 100  # Arctic-Shift page size ceiling
MAX_RETRIES = 5
BACKOFF_BASE = 1.5  # exponential backoff base (seconds)
DEFAULT_MONTHLY_CAP = 300  # posts per (subreddit, month)
START_MONTH = "2016-01"

DATA_DIR = "data"
OUTPUT_DIR = "output"
STATE_NAME = "reddit_edit_state.json"
RAW_NAME = "raw_posts.jsonl"

# Cohort boundaries (applied at clean-time from year_month, never at scrape).
PRE_AI_MAX_YEAR = 2021  # <= this year  -> pre_ai
POST_AI_MIN_YEAR = 2024  # >= this year  -> post_ai  (between -> "transition")

# Fields we keep from the ~90-field Arctic-Shift post object.
DELETED_MARKERS = {
    "[removed]",
    "[deleted]",
    "[ Removed by moderator ]",
    "[deleted by user]",
}
_EMOJI_TOKEN = re.compile(r":[a-z0-9_]+:|[\U0001F000-\U0001FAFF☀-➿]", re.I)


# --------------------------------------------------------------------------- #
# Month / time helpers
# --------------------------------------------------------------------------- #
def current_month() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


def month_range(start: str, end: str) -> list[str]:
    """Inclusive list of "YYYY-MM" from start to end."""
    sy, sm = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    out: list[str] = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def month_bounds(year_month: str) -> tuple[int, int]:
    """Half-open [start_epoch, next_month_start_epoch) for a "YYYY-MM"."""
    y, m = (int(x) for x in year_month.split("-"))
    start = int(datetime(y, m, 1, tzinfo=timezone.utc).timestamp())
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    end = int(datetime(ny, nm, 1, tzinfo=timezone.utc).timestamp())
    return start, end


def epoch_to_iso(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def epoch_to_month(epoch: float) -> str:
    d = datetime.fromtimestamp(float(epoch), tz=timezone.utc)
    return f"{d.year:04d}-{d.month:02d}"


# --------------------------------------------------------------------------- #
# Fetcher (Arctic-Shift archive client)
# --------------------------------------------------------------------------- #
def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def _request_with_retry(
    session: requests.Session, params: dict[str, str | int]
) -> list[dict]:
    """One Arctic-Shift page with exponential backoff on transient failures.

    Sleeps REQUEST_SLEEP after every call regardless of outcome to stay polite.
    """
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(ARCTIC_BASE, params=params, timeout=60)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise requests.HTTPError(f"transient {resp.status_code}")
            resp.raise_for_status()
            data = resp.json().get("data", [])
            time.sleep(REQUEST_SLEEP)
            return data
        except (requests.RequestException, ValueError) as err:
            last_err = err
            wait = BACKOFF_BASE**attempt + random.uniform(0, 0.5)
            print(
                f"    retry {attempt + 1}/{MAX_RETRIES} after error: {err} (waiting {wait:.1f}s)"
            )
            time.sleep(wait)
    raise RuntimeError(
        f"Arctic-Shift request failed after {MAX_RETRIES} retries: {last_err}"
    )


# --------------------------------------------------------------------------- #
# State / checkpoint manager
# --------------------------------------------------------------------------- #
def state_path(data_dir: str) -> str:
    return os.path.join(data_dir, STATE_NAME)


def raw_path(data_dir: str) -> str:
    return os.path.join(data_dir, RAW_NAME)


def load_state(path: str) -> dict:
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"progress": {}, "total_written": 0, "last_run_utc": None}


def save_state(path: str, state: dict) -> None:
    state["last_run_utc"] = int(datetime.now(timezone.utc).timestamp())
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, path)  # atomic: a crash mid-write never corrupts the state


def cell(state: dict, sub: str, ym: str) -> dict:
    return state.setdefault("progress", {}).setdefault(sub, {}).get(ym, {})


def set_cell(state: dict, sub: str, ym: str, value: dict) -> None:
    state.setdefault("progress", {}).setdefault(sub, {})[ym] = value


# --------------------------------------------------------------------------- #
# Raw writer + dedup
# --------------------------------------------------------------------------- #
def existing_ids(path: str) -> set[str]:
    """Rebuild the seen-id set from the JSONL so reruns never duplicate lines."""
    ids: set[str] = set()
    if not os.path.exists(path):
        return ids
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(json.loads(line)["id"])
            except (ValueError, KeyError):
                continue
    return ids


class RawWriter:
    """Append-only JSONL writer; one post per line."""

    def __init__(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._f = open(path, "a")

    def write(self, record: dict) -> None:
        self._f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def flush(self) -> None:
        self._f.flush()

    def close(self) -> None:
        self._f.close()


def extract_image_urls(post: dict) -> list[str]:
    """Collect image URLs without downloading. Handles galleries + direct hosts."""
    urls: list[str] = []
    meta = post.get("media_metadata")
    if post.get("is_gallery") and isinstance(meta, dict):
        for item in meta.values():
            if isinstance(item, dict):
                src = item.get("s", {})
                u = src.get("u") or src.get("gif")
                if u:
                    urls.append(str(u).replace("&amp;", "&"))
    url = post.get("url") or ""
    if not urls and url:
        urls.append(str(url))
    return urls


def to_raw_record(
    post: dict, sub: str, year_month: str, source: str = "arctic"
) -> dict:
    """Project the wide Arctic-Shift post down to the fields we keep."""
    return {
        "id": post.get("id"),
        "subreddit": sub,
        "title": post.get("title") or "",
        "selftext": post.get("selftext") or "",
        "link_flair_text": post.get("link_flair_text"),
        "created_utc": post.get("created_utc"),
        "year_month": year_month,
        "author": post.get("author"),
        "score": post.get("score"),
        "num_comments": post.get("num_comments"),
        "permalink": post.get("permalink"),
        "url": post.get("url"),
        "image_urls": extract_image_urls(post),
        "removed_by_category": post.get("removed_by_category"),
        "is_self": post.get("is_self"),
        "is_gallery": post.get("is_gallery"),
        "_source": source,
    }


# --------------------------------------------------------------------------- #
# Flair parsing (paid / free + AI-ok signals)
# --------------------------------------------------------------------------- #
def normalize_flair(flair: str | None) -> str:
    """Lowercase, strip emoji/CSS tokens. Returns "" for null (pre-2018 era)."""
    if not flair:
        return ""
    return _EMOJI_TOKEN.sub(" ", flair).lower().strip()


def parse_flair_signals(flair: str | None, title: str, selftext: str) -> dict:
    """Derive {paid, ai_ok}; unknown -> None (never guessed).

    Prefer the flair, fall back to title/selftext when flair is null so the
    signal survives the years where the subs had no flair vocabulary.
    """
    hay = " ".join([normalize_flair(flair), title.lower(), selftext.lower()])

    paid: bool | None = None
    if re.search(r"\bpaid\b|\btip\b|will tip|\$\d|bounty|reward", hay):
        paid = True
    elif re.search(r"\bfree\b|unpaid|no pay", hay):
        paid = False

    ai_ok: bool | None = None
    if re.search(r"no[ -]?ai|human only|no generative|not ai", hay):
        ai_ok = False
    elif re.search(r"ai ?ok|ai welcome|ai fine|ai allowed", hay):
        ai_ok = True

    return {"paid": paid, "ai_ok": ai_ok}


# --------------------------------------------------------------------------- #
# Cohort + cleaning
# --------------------------------------------------------------------------- #
def cohort_of(year_month: str) -> str:
    year = int(year_month.split("-")[0])
    if year <= PRE_AI_MAX_YEAR:
        return "pre_ai"
    if year >= POST_AI_MIN_YEAR:
        return "post_ai"
    return "transition"


def is_removed(record: dict) -> bool:
    if record.get("removed_by_category"):
        return True
    return (record.get("selftext") or "").strip() in DELETED_MARKERS or (
        record.get("title") or ""
    ).strip() in DELETED_MARKERS


def iter_records(jsonl: str) -> Iterable[dict]:
    with open(jsonl) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def build_clean_rows(jsonl: str) -> list[dict]:
    """Read raw JSONL, dedup on id, derive analysis columns."""
    seen: set[str] = set()
    rows: list[dict] = []
    for rec in iter_records(jsonl):
        pid = str(rec.get("id"))
        if pid in seen:
            continue
        seen.add(pid)
        signals = parse_flair_signals(
            rec.get("link_flair_text"), rec.get("title", ""), rec.get("selftext", "")
        )
        rows.append(
            {
                "id": pid,
                "subreddit": rec.get("subreddit"),
                "year_month": rec.get("year_month"),
                "cohort": cohort_of(rec.get("year_month", "1970-01")),
                "title": rec.get("title", ""),
                "selftext": rec.get("selftext", ""),
                "flair": normalize_flair(rec.get("link_flair_text")),
                "paid": signals["paid"],
                "ai_ok": signals["ai_ok"],
                "score": rec.get("score"),
                "num_comments": rec.get("num_comments"),
                "n_images": len(rec.get("image_urls") or []),
                "is_removed": is_removed(rec),
                "permalink": rec.get("permalink"),
                "source": rec.get("_source"),
            }
        )
    return rows


# --------------------------------------------------------------------------- #
# Keyword categorizer
# --------------------------------------------------------------------------- #
def categorize_text(text: str, compiled: list[tuple[str, re.Pattern[str]]]) -> str:
    for category, pattern in compiled:
        if pattern.search(text):
            return category
    return "UNMATCHED"


def categorize_post(
    title: str,
    selftext: str,
    flair: str,
    subreddit: str,
    keyword_rules: list[tuple[str, re.Pattern[str]]],
    flair_rules: list[tuple[str, re.Pattern[str]]],
    subreddit_default: dict[str, str],
) -> str:
    """Category from three signals, precision-first: keyword, then flair, then
    single-purpose-subreddit default."""
    cat = categorize_text((title + " " + selftext).lower(), keyword_rules)
    if cat != "UNMATCHED":
        return cat
    cat = categorize_text(flair, flair_rules)
    if cat != "UNMATCHED":
        return cat
    return subreddit_default.get(subreddit, "UNMATCHED")


def is_demand_request(
    row: dict,
    exclude_flairs: set[str],
    showcase_re: re.Pattern[str],
    demand_re: re.Pattern[str] | None = None,
    ungated_subs: set[str] | frozenset[str] = frozenset(),
) -> bool:
    """False for posts that aren't a demand request: removed/deleted (no text),
    finished-work showcases, and meta/result flairs.

    Business taxonomy adds a demand gate: outside the pure request subs
    (``ungated_subs``) a post must carry an explicit ask (``demand_re`` over
    title+selftext+flair), so the supply/showcase/discussion that dominates wide
    business subs doesn't get counted as demand.
    """
    if row.get("is_removed"):
        return False
    if (row.get("flair") or "") in exclude_flairs:
        return False
    if showcase_re.search(row.get("title") or ""):
        return False
    if demand_re is not None and row.get("subreddit") not in ungated_subs:
        hay = " ".join(
            [row.get("title") or "", row.get("selftext") or "", row.get("flair") or ""]
        )
        if not demand_re.search(hay):
            return False
    return True


def subreddit_include(args: argparse.Namespace) -> set[str] | None:
    """Explicit --subreddits include-set, or None when not given."""
    raw = getattr(args, "subreddits", "") or ""
    names = {s.strip() for s in raw.split(",") if s.strip()}
    return names or None


def keep_subreddit(
    name: str,
    include: set[str] | None,
    general_only: bool,
    subreddit_default: dict[str, str],
) -> bool:
    """Filter by --subreddits and --general-only. General = not single-purpose
    (single-purpose subs are the keys of SUBREDDIT_DEFAULT, e.g. r/estoration),
    so excluding them removes the dedicated-community amplification."""
    if include is not None and name not in include:
        return False
    if general_only and name in subreddit_default:
        return False
    return True


# --------------------------------------------------------------------------- #
# Optional official Reddit API enrichment (skippable)
# --------------------------------------------------------------------------- #
def reddit_oauth_session_or_none() -> requests.Session | None:
    """Return an OAuth'd session if creds are present, else None (archive-only)."""
    try:
        from dotenv import load_dotenv  # already a dev dependency

        load_dotenv()
    except ImportError:
        pass
    from requests.auth import HTTPBasicAuth

    cid = os.environ.get("REDDIT_CLIENT_ID")
    secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not cid or not secret:
        return None
    ua = os.environ.get("REDDIT_USER_AGENT", USER_AGENT)
    auth = HTTPBasicAuth(cid, secret)
    resp = requests.post(
        "https://www.reddit.com/api/v1/access_token",
        auth=auth,
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": ua},
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    s = requests.Session()
    s.headers.update({"Authorization": f"bearer {token}", "User-Agent": ua})
    return s


def refresh_recent(session: requests.Session, sub: str) -> list[dict]:
    """Pull the freshest posts the archive lags on (listings cap ~1000)."""
    out: list[dict] = []
    after: str | None = None
    for _ in range(10):  # up to ~1000 posts
        params: dict[str, str | int] = {"limit": 100}
        if after:
            params["after"] = after
        resp = session.get(
            f"https://oauth.reddit.com/r/{sub}/new", params=params, timeout=30
        )
        resp.raise_for_status()
        listing = resp.json().get("data", {})
        children = listing.get("children", [])
        if not children:
            break
        out.extend(c["data"] for c in children)
        after = listing.get("after")
        if not after:
            break
        time.sleep(REQUEST_SLEEP)
    return out


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def scrape(args: argparse.Namespace) -> None:
    subs = [s.strip() for s in args.subreddits.split(",") if s.strip()]
    end = args.end_month or current_month()
    months = month_range(args.start_month, end)
    os.makedirs(args.data_dir, exist_ok=True)

    spath = state_path(args.data_dir)
    rpath = raw_path(args.data_dir)
    state = load_state(spath)
    state["start_month"], state["cap_per_month"], state["subreddits"] = (
        args.start_month,
        args.cap,
        subs,
    )

    seen = existing_ids(rpath)
    writer = RawWriter(rpath)
    session = _session()
    print(
        f"scrape: {len(subs)} subs x {len(months)} months ({months[0]}..{months[-1]}), cap {args.cap}/month"
    )

    try:
        for sub in subs:
            for ym in months:
                c = cell(state, sub, ym)
                if c.get("done"):
                    continue
                start_epoch, end_epoch = month_bounds(ym)
                count = int(c.get("count", 0))
                before = int(c.get("cursor", end_epoch))
                while count < args.cap:
                    page = _request_with_retry(
                        session,
                        {
                            "subreddit": sub,
                            "limit": min(MAX_LIMIT, args.cap - count),
                            "sort": "desc",
                            "after": epoch_to_iso(start_epoch),
                            "before": epoch_to_iso(before),
                        },
                    )
                    if not page:
                        break
                    new = 0
                    for post in page:
                        pid = post.get("id")
                        if not isinstance(pid, str) or pid in seen:
                            continue
                        seen.add(pid)
                        writer.write(to_raw_record(post, sub, ym))
                        count += 1
                        new += 1
                        state["total_written"] = int(state.get("total_written", 0)) + 1
                        if count >= args.cap:
                            break
                    oldest = min(int(p["created_utc"]) for p in page)
                    if oldest >= before and new == 0:
                        break  # no forward progress and nothing new -> month exhausted
                    before = oldest
                    set_cell(
                        state,
                        sub,
                        ym,
                        {"done": False, "cursor": before, "count": count},
                    )
                    writer.flush()
                    save_state(spath, state)  # checkpoint after every page
                    if len(page) < min(MAX_LIMIT, args.cap):
                        break  # month exhausted before hitting cap
                set_cell(state, sub, ym, {"done": True, "count": count})
                save_state(spath, state)
                print(f"  r/{sub} {ym}: {count} posts")

        if args.use_reddit_api:
            reddit = reddit_oauth_session_or_none()
            if reddit is None:
                print(
                    "  --use-reddit-api set but no REDDIT_CLIENT_ID/SECRET in env; skipping enrichment."
                )
            else:
                for sub in subs:
                    added = 0
                    for post in refresh_recent(reddit, sub):
                        pid = post.get("id")
                        if not isinstance(pid, str) or pid in seen:
                            continue
                        seen.add(pid)
                        writer.write(
                            to_raw_record(
                                post,
                                sub,
                                epoch_to_month(post.get("created_utc", 0)),
                                source="reddit_api",
                            )
                        )
                        state["total_written"] = int(state.get("total_written", 0)) + 1
                        added += 1
                    print(f"  reddit-api r/{sub}: +{added} fresh posts")
                writer.flush()
                save_state(spath, state)
    finally:
        writer.close()
    print(f"done. total_written={state.get('total_written')}  raw={rpath}")


def clean(args: argparse.Namespace) -> None:
    import pandas as pd

    rows = build_clean_rows(raw_path(args.data_dir))
    df = pd.DataFrame(rows)
    os.makedirs(args.output_dir, exist_ok=True)
    print(f"clean: {len(df)} unique posts; cohorts={dict(Counter(df['cohort']))}")

    if args.format in ("csv", "both"):
        p = os.path.join(args.output_dir, "clean.csv")
        df.to_csv(p, index=False)
        print(f"  wrote {p}")
    if args.format in ("parquet", "both"):
        p = os.path.join(args.output_dir, "clean.parquet")
        try:
            df.to_parquet(p, index=False)
            print(f"  wrote {p}")
        except ImportError:
            print(
                "  parquet needs pyarrow -> `pip install -r requirements.txt`, or use --format csv"
            )


def categorize(args: argparse.Namespace) -> None:
    import pandas as pd

    clean_csv = os.path.join(args.output_dir, "clean.csv")
    if os.path.exists(clean_csv):
        df = pd.read_csv(clean_csv).fillna({"title": "", "selftext": ""})
    else:
        df = pd.DataFrame(build_clean_rows(raw_path(args.data_dir)))
    if df.empty:
        print("no data to categorize; run scrape/clean first.")
        return

    for col in ("title", "selftext", "flair", "subreddit", "cohort"):
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)
    # is_removed survives a CSV round-trip as the string "True"/"False"; coerce.
    df["is_removed"] = df.get("is_removed", False)
    df["is_removed"] = df["is_removed"].map(lambda v: str(v).lower() in ("true", "1"))

    tax = load_taxonomy(args.taxonomy)
    subreddit_default: dict[str, str] = tax.SUBREDDIT_DEFAULT
    edit_categories: set[str] | None = getattr(tax, "EDIT_CATEGORIES", None)
    demand_re = getattr(tax, "DEMAND_RE", None)
    ungated_subs = getattr(tax, "UNGATED_SUBS", frozenset())
    selftext_chars = getattr(tax, "SELFTEXT_CHARS", None)
    gated_require_category = getattr(tax, "GATED_REQUIRE_CATEGORY", False)

    include = subreddit_include(args)
    if include is not None or args.general_only:
        df = df[
            df["subreddit"].map(
                lambda s: keep_subreddit(
                    s, include, args.general_only, subreddit_default
                )
            )
        ]
        scope = (
            "general subs only"
            if args.general_only
            else ",".join(sorted(include or []))
        )
        print(f"filter: {scope}  ({len(df)} posts after filtering)")
        if df.empty:
            print("no posts match the subreddit filter.")
            return

    kw = compile_rules(tax.RULES)
    fl = compile_rules(tax.FLAIR_RULES)
    # Classify on title + (optionally capped) selftext lead. The gate below still
    # sees full selftext; only the category match uses the cap, so long gig-board
    # job specs don't mis-fire a category via a stray keyword in their tail.
    clf_selftext = (
        df["selftext"].str.slice(0, selftext_chars)
        if selftext_chars
        else df["selftext"]
    )
    df["category"] = df.apply(
        lambda r: categorize_post(
            r["title"],
            clf_selftext.loc[r.name],
            r["flair"],
            r["subreddit"],
            kw,
            fl,
            subreddit_default,
        ),
        axis=1,
    )
    df["is_request"] = df.apply(
        lambda r: is_demand_request(
            {
                "is_removed": r["is_removed"],
                "flair": r["flair"],
                "title": r["title"],
                "selftext": r["selftext"],
                "subreddit": r["subreddit"],
            },
            tax.EXCLUDE_FLAIRS,
            tax.SHOWCASE_RE,
            demand_re,
            ungated_subs,
        ),
        axis=1,
    )
    # In gated subs, an ask that resolves to no image-edit category (UNMATCHED)
    # is a generic role/project hire, not the discrete edit demand we measure.
    if gated_require_category:
        df["is_request"] = df["is_request"] & ~(
            (~df["subreddit"].isin(list(ungated_subs)))
            & (df["category"] == "UNMATCHED")
        )

    # Tag edit-of-existing-asset vs create-from-scratch (business taxonomy only).
    if edit_categories is not None:
        df["is_edit"] = df["category"].isin(list(edit_categories))

    # Shares are over demand *requests* only -- excluding posts that can't be a
    # request (removed/no-text) or aren't one (finished-work showcases / supply).
    req = cast("pd.DataFrame", df[df["is_request"]])
    total, n_removed = len(df), int(df["is_removed"].sum())
    n_showcase = total - len(req) - n_removed
    # --edits-only restricts the whole report to the consumer-comparable subset.
    if args.edits_only and edit_categories is not None:
        req = cast("pd.DataFrame", req[req["is_edit"]])
    n_req = len(req)

    os.makedirs(args.output_dir, exist_ok=True)
    counts = req.groupby(["category", "cohort", "subreddit"]).size().reset_index()
    counts.columns = ["category", "cohort", "subreddit", "n"]
    counts_csv = os.path.join(args.output_dir, "category_counts.csv")
    counts.to_csv(counts_csv, index=False)

    def cohort_tables(frame: "pd.DataFrame") -> list[str]:
        out: list[str] = []
        for cohort in ["pre_ai", "transition", "post_ai"]:
            sub = cast("pd.DataFrame", frame[frame["cohort"] == cohort])
            if sub.empty:
                continue
            out.append(f"\n## {cohort} (n={len(sub)})\n")
            out.append("| category | n | share |")
            out.append("|---|---:|---:|")
            for cat, n in Counter(sub["category"]).most_common():
                out.append(f"| {cat} | {n} | {100 * n / len(sub):.1f}% |")
        return out

    title = (
        "Business image-edit demand"
        if args.taxonomy == "business"
        else "Image-edit demand"
    )
    lines: list[str] = [f"# {title} by category\n"]
    lines.append(
        f"_{n_req} demand requests across {req['subreddit'].nunique()} subreddits "
        f"(excluded {n_removed} removed/deleted, {n_showcase} showcase/supply)._\n"
    )
    if edit_categories is not None and not args.edits_only:
        n_edit = int(req["is_edit"].sum())
        lines.append(
            f"_Of these, {n_edit} edit an existing asset and {n_req - n_edit} are "
            f"create-from-scratch. Reddit is a weak proxy for business demand "
            f"(real commissions run on Fiverr/Upwork/99designs and skew this toward "
            f"low-budget/free work), so read the category **mix**, not absolute volume._\n"
        )
    lines.extend(cohort_tables(req))

    # Business: an edits-only view (manipulating an existing asset) that lines up
    # apples-to-apples with the consumer (edit-only) benchmark.
    if edit_categories is not None and not args.edits_only:
        edits = cast("pd.DataFrame", req[req["is_edit"]])
        if not edits.empty:
            lines.append("\n# Edits-only view (existing-asset manipulation)\n")
            lines.extend(cohort_tables(edits))

    lines.append("\n## Example titles per category\n")
    for cat, _ in Counter(req["category"]).most_common():
        if cat == "UNMATCHED":
            continue
        examples = req.loc[req["category"] == cat, "title"].head(args.examples).tolist()
        lines.append(f"\n**{cat}**")
        for ex in examples:
            lines.append(f"- {str(ex)[:110]}")
    report = os.path.join(args.output_dir, "category_report.md")
    with open(report, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(
        f"categorize: {total} posts; {n_req} demand requests -> {report}, {counts_csv}"
    )
    print(
        f"  excluded: {n_removed} removed/deleted, {n_showcase} showcase/supply (not requests)"
    )
    for cat, n in Counter(req["category"]).most_common():
        print(f"  {n:6d}  {100 * n / n_req:5.1f}%  {cat}")


def stats(args: argparse.Namespace) -> None:
    rows = build_clean_rows(raw_path(args.data_dir))
    if not rows:
        print("no data; run scrape first.")
        return
    include = subreddit_include(args)
    if include is not None or args.general_only:
        subreddit_default = load_taxonomy(args.taxonomy).SUBREDDIT_DEFAULT
        rows = [
            r
            for r in rows
            if keep_subreddit(
                r["subreddit"], include, args.general_only, subreddit_default
            )
        ]
        if not rows:
            print("no posts match the subreddit filter.")
            return
    months = sorted({r["year_month"] for r in rows})
    print(
        f"stats: {len(rows)} unique posts, {months[0]}..{months[-1]} ({len(months)} months)"
    )
    print(f"  cohorts: {dict(Counter(r['cohort'] for r in rows))}")
    print(f"  by subreddit: {dict(Counter(r['subreddit'] for r in rows))}")
    paid = Counter(r["paid"] for r in rows)
    print(
        f"  paid: True={paid.get(True, 0)} False={paid.get(False, 0)} unknown={paid.get(None, 0)}"
    )
    ai = Counter(r["ai_ok"] for r in rows)
    print(
        f"  ai_ok: True={ai.get(True, 0)} False={ai.get(False, 0)} unknown={ai.get(None, 0)}"
    )
    print(f"  removed/deleted: {sum(1 for r in rows if r['is_removed'])}")
    top_flairs = Counter(r["flair"] for r in rows if r["flair"]).most_common(8)
    print(f"  top flairs: {top_flairs}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser(
        "scrape", help="collect raw posts from Arctic-Shift (resumable)"
    )
    sc.add_argument("--subreddits", default=",".join(DEFAULT_SUBREDDITS))
    sc.add_argument("--start-month", default=START_MONTH)
    sc.add_argument("--end-month", default="", help="YYYY-MM (default: current month)")
    sc.add_argument(
        "--cap",
        type=int,
        default=DEFAULT_MONTHLY_CAP,
        help="max posts per (subreddit, month)",
    )
    sc.add_argument("--data-dir", default=DATA_DIR)
    sc.add_argument(
        "--use-reddit-api",
        action="store_true",
        help="top up freshest month via official API (needs .env)",
    )
    sc.set_defaults(func=scrape)

    cl = sub.add_parser(
        "clean", help="JSONL -> clean.{csv,parquet} with derived columns"
    )
    cl.add_argument("--data-dir", default=DATA_DIR)
    cl.add_argument("--output-dir", default=OUTPUT_DIR)
    cl.add_argument("--format", choices=["csv", "parquet", "both"], default="csv")
    cl.set_defaults(func=clean)

    ca = sub.add_parser("categorize", help="keyword categorize -> report + counts")
    ca.add_argument("--data-dir", default=DATA_DIR)
    ca.add_argument("--output-dir", default=OUTPUT_DIR)
    ca.add_argument(
        "--general-only",
        action="store_true",
        help="exclude single-purpose subs (e.g. r/estoration) to de-bias weights",
    )
    ca.add_argument("--subreddits", default="", help="restrict to a comma list of subs")
    ca.add_argument(
        "--taxonomy",
        choices=["consumer", "business"],
        default="consumer",
        help="which rule set to classify with (default: consumer)",
    )
    ca.add_argument(
        "--edits-only",
        action="store_true",
        help="business: restrict to edits of an existing asset (consumer-comparable)",
    )
    ca.add_argument(
        "--examples",
        type=int,
        default=4,
        help="example titles per category in the report",
    )
    ca.set_defaults(func=categorize)

    st = sub.add_parser("stats", help="coverage / flair / paid-vs-free diagnostics")
    st.add_argument("--data-dir", default=DATA_DIR)
    st.add_argument(
        "--general-only", action="store_true", help="exclude single-purpose subs"
    )
    st.add_argument("--subreddits", default="", help="restrict to a comma list of subs")
    st.add_argument(
        "--taxonomy",
        choices=["consumer", "business"],
        default="consumer",
        help="taxonomy whose single-purpose subs --general-only drops",
    )
    st.set_defaults(func=stats)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
