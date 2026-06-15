"""Rules that map an edit request to a demand category -- the *audit surface*.

The taxonomy a benchmark weights by is only as defensible as these rules, so
they live here as plain, readable, diffable data instead of buried in the
script. There are three signals, applied in this order by ``categorize_post``
in ``reddit_edit_demand.py``:

  1. KEYWORD (``RULES``) on title + selftext -- highest precision: the request
     literally says what to do ("remove the guy", "colorize this").
  2. FLAIR (``FLAIR_RULES``) -- many subs tag the request type in the flair, so
     a post titled "My grandmother, 1955" with no edit verb is still a clear
     "Restoration Request". This recovers the large tail of sentimental titles.
  3. SUBREDDIT DEFAULT (``SUBREDDIT_DEFAULT``) -- a single-purpose sub (e.g.
     r/estoration is entirely restoration) classifies its otherwise-unmatched
     posts by context.

Matching within RULES / FLAIR_RULES: each entry is ``(category, pattern)``, a
regex alternation matched case-insensitively; rules are tried top-to-bottom and
the FIRST match wins, so order = priority. Anything still unmatched is
``UNMATCHED``.

Not every post is demand. ``EXCLUDE_FLAIRS`` and ``SHOWCASE_RE`` mark finished-
work showcases / meta posts; removed-or-deleted posts have no text. Both are
reported separately and kept out of the category-share denominator -- otherwise
"unmatched" conflates "we missed it" with "nothing to match".

Categories are use-case (demand) categories, deliberately broader than the
capability taxonomies (Artificial Analysis / KontextBench: add / remove /
modify / text / style): restoration, quality/upscale and "composite people
together" are among the highest-volume real requests yet have no home there.

Tuning: edit freely, then re-run ``categorize`` and read the per-category
example titles it prints to confirm the buckets still hold.
"""

from __future__ import annotations

import re

# Keyword rules over title + selftext. Ordered, priority-first.
RULES: list[tuple[str, str]] = [
    # High-signal, specific intents first ------------------------------------
    (
        "Restoration / colorize old photo",
        r"restor|repair|old photo|damaged|faded|torn|scratch|crease|"
        r"colou?ri[sz]e|black ?and ?white|deteriorat|"
        # "fix/clean up this photo" is overwhelmingly restoration in these subs
        r"clean ?up|cleaned ?up|clean this|fix(ed)? (this )?(up |the )?(photo|picture|image|pic)|"
        r"\bglare\b|sun ?damage|water ?damage|overexpos|yellow(ed|ing)|\bstain",
    ),
    (
        "Remove watermark / text / logo / date",
        r"watermark|remove (the )?text|remove.*logo|\blogo\b|date ?stamp|"
        r"timestamp|remove.*sign|caption|remove.*label",
    ),
    # The single largest real category -- generic but dominant ---------------
    (
        "Remove object / person / photobomber",
        r"\bremove\b|get rid of|take out|\bdelete\b|erase|photobomb|"
        r"crop out|edit out|remove.*background",
    ),
    (
        "Background change / removal",
        r"background|backdrop|\bbg\b|green ?screen|white background|transparent",
    ),
    (
        "Combine / composite people together",
        r"combine|composit|merge|same (picture|photo|image)|\btogether\b|"
        r"into one|put (us|them|him|her|me) (in|with)|standing (with|next)",
    ),
    (
        "Add object / person / element",
        r"\badd\b|insert|put .* (in|on|into)|\bplace\b|superimpose|\breplace\b|"
        r"\bswap\b|make .* look like|turn (me|us|this|him|her|it) into",
    ),
    (
        "Retouch face / body / skin",
        r"retouch|\bskin\b|blemish|acne|smooth|wrinkle|\bteeth\b|whiten|"
        r"slim|skinn|thinner|\bweight\b|\btan\b|muscle|\babs\b|jawline|"
        r"hair ?cut|hairstyle|\bhair\b",
    ),
    (
        "Expression / eyes / smile",
        r"smil|eyes open|open .*eyes|\bfrown\b|expression|looking at|close.*eyes",
    ),
    (
        "Quality / upscale / unblur / enhance",
        r"unblur|deblur|sharpen|upscale|resolution|\benhance\b|quality|"
        r"pixelat|blurry|\bhd\b|clarity|denoise|"
        r"legib|readable|decipher|make out|\bclearer\b|crisp",
    ),
    (
        "Color / lighting correction",
        r"brighten|lighting|exposure|colou?r correct|contrast|saturat|"
        r"white balance|\bhdr\b|too dark|too bright",
    ),
    (
        "Change color of object",
        r"change (the )?colou?r|recolou?r|different colou?r|"
        r"make (it|the [\w ]{1,20}) (red|blue|green|black|white|pink|purple|"
        r"yellow|gray|grey|gold|silver|orange|brown)",
    ),
    (
        "Clothing / outfit",
        r"\bshirt\b|clothes|clothing|outfit|\bdress\b|\bsuit\b|\btie\b|"
        r"jersey|hoodie|\bjacket\b",
    ),
    # Lower-priority intents: placed after the verbs above so e.g. "crop out the
    # person" lands in Remove, while a bare "crop this to square" lands here.
    (
        "Resize / crop / aspect ratio",
        r"\bresize\b|\bcrop\b|aspect ratio|make .* (wider|taller|bigger|smaller|square)|"
        r"fit (an? )?(iphone|phone|screen|wallpaper|print|frame)|\bdimensions\b|stretch",
    ),
    (
        "Vectorize / convert format",
        r"vectori[sz]e|\bvector\b|(to|into) (a )?svg|\.svg|"
        r"convert .* (to|into) (png|jpe?g|pdf|svg|vector)|\btrace\b",
    ),
]

# Flair rules: fall-back signal when the title carries no edit verb. Only flairs
# that genuinely name a category belong here -- status/payment flairs
# (serious / paid / free / solved) say nothing about *what* edit is wanted.
FLAIR_RULES: list[tuple[str, str]] = [
    ("Restoration / colorize old photo", r"restor|colou?ri[sz]"),
    ("Remove watermark / text / logo / date", r"watermark|text"),
]

# Single-purpose subreddits: classify otherwise-unmatched posts by context.
SUBREDDIT_DEFAULT: dict[str, str] = {
    "estoration": "Restoration / colorize old photo",
}

# Posts that are not demand: finished-work showcases, results, meta. Excluded
# from the category-share denominator (reported separately).
EXCLUDE_FLAIRS: set[str] = {
    "result",
    "results",
    "meta",
    "comparison",
    "psa",
    "announcement",
}
SHOWCASE_RE = re.compile(
    r"commission|open for work|open for comm|my (recent )?work|hit me up|"
    r"portfolio|for hire|\bi do\b.*(edit|restor)",
    re.I,
)


def compile_rules(rules: list[tuple[str, str]]) -> list[tuple[str, re.Pattern[str]]]:
    """Pre-compile a rule list (case-insensitive)."""
    return [(category, re.compile(pattern, re.I)) for category, pattern in rules]
