"""Business/commercial counterpart to ``category_rules.py`` -- the rules that map
a *business* image request to a demand category.

Same audit surface and three-signal cascade as the consumer taxonomy (keyword on
title+selftext, then flair, then single-purpose-subreddit default); see
``category_rules.py`` for the shared mechanics. Two things differ:

  1. The categories are commercial intents (logo placement, vectorize a logo,
     ecommerce product photo, virtual staging, mockups, ad creative, packaging,
     ...) rather than the consumer ones (restore, remove person, retouch).

  2. Business subs are mostly NOT demand -- gig boards are flooded with supply
     (freelancers advertising) and design/business communities with showcase,
     feedback, and discussion. So everything except the pure request subs
     (``UNGATED_SUBS``) passes a *demand gate*: a row only counts if ``DEMAND_RE``
     matches title+selftext+flair (an actual ask -- "can someone...", "[hiring]",
     "looking for someone to...", "WTB"). ``SHOWCASE_RE`` / ``EXCLUDE_FLAIRS`` are
     also expanded with supply/showcase vocabulary. Together these let us scrape a
     wide, high-volume net without drowning the signal in non-requests.

Each request is also tagged edit-vs-create via ``EDIT_CATEGORIES``: business demand
is dominated by create-from-scratch work (logo/flyer/packaging design), so the
categories that manipulate an *existing* asset are listed there. ``is_edit`` is
simply membership of the assigned category in that set, which keeps the
edit-vs-create split in lock-step with the (already audited) category buckets
rather than introducing a second, separately-tunable regex pass.
"""

from __future__ import annotations

import re

# Keyword rules over title + selftext. Ordered, priority-first: specific
# edit-of-an-existing-asset intents win over the generic from-scratch design
# verbs, so "place my logo on the bottle" and "png to vector" don't collapse
# into a bare "logo design".
RULES: list[tuple[str, str]] = [
    (
        "Virtual staging / real-estate edit",
        r"virtual(ly)? stag|de-?clutter|empty (the )?room|furnish|real ?estate|"
        r"replace (the )?sky|sky replace|twilight (photo|edit|conversion)|"
        r"day ?to ?dusk|\bmls\b",
    ),
    (
        "Ghost-mannequin / apparel product photo",
        r"ghost ?mannequin|invisible mannequin|\bflat ?lay\b|on[- ]model|neck ?joint",
    ),
    (
        "Ecommerce product photo / white background",
        r"white background|product (photo|image|shot)|listing (image|photo)|"
        r"amazon (listing|image|photo)|clipping path|\bcut ?out\b|infographic|"
        r"hero image|catalog|on (a )?white|pure white",
    ),
    (
        "Remove / replace background",
        r"remove (the )?background|background remov|replace (the )?background|"
        r"transparent (background|png)|\bbg\b|backdrop|green ?screen|"
        r"knock ?out the background",
    ),
    (
        "Composite product / object into scene",
        r"composit|place (the |my )?product|product in(to)? (a )?(scene|setting|environment)|"
        r"drop (it|this|the product) (in|into)|"
        r"insert .* (in|into) (the )?(scene|image|photo|background)|in[- ]context",
    ),
    (
        "Add / place logo onto image",
        r"add (my |the |a |our )?logo|place (my |the |our )?logo|"
        r"put (my |the |our )?logo|logo on(to)? (the|this|my|a)|"
        r"slap (my |the )?logo|overlay (my |the )?logo|brand(ing)? on (the|this|my)",
    ),
    (
        "Vectorize / redraw / recreate logo",
        r"vectori[sz]e|\bvector\b|png to (vector|svg|ai|eps)|to (svg|eps|\.ai)|"
        r"\.svg|\.eps|\.ai\b|redraw|re-?create (this|the|my) (logo|design|graphic)|"
        r"trace (this|the|my)|clean ?up (the |my )?logo|"
        r"high[- ]?res(olution)? (version of )?(the |my )?logo",
    ),
    (
        "Logo design",
        r"\blogo\b|logotype|wordmark|brand ?mark|\bemblem\b|monogram",
    ),
    (
        "Mockup (product / apparel / packaging)",
        r"mock ?up|mockups?|t-?shirt mock|apparel mock|bottle mock|box mock|"
        r"3d render|product render",
    ),
    (
        "Packaging / label / sticker",
        r"packag|\blabel\b|box design|pouch|carton|\bsticker\b|\btin\b|"
        r"can design|bottle design|wrapper",
    ),
    (
        "Ad / social-media creative / banner / thumbnail",
        r"\bads?\b|ad creative|\bbanner\b|thumbnail|facebook ad|google ad|"
        r"insta(gram)? (post|story|reel)|social ?media (post|graphic|content)|"
        r"\bcover (photo|art|image)\b|\bheader\b|youtube",
    ),
    (
        "Text / typography / copy placement",
        r"add (the |some )?text|typograph|headline|\bcaption\b|"
        r"put (the |some )?text|replace (the )?text|change (the )?text|"
        r"\bfont\b|lettering",
    ),
    (
        "Flyer / poster / menu / brochure",
        r"\bflyer\b|\bposter\b|\bmenu\b|brochure|leaflet|pamphlet|"
        r"invitation|certificate|\bprogram\b",
    ),
    (
        "Business card / stationery",
        r"business ?card|letterhead|stationery|name ?card|invoice template",
    ),
    (
        "Brand color / consistency match",
        r"brand colou?r|match (the |our )?colou?r|colou?r match|\bpantone\b|"
        r"hex code|brand guidelines|on[- ]brand|colou?r scheme",
    ),
    (
        "Resize / adapt to platform format",
        r"\bresize\b|aspect ratio|different sizes|adapt (it |this )?(for|to)|"
        r"reformat|square version|story size|\b1080|\b4k\b|print ?ready|"
        r"\bdimensions\b|\bdpi\b",
    ),
    (
        "Apparel / merch design",
        r"t-?shirt design|tee design|hoodie design|\bmerch\b|jersey design|"
        r"apparel design|embroider|print[- ]on[- ]demand",
    ),
]

