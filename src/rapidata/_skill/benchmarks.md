# Benchmarks (Model Ranking Insights)

> Part of the Rapidata agent skill: `python -m rapidata skill benchmarks`. The **Task design rules** and **Key Gotchas** in the main guide (`python -m rapidata skill`) apply to everything here; parameters shared by every job type are in `python -m rapidata skill reference`.

To compare **two** image or video models once, a template is quicker: `python -m rapidata skill comparison`.

Compare and rank AI models on leaderboards. Supports images, videos, audio, and text.

```python
# Create benchmark
benchmark = client.mri.create_new_benchmark(
    name="AI Art Competition",
    prompts=["A serene mountain landscape", "A futuristic city"],
    # identifiers=[...],        # Optional: stable ids for each prompt
    # prompt_assets=[["ref1.jpg"], ["ref2.jpg"]],  # Optional: one list of asset URLs/paths per prompt
    #                                              #   (several entries in a list = one multi-asset), or None
    # tags=[...],               # Optional: per-prompt tag lists; entries may be str, Tag, or a mix
    # origins=[...],            # Optional: per-prompt Origin or plain source string
)

# Add prompts later if needed (one or many, matched up by index)
benchmark.add_prompts(
    prompts=["A quiet lake at dawn"],
    # identifiers=["dawn_lake"],   # Optional: stable id per prompt
    # prompt_assets=[["ref.jpg"]],  # Optional: one list of asset URLs/paths per prompt (or None)
    # tags=[["landscape"]],        # Optional: list of tag lists, one per prompt (str and/or Tag)
    # origins=["coco"],            # Optional: Origin / source string / None, one per prompt
)

# Replace tags and/or set the origin of an already-registered prompt
benchmark.update_prompt("dawn_lake", tags=["abstract", "surreal"], origin="wikiart")

# Create leaderboard
leaderboard = benchmark.create_leaderboard(
    name="Realism",
    instruction="Which image is more realistic?",
    show_prompt=False,
    show_prompt_asset=False,
    inverse_ranking=False,
    # level_of_detail="high",            # "debug" | "low" | "medium" | "high" | "very high", or a positive int budget
    # min_responses_per_matchup=5,
    # audience_id="...",                 # Optional: id string, RapidataAudience, or RapidataFilteredAudience
    # settings=[...],
    # included_tags=["outdoor"],         # Optional: only collect matchups for prompts carrying one of these tags
    # excluded_tags=["nsfw"],            # Optional: skip prompts carrying any of these tags (always wins)
    # vote_aggregation=VoteAggregation.MAJORITY_VOTE,  # VoteAggregation.MAJORITY_VOTE (default) or ALL_VOTES — how matchup votes are aggregated
    # skip_initial_run=False,            # Leave False unless the user explicitly asks to skip. See "Skipping the initial run" below
)

# Skipping the initial run: the initial run IS the evaluation of the models already in the
# benchmark, so skip_initial_run=True means they are never compared and the leaderboard has
# no standings. Use it only when the user explicitly asks for it, never to save cost or to
# "launch it yourself": skipping marks those models submitted, so a later benchmark.run()
# finds nothing to submit and evaluates nothing. Create-only — not readable back.

# Evaluate a model (creates participant, uploads media, and submits in one step).
# Pair each media item with its prompt via prompts=[...] or identifiers=[...] (one is required).
benchmark.evaluate_model(
    name="MyModel_v2",
    media=["mountain.png", "city.png"],
    prompts=["A serene mountain landscape", "A futuristic city"],
    # identifiers=["mountain", "city"],  # alternative to prompts
    data_type="media",   # "media" (default) or "text"
)

# Or add a model without submitting (for more control). If any sample fails to
# upload, add_model automatically runs a recovery sweep (retry_missing) that diffs
# intended samples against server state and re-uploads only the difference; any
# still-failing samples are logged individually (first 5, then "… and N more") and
# the warning points at participant.retry_missing(...) / participant.missing_counts(...).
participant = benchmark.add_model(
    name="MyModel_v3",
    media=["mountain_v3.png", "city_v3.png"],
    prompts=["A serene mountain landscape", "A futuristic city"],
    data_type="media",
    is_public=True,      # False: only the benchmark's org and staff see it; paired like any other model
    is_candidate=False,  # True: plays the whole field now; later models don't play it until promote()
)

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

# Submit individually or all at once
participant.run()       # Submit one participant (via the batch endpoint as a batch of one).
                        # Submission always completes; if the benchmark has a minimum-samples-per-prompt
                        # gate, any prompt filled below it is logged via logger.warning (advisory, not a rejection).
benchmark.run()         # Submit all unsubmitted (CREATED or SUBMITTABLE) participants in a single batch request
                        # (chunked at 100 ids). Batching evaluates them symmetrically as one run —
                        # each model compared against every other and against the already-submitted
                        # field — rather than as separate per-participant runs.
                        # Emits a single aggregated logger.warning listing any participant that filled a
                        # prompt below the benchmark's minimum-samples-per-prompt gate (advisory; submission still completes).

# Update benchmark configuration (only passed args change; omitted ones keep their stored value)
benchmark.update(
    min_assets_per_prompt=4,      # int >= 2 (bool rejected); ValueError otherwise
)

participant.deprecate()           # No new matchups; row and votes leave the default standings (reversible)
participant.restore()             # Undo deprecate(). disable()/enable() are deprecated aliases
participant.promote()             # Candidate joins the field: models submitted later play it (no run starts);
                                  #   RapidataError 400 if it isn't a candidate
participant.get_elo()             # Aggregated Elo across all leaderboards (None if not yet computed or deprecated)
participant.delete()              # Delete participant and its uploaded media (cannot be undone)

# Update participant metadata — adding a model and pricing it are separate calls (see "Participant pricing")
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

# Get results
standings = leaderboard.get_standings()                    # Pandas DataFrame for one leaderboard
overall = benchmark.get_overall_standings(tags=None, leaderboard_ids=None)  # Aggregated ELO across all leaderboards
matrix_lb = leaderboard.get_win_loss_matrix()              # Pairwise wins/losses for one leaderboard
matrix_bm = benchmark.get_win_loss_matrix(                 # Pairwise wins/losses across leaderboards
    tags=None, participant_ids=None, leaderboard_ids=None, use_weighted_scoring=None,
)
# These four leave deprecated models and their votes out by default;
# include_deprecated=True brings them back and refits every score.
overall_all = benchmark.get_overall_standings(include_deprecated=True)

# All of the read methods above (plus the two below) accept voter-demographic filters
# and run_id — see "Voter demographic filtering".
demographics = benchmark.get_demographics()                # Demographic composition of the voters
breakdown = benchmark.get_standings_breakdown(             # Standings split by a voter dimension
    dimension=BenchmarkDemographicDimension.COUNTRY,
)

# Access the jobs that ran for a leaderboard (one RapidataJob per run, most recent first)
for job in leaderboard.jobs:
    job_results = job.get_results()

# Update leaderboard config live — every mutable setting goes through update();
# only the arguments passed change, all in one PATCH request.
leaderboard.update(
    name="Realism (Updated)",                        # non-empty str
    level_of_detail="very high",                     # Named level or a positive int response budget
    min_responses_per_matchup=7,                     # int >= 3 (bool rejected)
    vote_aggregation=VoteAggregation.MAJORITY_VOTE,  # re-counts already-collected responses
)

# Read-only leaderboard properties (mutate via update(), never by assignment —
# assigning to any of these raises AttributeError)
print(leaderboard.name)                     # str
print(leaderboard.level_of_detail)          # Named level or "custom"
print(leaderboard.min_responses_per_matchup)
print(leaderboard.vote_aggregation)  # VoteAggregation.MAJORITY_VOTE / ALL_VOTES
print(leaderboard.response_budget)   # Exact budget behind level_of_detail
print(leaderboard.included_tags)     # Copies; empty list when unset. Fixed at creation —
print(leaderboard.excluded_tags)     # create a new leaderboard to re-scope

# Open in browser
benchmark.view()
leaderboard.view()

# Find existing benchmarks
benchmarks = client.mri.find_benchmarks(name="AI Art", amount=10)
benchmark = client.mri.get_benchmark_by_id("benchmark_id")
```

