# Benchmark participants, uploads and prompts

> Part of the Rapidata agent skill: `python -m rapidata skill benchmark-participants`. The **Task design rules** and **Key Gotchas** in the main guide (`python -m rapidata skill`) apply to everything here.

Creating benchmarks and leaderboards: `python -m rapidata skill benchmarks`.

## Uploads and recovery

```python
# Upload additional media to the same participant. Returns
# (identifiers uploaded, failures) where failures is list[FailedUpload[SampleUpload]].
# Raises ValueError if assets and identifiers differ in length.
uploaded, failed = participant.upload_media(
    assets=["mountain_v3_extra.png"],
    identifiers=["A serene mountain landscape"],
    data_type="media",
)

# Recover a partial upload — ask the server which identifiers are still short and
# re-send every asset belonging to those identifiers. Safe to call repeatedly (the
# backend rejects samples the participant already holds, so no duplication) and stops
# early once a round stops closing the gap. Works for any participant, including ones
# fetched from benchmark.participants. Raises ValueError on assets/identifiers length
# mismatch. Returns (identifiers uploaded across all rounds, failures still short on
# the last round → list[FailedUpload[SampleUpload]]).
uploaded, still_failed = participant.retry_missing(
    assets=["mountain_v3.png", "city_v3.png"],
    identifiers=["A serene mountain landscape", "A futuristic city"],
    data_type="media",
)

# Per-identifier count (server truth) of how many samples are still outstanding.
# Fully-uploaded identifiers are omitted, so an empty Counter means nothing is short.
missing = participant.missing_counts(
    identifiers=["A serene mountain landscape", "A futuristic city"],
)  # Counter[str]
```

## Participants and prompts

```python
participant.deprecate()           # No new matchups; row and votes leave the default standings (reversible)
participant.restore()             # Undo deprecate(). disable()/enable() are deprecated aliases
participant.promote()             # Candidate joins the field: models submitted later play it (no run starts);
                                  #   RapidataError 400 if it isn't a candidate
participant.get_elo()             # Aggregated Elo across all leaderboards (None if not yet computed or deprecated)
participant.delete()              # Delete participant and its uploaded media (cannot be undone)

# Update participant metadata — adding a model and pricing it are separate calls (see **Participant pricing** below)
participant.rename("New Name")    # Rename the participant
participant.set_price(0.04, unit="image")  # List price in USD per unit ("image" | "video_second" | "million_tokens");
                                           #   both required. ValueError on a non-positive or non-finite price, or an unknown unit
participant.clear_price()         # Remove the price
participant.price                 # float | None — USD per price_unit
participant.price_unit            # str | None — "image" | "video_second" | "million_tokens"

# List participants and their status (p.price / p.price_unit are None for unpriced models)
for p in benchmark.participants:
    print(p.id, p.name, p.status, p.price, p.price_unit)

for lb in benchmark.leaderboards:  # list[RapidataLeaderboard]
    print(lb.id, lb.name)

# Prompts — original language and English translation (aligned by index)
print(benchmark.prompts)          # As originally provided
print(benchmark.english_prompts)  # Server-side English translations, aligned by index
print(benchmark.identifiers)      # Prompt identifiers, aligned by index
print(benchmark.structured_tags)  # list[list[Tag]] — tags with categories, aligned by index
print(benchmark.origins)          # list[Origin | None], aligned by index
print(benchmark.tags)             # list[list[str]] — values only (categories dropped)
print(benchmark.get_tag_counts()) # DataFrame of every tag: value, category, prompt_count — one request,
                                  # no prompt paging; `value` is what the standings `tags=` filters take
print(benchmark.prompt_assets)    # list[list[str] | None], aligned by index — the reference asset(s)
                                  # of each prompt. Each entry is the list of assets for that prompt
                                  # (one element for a single asset, several for a multi-asset), or None
                                  # for text/null prompts. This is the same shape add_prompts /
                                  # create_new_benchmark take, so a value read back can be fed straight in
```

## Minimum samples per prompt (`benchmark.update`)

A benchmark can require a minimum number of samples (assets) per prompt. Set it with `benchmark.update(min_assets_per_prompt=...)`:

```python
def update(self, min_assets_per_prompt: int | None = None) -> None: ...
```

- Only the arguments you pass are changed; anything omitted keeps its stored value.
- `min_assets_per_prompt`, when provided, must be an `int` and **≥ 2** (`bool` is explicitly rejected), else `ValueError`.

The gate is **advisory**, not a rejection. When a participant is submitted (`participant.run()` or `benchmark.run()`) with any prompt filled below the required count, the submission still completes and the participant is still marked `SUBMITTED`, but a `logger.warning` reports the shortfall. Each shortfall prompt is formatted as `'identifier' (asset_count/required)` — e.g. `model-0: 'cat' (2/4)`. `benchmark.run()` emits one aggregated warning listing every affected participant (by display name) and its shortfall prompts.

## Participant pricing (`set_price` / `clear_price`)

A benchmark participant can carry the model's list price so it appears on the benchmark's **"Score vs. cost"** chart. Pricing is participant metadata, like `rename`: add the model first (`add_model` / `evaluate_model` take no price arguments), then price the returned participant.

```python
def set_price(self, price: float, unit: Literal["image", "video_second", "million_tokens"]) -> None: ...
def clear_price(self) -> None: ...

participant.price       # float | None — USD per price_unit
participant.price_unit  # str | None   — "image" | "video_second" | "million_tokens"
```