# Flairs on the business request subs (Free / Paid / Idea / Hiring) say nothing
# about *what* is wanted, so there is no useful flair-to-category signal here.
FLAIR_RULES: list[tuple[str, str]] = []

# Single-purpose subreddits: classify otherwise-unmatched posts by context.
# Only r/realestatephotography is single-intent enough to default; the request
# subs (DesignRequests, ...) are multi-intent and must NOT be defaulted.
SUBREDDIT_DEFAULT: dict[str, str] = {
    "realestatephotography": "Virtual staging / real-estate edit",
}

# Categories that manipulate an *existing* asset (vs. create-from-scratch).
# ``is_edit`` = assigned category in this set. The edits-only view over these is
# the apples-to-apples comparison with the consumer (edit-only) benchmark.
EDIT_CATEGORIES: set[str] = {
    "Virtual staging / real-estate edit",
    "Ghost-mannequin / apparel product photo",
    "Ecommerce product photo / white background",
    "Remove / replace background",
    "Composite product / object into scene",
    "Add / place logo onto image",
    "Vectorize / redraw / recreate logo",
    "Mockup (product / apparel / packaging)",
    "Text / typography / copy placement",
    "Brand color / consistency match",
    "Resize / adapt to platform format",
}

# Demand gate. The consumer subs were pure request boards -- every post is an
# edit request. Most business subs are NOT: gig boards are dominated by supply
# (freelancers advertising), and design/business communities are dominated by
# showcase, feedback, and discussion. So OUTSIDE the pure request subs
# (UNGATED_SUBS) a post only counts as demand if it actually asks for work --
# DEMAND_RE over title + selftext + flair. This is what lets us scrape a wide
# net of high-volume subs without drowning the signal in showcase/discussion.
UNGATED_SUBS: set[str] = {"DesignRequests"}

# Objects a commercial image request is about, and the imperative verbs that act
# on them -- used to recognise "Remove the background", "Need a white background
# for my listing photos" as asks even when no role/"can someone" phrasing is
# present (common in business-owner subs).
_OBJ = (
    r"photo|image|logo|background|backdrop|product|listing|thumbnail|banner|"
    r"mockup|flyer|poster|graphic|design|sky|\btext\b|label|packaging|headshot|"
    r"\broom\b|space|property|\bhome\b|wallpaper"
)
_VERB = (
    r"need|remove|edit|design|make|create|fix|enhance|composite|vectori[sz]e|resize|"
    r"retouch|colou?ri[sz]e|restore|crop|cut ?out|add|replace|change|put|stage|"
    r"clean ?up|touch ?up|photoshop"
)
DEMAND_RE = re.compile(
    # explicit hiring / request framing
    r"\bhiring\b|\[\s*(hiring|task|request|req|paid)\s*\]|"
    r"can (someone|somebody|anyone|you)|could (someone|somebody|anyone|you)|"
    r"would (someone|somebody|anyone)|anyone (able|who can|willing)|"
    r"looking for (a |an |someone )?(designer|editor|artist|illustrator|photographer|"
    r"help|someone to)|"
    r"\bi need\b|requesting|\brequest\b|want to buy|\bwtb\b|"
    r"help me (make|edit|design|create|with)|make me (a|an)|"
    r"paying (for|someone)|will pay|\bbudget\b|commission (a|an|someone|for)|"
    # a "need"/imperative-edit verb acting on a commercial object, allowing an
    # adjective or two in between ("stage this empty living room", "need a pure
    # white background"). Gap-capped so it stays within one clause.
    rf"\b({_VERB})\b[^.?!]{{0,40}}\b({_OBJ})\b",
    re.I,
)

# Posts that are not demand: finished-work showcases, freelancers advertising,
# meta/discussion. Exact-match against the normalized (lowercased) flair.
EXCLUDE_FLAIRS: set[str] = {
    "for hire",
    "for-hire",
    "forhire",
    "offer",
    "closed",
    "commission",
    "commissions",
    "commissions open",
    "showcase",
    "sharing work",
    "career advice",
    "feedback",
    "feedback needed",
    "discussion",
    "portfolio",
    "cv review",
    "news",
    "meta",
    "result",
    "results",
    "rant",
    "vent",
}

# Title-level supply / showcase filter. Expanded well beyond the consumer set to
# catch the freelancer-advertising vocabulary that floods business design subs;
# the leading-bracket anchor catches "[For Hire] ..." titles that carry no flair.
SHOWCASE_RE = re.compile(
    r"^\s*\[?\s*for ?hire|for ?hire\]|\bfor hire\b|^\s*\[?\s*offer\b|open for (work|comm)|"
    # feedback/critique posts are showcase, not a request to do the work
    r"\bfeedback\b|critique|thoughts on|rate my|roast my|\bc ?& ?c\b|cc welcome|"
    r"my (recent )?work|hit me up|portfolio|"
    r"offering (free )?(graphic )?design|i can (make|do|design) (your|a|you)|"
    r"\bi do\b.*(edit|design|logo)|commissions? open|dm (me )?if interested|"
    r"available for|taking (on )?clients|hire me|my services|slots open|"
    r"\brates\b|\$\d+ ?/ ?(hr|hour)",
    re.I,
)


def compile_rules(rules: list[tuple[str, str]]) -> list[tuple[str, re.Pattern[str]]]:
    """Pre-compile a rule list (case-insensitive)."""
    return [(category, re.compile(pattern, re.I)) for category, pattern in rules]