### Minimum samples per prompt (`benchmark.update`)

A benchmark can require a minimum number of samples (assets) per prompt. Set it with `benchmark.update(min_assets_per_prompt=...)`:

```python
def update(self, min_assets_per_prompt: int | None = None) -> None: ...
```

- Only the arguments you pass are changed; anything omitted keeps its stored value.
- `min_assets_per_prompt`, when provided, must be an `int` and **≥ 2** (`bool` is explicitly rejected), else `ValueError`.

The gate is **advisory**, not a rejection. When a participant is submitted (`participant.run()` or `benchmark.run()`) with any prompt filled below the required count, the submission still completes and the participant is still marked `SUBMITTED`, but a `logger.warning` reports the shortfall. Each shortfall prompt is formatted as `'identifier' (asset_count/required)` — e.g. `model-0: 'cat' (2/4)`. `benchmark.run()` emits one aggregated warning listing every affected participant (by display name) and its shortfall prompts.

### Participant pricing (`set_price` / `clear_price`)

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

### `SampleUpload`

Importable from the top-level `rapidata` package. A frozen dataclass representing one media/identifier pair as submitted to a participant. It is the `item` carried by each `FailedUpload` returned from `upload_media` / `retry_missing`, so a caller can re-submit a failed pair directly.

```python
from rapidata import SampleUpload

@dataclass(frozen=True)
class SampleUpload:
    media: str        # media asset (local path or URL) or text content
    identifier: str   # the benchmark identifier/prompt the media was paired with

    def __str__(self) -> str: ...   # "identifier (media)"
```