- `price` is in **USD per unit** and must be a finite number greater than 0; `unit` must be one of the three literals. Both are required — an invalid price or an unknown unit raises `ValueError`.
- `clear_price()` removes the price; `price` and `price_unit` read back `None` afterwards.
- Unpriced participants are **hidden** from the cost chart, and only participants quoted in the benchmark's **majority unit** are plotted. Set the price only when the vendor publishes a list price you are confident in; otherwise leave it unset and say so.

## `SampleUpload`

Importable from the top-level `rapidata` package. A frozen dataclass representing one media/identifier pair as submitted to a participant. It is the `item` carried by each `FailedUpload` returned from `upload_media` / `retry_missing`, so a caller can re-submit a failed pair directly.

```python
from rapidata import SampleUpload

@dataclass(frozen=True)
class SampleUpload:
    media: str        # media asset (local path or URL) or text content
    identifier: str   # the benchmark identifier/prompt the media was paired with

    def __str__(self) -> str: ...   # "identifier (media)"
```

## `Tag` and `Origin`

Both are importable from the top-level `rapidata` package (and from `rapidata.types`).

```python
from rapidata import Tag, Origin

@dataclass
class Tag:
    value: str
    category: str | None = None

@dataclass
class Origin:
    source: str
```

`tags` on `create_new_benchmark`, `add_prompts` and `update_prompt` accepts plain strings, `Tag`s, or a mix — a bare string becomes `Tag(value, category=None)`. `origins` accepts an `Origin`, a plain string (mapped to `Origin(source)`), or `None`, one per prompt.

```python
benchmark = client.mri.create_new_benchmark(
    name="Tagged Benchmark",
    identifiers=["scene_1", "scene_2"],
    prompts=["A sunny beach", "A car in a garage"],
    tags=[
        [Tag("beach", category="scene"), "outdoor"],
        [Tag("vehicle", category="object"), "indoor"],
    ],
    origins=["coco", "coco"],
)
```

`identifiers`, `prompts`, `prompt_assets`, `tags` and `origins` must all have the same length or be `None`.

## Prompt assets shape (`prompt_assets`)

On `create_new_benchmark` and `add_prompts`, `prompt_assets` is a **list with one entry per prompt**, each entry being a `list[str]` of image / video / audio URLs or file paths shown alongside that prompt (or `None` for no asset). A single asset is a one-element list; several entries in one list are registered together as one multi-asset. This matches the `media_contexts` shape of job definitions, and the write shape equals the read shape — a value read from `benchmark.prompt_assets` can be fed straight back in.

```python
prompt_assets = [
    ["https://assets.rapidata.ai/prompt_1.jpg"],                        # single asset
    ["https://example.com/pan_left.gif", "https://example.com/street.jpg"],  # one multi-asset
    None,                                                               # no asset (e.g. text prompt)
]
```

Passing a bare `str` per prompt is still accepted but **deprecated** — it is wrapped in a single-element list and logs one warning per call. Passing anything that is not a list raises `ValueError` ("Prompt assets must be a list with one entry per prompt, each a list of strings or None."); an empty list or empty-string entry also raises `ValueError`.

## `benchmark.update_prompt(identifier, tags=None, origin=None)`

Replaces the tags and/or sets the origin of an already-registered prompt. A field left as `None` is not sent and stays unchanged; local caches are updated in place. Raises `ValueError` if both are `None` ("Provide tags and/or origin to update."), on bad tag/origin types, or if the identifier is not registered on the benchmark.

## Prompt-tag scoping (`included_tags` / `excluded_tags`)

These restrict **which benchmark prompts the leaderboard collects matchups for**. A prompt is used when it carries at least one `included_tags` value and no `excluded_tags` value; `excluded_tags` always wins, and a non-empty `included_tags` drops untagged prompts. Matching is on the tag value only — the category is irrelevant. The filter is applied when a run starts, not snapshotted at creation, and is fixed for the life of the leaderboard.

Distinct from `get_standings(tags=...)`, which filters what you read back rather than what gets collected.

## Example

### Model Benchmark — Recovering a Partial Upload

If some samples fail to upload (e.g. a flaky network), recover without re-sending
everything. `add_model` already runs an automatic recovery sweep on its own
failures, but you can also drive recovery yourself on any participant — including
ones fetched from `benchmark.participants`.

```python
from rapidata import RapidataClient, SampleUpload

client = RapidataClient()
benchmark = client.mri.get_benchmark_by_id("benchmark_id")

MEDIA = ["dalle_mountain.png", "dalle_city.png", "dalle_wizard.png"]
IDENTIFIERS = ["A serene mountain landscape", "A futuristic city at night", "A wise wizard portrait"]

participant = next(p for p in benchmark.participants if p.name == "DALL-E 3")

# Ask the server how many samples each identifier is still short (server truth).
# Fully-uploaded identifiers are omitted, so an empty Counter means nothing is
# outstanding.
missing = participant.missing_counts(IDENTIFIERS)
if missing:
    print(f"Still short: {dict(missing)}")

    # Re-send only the assets for the short identifiers. Safe to call repeatedly:
    # the backend rejects samples the participant already holds, so nothing is
    # duplicated, and it stops early once a round stops closing the gap. Returns
    # the identifiers uploaded across all rounds and any still short on the last.
    uploaded, failures = participant.retry_missing(MEDIA, IDENTIFIERS)
    print(f"uploaded {len(uploaded)} across all rounds")

    # Each failure's item is a SampleUpload(media, identifier) you can re-submit
    # directly; it also carries the failure reason and backend trace id.
    for fu in failures:
        sample: SampleUpload = fu.item
        print(f"still failed: {sample} — {fu.error_message} (trace {fu.trace_id})")
```
