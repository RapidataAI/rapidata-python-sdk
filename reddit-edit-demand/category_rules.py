"""Priority-ordered keyword rules mapping an edit request to a demand category.

This module is the *audit surface* of the whole tool: the taxonomy a benchmark
should weight by is only as defensible as these rules, so they live here as
plain data you can read, edit, and diff in review -- not buried in the script.

How matching works (see ``categorize_text`` in ``reddit_edit_demand.py``):
  - Each rule is ``(category, pattern)`` where ``pattern`` is a regex alternation
    of keywords matched case-insensitively against ``title + " " + selftext``.
  - Rules are tried top-to-bottom and the FIRST match wins. Order therefore
    encodes priority: put the more specific / higher-signal intents first so a
    generic word ("add", "remove") doesn't swallow a request that is really
    about restoration or watermark removal.
  - Anything matching nothing falls into the implicit ``UNMATCHED`` bucket.

Why these categories: they are use-case (demand) categories, deliberately
broader than the capability taxonomies (Artificial Analysis / KontextBench:
add / remove / modify / text / style). Restoration, quality/upscale and
"composite people together" have no home in those lists yet are among the
highest-volume real requests -- which is the entire point of measuring demand.

Tuning: reorder or extend freely. After editing, re-run ``categorize`` and read
the per-category example titles it prints to confirm the buckets still hold.
"""

from __future__ import annotations

import re

# Ordered, priority-first. (category, regex-alternation-of-keywords)
RULES: list[tuple[str, str]] = [
    # High-signal, specific intents first ------------------------------------
    (
        "Restoration / colorize old photo",
        r"restor|repair|old photo|damaged|faded|torn|scratch|crease|"
        r"colou?ri[sz]e|black ?and ?white|deteriorat",
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
        r"\badd\b|insert|put .* (in|on|into)|\bplace\b|superimpose",
    ),
    (
        "Retouch face / body / skin",
        r"retouch|\bskin\b|blemish|acne|smooth|wrinkle|\bteeth\b|whiten|"
        r"slim|skinn|thinner|\bweight\b|\btan\b|muscle|\babs\b|jawline",
    ),
    (
        "Expression / eyes / smile",
        r"smil|eyes open|open .*eyes|\bfrown\b|expression|looking at|" r"close.*eyes",
    ),
    (
        "Quality / upscale / unblur / enhance",
        r"unblur|deblur|sharpen|upscale|resolution|\benhance\b|quality|"
        r"pixelat|blurry|\bhd\b|clarity|denoise",
    ),
    (
        "Color / lighting correction",
        r"brighten|lighting|exposure|colou?r correct|contrast|saturat|"
        r"white balance|\bhdr\b|too dark|too bright",
    ),
    (
        "Change color of object",
        r"change (the )?colou?r|recolou?r|different colou?r|make it (red|blue|"
        r"green|black|white|pink|purple|yellow)",
    ),
    (
        "Clothing / outfit",
        r"\bshirt\b|clothes|clothing|outfit|\bdress\b|\bsuit\b|\btie\b|"
        r"jersey|hoodie|\bjacket\b",
    ),
]


def compile_rules(
    rules: list[tuple[str, str]] = RULES,
) -> list[tuple[str, re.Pattern[str]]]:
    """Pre-compile the rule patterns once (case-insensitive)."""
    return [(category, re.compile(pattern, re.I)) for category, pattern in rules]