### `Tag` and `Origin`

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

### Prompt assets shape (`prompt_assets`)

On `create_new_benchmark` and `add_prompts`, `prompt_assets` is a **list with one entry per prompt**, each entry being a `list[str]` of image / video / audio URLs or file paths shown alongside that prompt (or `None` for no asset). A single asset is a one-element list; several entries in one list are registered together as one multi-asset. This matches the `media_contexts` shape of job definitions, and the write shape equals the read shape — a value read from `benchmark.prompt_assets` can be fed straight back in.

```python
prompt_assets = [
    ["https://assets.rapidata.ai/prompt_1.jpg"],                        # single asset
    ["https://example.com/pan_left.gif", "https://example.com/street.jpg"],  # one multi-asset
    None,                                                               # no asset (e.g. text prompt)
]
```

Passing a bare `str` per prompt is still accepted but **deprecated** — it is wrapped in a single-element list and logs one warning per call. Passing anything that is not a list raises `ValueError` ("Prompt assets must be a list with one entry per prompt, each a list of strings or None."); an empty list or empty-string entry also raises `ValueError`.

### `benchmark.update_prompt(identifier, tags=None, origin=None)`

Replaces the tags and/or sets the origin of an already-registered prompt. A field left as `None` is not sent and stays unchanged; local caches are updated in place. Raises `ValueError` if both are `None` ("Provide tags and/or origin to update."), on bad tag/origin types, or if the identifier is not registered on the benchmark.

### Response budgets (`level_of_detail`)

`level_of_detail` accepts a named level or a positive integer response budget. Named levels map to fixed budgets:

| Level | Budget |
|-------|--------|
| `"debug"` | 20 |
| `"low"` | 2,000 |
| `"medium"` | 4,000 |
| `"high"` | 8,000 |
| `"very high"` | 16,000 |

`leaderboard.response_budget` always returns the exact budget. The `level_of_detail` getter returns a named level only on an **exact** budget match and `"custom"` otherwise. Booleans are rejected; a non-positive or non-integer budget raises "Response budget must be a positive integer". Changing the budget applies to future evaluations — already-computed standings are not recomputed.

```python
print(leaderboard.level_of_detail)   # "low"
leaderboard.update(level_of_detail=5000)
print(leaderboard.level_of_detail)   # "custom"
print(leaderboard.response_budget)   # 5000
```

### Updating a leaderboard (`leaderboard.update()`)

`update()` is the single entry point for every mutable leaderboard setting. The properties (`name`, `level_of_detail`, `min_responses_per_matchup`, …) are read-only — assigning to them raises `AttributeError`.

```python
def update(
    self,
    name: str | None = None,
    level_of_detail: LevelOfDetail | int | None = None,
    min_responses_per_matchup: int | None = None,
    vote_aggregation: VoteAggregation | None = None,
) -> None: ...
```

Only the arguments you pass are changed; anything omitted keeps its stored value, and all changes go out in a single PATCH request. A no-argument `update()` sends an empty patch (it does not resend the current state).

| Argument | Validation / effect |
|----------|---------------------|
| `name` | Non-empty string (≥ 1 char), else `ValueError` |
| `level_of_detail` | Named level (`"debug"`/`"low"`/`"medium"`/`"high"`/`"very high"`) or a positive int budget. Takes effect for future evaluations; already-computed standings are not recomputed |
| `min_responses_per_matchup` | `int` and ≥ `3`; `bool` is explicitly rejected, else `ValueError` |
| `vote_aggregation` | A `VoteAggregation` member, else `ValueError`. Because standings are derived from raw responses on every read, changing this re-counts already-collected responses (no re-evaluation needed) |

```python
leaderboard.update(level_of_detail="high")
leaderboard.update(min_responses_per_matchup=5)
leaderboard.update(name="Realism v2")

# Multiple fields in one request:
leaderboard.update(
    name="Realism v2",
    level_of_detail="high",
    min_responses_per_matchup=5,
    vote_aggregation=VoteAggregation.MAJORITY_VOTE,
)
```

### Vote aggregation (`VoteAggregation`)

`VoteAggregation` controls how the individual annotator responses on a single matchup (one comparison of two models on one prompt) are aggregated into that matchup's result. Importable from the top-level `rapidata` package (and from `rapidata.types`).

```python
from rapidata import VoteAggregation
```

| Member | Meaning |
|--------|---------|
| `VoteAggregation.MAJORITY_VOTE` | Collapses each matchup to a single win for the side the majority of responses picked, splitting ties 0.5/0.5. Every matchup weighs the same regardless of how many responses it collected. **Default.** |
| `VoteAggregation.ALL_VOTES` | Counts every individual response as its own matchup, so heavily-answered matchups dominate the standings |

- Set at creation via `benchmark.create_leaderboard(..., vote_aggregation=...)` (defaults to `VoteAggregation.MAJORITY_VOTE`).
- Read back via the read-only `leaderboard.vote_aggregation` property (returns a `VoteAggregation`). For a leaderboard read from the benchmark's listing the value is lazily fetched on first access and cached.
- Change afterwards via `leaderboard.update(vote_aggregation=...)`.

```python
from rapidata import VoteAggregation

leaderboard = benchmark.create_leaderboard(
    name="Realism",
    instruction="Which image is more realistic?",
    vote_aggregation=VoteAggregation.ALL_VOTES,
)
print(leaderboard.vote_aggregation)   # VoteAggregation.ALL_VOTES
```

### Prompt-tag scoping (`included_tags` / `excluded_tags`)

These restrict **which benchmark prompts the leaderboard collects matchups for**. A prompt is used when it carries at least one `included_tags` value and no `excluded_tags` value; `excluded_tags` always wins, and a non-empty `included_tags` drops untagged prompts. Matching is on the tag value only — the category is irrelevant. The filter is applied when a run starts, not snapshotted at creation, and is fixed for the life of the leaderboard.

Distinct from `get_standings(tags=...)`, which filters what you read back rather than what gets collected.

### Win/loss matrix

`leaderboard.get_win_loss_matrix(tags=None, use_weighted_scoring=None)` and `benchmark.get_win_loss_matrix(tags=None, participant_ids=None, leaderboard_ids=None, use_weighted_scoring=None)` return a square pandas DataFrame indexed by participant name on both axes. Cell `[i, j]` is how often row model `i` beat column model `j`; the diagonal is always 0.

- `tags=None` includes every matchup; `tags=[]` includes none.
- `use_weighted_scoring=True` weights each matchup by annotator reliability (`userScore`), so cells hold weighted float sums; `False` gives raw win counts; `None` uses the server-configured default.
- Both also accept the voter-demographic filters and `run_id` described below.

### Voter demographic filtering

Every benchmark and leaderboard read method that returns standings or a matrix accepts the same six optional voter-demographic filters plus `run_id`, restricting the result to votes cast by matching voters:

- **Benchmark:** `get_overall_standings`, `get_win_loss_matrix`, `get_demographics`, `get_standings_breakdown`.
- **Leaderboard:** `get_standings`, `get_win_loss_matrix`.

| Parameter | Type | Notes |
|-----------|------|-------|
| `country` | `list[str] \| None` | ISO-2 country codes; **observed** |
| `language` | `list[str] \| None` | Language codes; **observed** |
| `gender` | `list[Gender] \| None` | SDK `Gender` enum; **estimated** (inferred) |
| `age_bucket` | `list[AgeGroup] \| None` | SDK `AgeGroup` enum; **estimated** (inferred) |
| `occupation` | `list[str] \| None` | Occupation strings; **estimated** (inferred) |
| `run_id` | `str \| None` | Restrict to a single evaluation run |

```python
from rapidata import Gender, AgeGroup, BenchmarkDemographicDimension

# Standings from US/GB voters aged 18–29
overall = benchmark.get_overall_standings(
    country=["US", "GB"],
    age_bucket=[AgeGroup.BETWEEN_18_29],
)
```

`gender`/`age_bucket` enum values are converted to backend values internally.

### `benchmark.get_demographics(...)`

Returns the demographic composition of the benchmark's voters. Accepts `tags`, `leaderboard_ids`, and the six demographic filters plus `run_id` above. The DataFrame has one row per `(dimension, bucket)`:

| Column | Meaning |
|--------|---------|
| `dimension` | Which attribute the row describes (a `BenchmarkDemographicDimension` value) |
| `value` | The bucket within that dimension |
| `votes` | Raw vote count in the bucket |
| `share` | Fraction of the dimension's votes; shares within a dimension sum to 1 |

Every dimension includes an `"unknown"` bucket for votes whose attribute could not be determined.

### `benchmark.get_standings_breakdown(dimension, ...)`

Returns standings split by a demographic dimension of the voters. `dimension` (required, first positional arg) is a `BenchmarkDemographicDimension`; the method also accepts `tags`, `leaderboard_ids`, and the six demographic filters plus `run_id`. The DataFrame has one row per `(segment, model)`:

| Column | Meaning |
|--------|---------|
| `segment` | The voter segment within the chosen dimension (includes an `"unknown"` bucket) |
| `segment_votes` | Raw vote count for the segment |
| `name` | Model / participant name |
| `wins` | Wins for that model within the segment |
| `total_matches` | Matches the model took part in within the segment |
| `score` | Score rounded to 2 decimals, or `None` |

### `BenchmarkDemographicDimension`

Importable from the top-level `rapidata` package. Selects which voter attribute `get_standings_breakdown` splits on and identifies the `dimension` column of `get_demographics`. Members: `AGEBUCKET`, `GENDER`, `OCCUPATION`, `COUNTRY`, `LANGUAGE` (rendered as `AgeBucket`, `Gender`, `Occupation`, `Country`, `Language`).

```python
from rapidata import BenchmarkDemographicDimension
```

## Examples

### Model Benchmark (MRI)

```python
from rapidata import RapidataClient, Tag, VoteAggregation

client = RapidataClient()

benchmark = client.mri.create_new_benchmark(
    name="Text-to-Image Benchmark",
    identifiers=["mountain", "city", "wizard"],
    prompts=[
        "A serene mountain landscape",
        "A futuristic city at night",
        "A wise wizard portrait",
    ],
    # Each inner entry may mix Tag objects and bare strings; a bare string becomes
    # Tag(value, category=None).
    tags=[
        [Tag("outdoor", category="scene"), "nature"],
        [Tag("outdoor", category="scene"), "urban"],
        [Tag("portrait", category="subject")],
    ],
    # Per-prompt provenance: an Origin or a plain string (mapped to Origin(source)).
    origins=["coco", "coco", "wikiart"],
)

# Replace the tags of / set the origin on an already-registered prompt.
# A field left as None is not sent and stays unchanged.
benchmark.update_prompt("wizard", tags=["portrait", "fantasy"], origin="wikiart")

# tags is the values-only view (categories dropped, kept for backwards
# compatibility); structured_tags and origins keep the full objects. All three are
# aligned by index with benchmark.prompts.
print(benchmark.tags, benchmark.structured_tags, benchmark.origins)

# Every tag in the benchmark with the number of prompts carrying it, in one request
print(benchmark.get_tag_counts())

leaderboard = benchmark.create_leaderboard(
    name="Prompt Adherence (outdoor)",
    instruction="Which image matches the description better?",
    show_prompt=True,
    # Scope which benchmark prompts this leaderboard collects matchups for: a prompt
    # is used if it carries an included tag and no excluded one. excluded_tags always
    # wins, and a non-empty included_tags drops untagged prompts. Matching is on the
    # tag value only — categories are irrelevant. Applied when a run starts, and fixed
    # at creation: to re-scope, create a new leaderboard.
    included_tags=["outdoor"],
    excluded_tags=["nsfw"],
    # level_of_detail also accepts a positive integer response budget instead of a
    # named level ("debug" 20, "low" 2000, "medium" 4000, "high" 8000,
    # "very high" 16000).
    level_of_detail=5000,
    # How per-matchup annotator responses are aggregated into a matchup result:
    # MAJORITY_VOTE (default) collapses each matchup to one win (ties split 0.5/0.5)
    # so every matchup weighs the same; ALL_VOTES counts each response as its own
    # matchup, so heavily-answered matchups dominate the standings.
    vote_aggregation=VoteAggregation.ALL_VOTES,
)

print(leaderboard.included_tags, leaderboard.excluded_tags)  # copies; [] when unset
print(leaderboard.response_budget)  # 5000
print(leaderboard.level_of_detail)  # "custom" — a name only on an exact budget match
print(leaderboard.vote_aggregation)  # VoteAggregation.ALL_VOTES

# name, level_of_detail, min_responses_per_matchup, and vote_aggregation are
# read-only — assigning to them raises AttributeError. Change any of them through
# update(); only the arguments you pass change, and all go out in one request.
leaderboard.update(
    name="Prompt Adherence v2",
    level_of_detail="high",        # named level or a positive integer budget
    min_responses_per_matchup=5,   # must be an int >= 3
    vote_aggregation=VoteAggregation.MAJORITY_VOTE,
)

# Evaluate models (creates, uploads, and submits in one step)
benchmark.evaluate_model(
    name="DALL-E 3",
    media=["dalle_mountain.png", "dalle_city.png", "dalle_wizard.png"],
    prompts=["A serene mountain landscape", "A futuristic city at night", "A wise wizard portrait"],
)

benchmark.evaluate_model(
    name="Midjourney v6",
    media=["mj_mountain.png", "mj_city.png", "mj_wizard.png"],
    prompts=["A serene mountain landscape", "A futuristic city at night", "A wise wizard portrait"],
)

# Pricing is separate participant metadata: add the model first, then attach the
# vendor's list price (USD per unit) so it is plotted on the benchmark's
# "Score vs. cost" chart. Skip this if you don't know the price.
midjourney = next(p for p in benchmark.participants if p.name == "Midjourney v6")
midjourney.set_price(0.04, unit="image")   # "image" | "video_second" | "million_tokens"

# Leaderboard-level results
standings = leaderboard.get_standings()
print(standings)

# Benchmark-level aggregation across leaderboards
overall = benchmark.get_overall_standings()
matrix = benchmark.get_win_loss_matrix()
```

### Model Benchmark — Voter Demographics

Standings, win/loss matrices, and both demographic read methods accept the same
optional voter-demographic filters. `country` (ISO-2 codes), `language`, and
`occupation` take plain strings; `gender` takes the `Gender` enum and `age_bucket`
the `AgeGroup` enum. `run_id` restricts to a single evaluation run. `gender` /
`age_bucket` / `occupation` are estimated (inferred); `country` / `language` are
observed.

```python
from rapidata import RapidataClient, Gender, AgeGroup, BenchmarkDemographicDimension

client = RapidataClient()
benchmark = client.mri.get_benchmark_by_id("benchmark_id")

# Restrict any read to a demographic slice of the voters.
standings = benchmark.get_overall_standings(
    country=["US", "CA"],
    language=["en"],
    gender=[Gender.FEMALE],
    age_bucket=[AgeGroup.BETWEEN_18_29],
)
matrix = benchmark.get_win_loss_matrix(country=["US"])

# The same filters work on a single leaderboard's reads.
# lb.get_standings(country=["US"], occupation=["student"])
# lb.get_win_loss_matrix(gender=[Gender.MALE])

# Who voted: one row per (dimension, value) with vote counts and shares that sum
# to 1 within each dimension. Every dimension has an "unknown" bucket for votes
# whose attribute could not be determined.
demographics = benchmark.get_demographics()
print(demographics)  # columns: dimension, value, votes, share

# Standings split by one demographic dimension of the voters.
breakdown = benchmark.get_standings_breakdown(
    dimension=BenchmarkDemographicDimension.COUNTRY,
)
print(breakdown)  # columns: segment, segment_votes, name, wins, total_matches, score
```

### Model Benchmark — Staged Submission

```python
from rapidata import RapidataClient

client = RapidataClient()

benchmark = client.mri.get_benchmark_by_id("benchmark_id")

# Add models without submitting
benchmark.add_model(
    name="DALL-E 3",
    media=["dalle_mountain.png", "dalle_city.png", "dalle_wizard.png"],
    prompts=["A serene mountain landscape", "A futuristic city at night", "A wise wizard portrait"],
)

benchmark.add_model(
    name="Midjourney v6",
    media=["mj_mountain.png", "mj_city.png", "mj_wizard.png"],
    prompts=["A serene mountain landscape", "A futuristic city at night", "A wise wizard portrait"],
)

# Update participant metadata after adding: rename, or set / clear the list price
# (USD per unit). Pricing is never part of add_model / evaluate_model.
dalle = next(p for p in benchmark.participants if p.name == "DALL-E 3")
dalle.set_price(0.04, unit="image")
print(dalle.price, dalle.price_unit)  # 0.04 image
# dalle.clear_price()                 # -> None None; model leaves the cost chart

# Inspect participants before submitting
for p in benchmark.participants:
    print(p.name, p.status, p.price, p.price_unit)

# Optional advisory gate: require every prompt to be filled with at least N samples.
# Only the arguments you pass change; omitted ones keep their stored value.
# min_assets_per_prompt must be an int >= 2 (bool is rejected).
benchmark.update(min_assets_per_prompt=4)

# Submit all CREATED and SUBMITTABLE participants in a single batch request. They
# are evaluated symmetrically as one run — each model is compared against every other
# and against the benchmark's already-submitted field, rather than as separate
# per-participant runs.
#
# The gate is advisory, not a rejection: submission always completes and participants
# are marked SUBMITTED. If any submitted participant filled a prompt below the required
# samples-per-prompt, run() emits a single aggregated logger.warning listing each
# participant and its shortfall prompts, e.g. "DALL-E 3: 'mountain' (2/4)".
benchmark.run()
```

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
