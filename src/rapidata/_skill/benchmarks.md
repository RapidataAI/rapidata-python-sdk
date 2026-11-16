# Benchmarks (Model Ranking Insights): setup and leaderboards

> Part of the Rapidata agent skill: `python -m rapidata skill benchmarks`. The **Task design rules** and **Key Gotchas** in the main guide (`python -m rapidata skill`) apply to everything here.

To compare **two** image or video models once, a template is quicker: `python -m rapidata skill comparison`.

Compare and rank AI models on leaderboards. Supports images, videos, audio, and text. Participants, uploads and prompt metadata: `python -m rapidata skill benchmark-participants`. Standings, win/loss matrices and voter demographics: `python -m rapidata skill benchmark-results`.

## Create a benchmark, leaderboards and models

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
    min_responses_per_matchup=5,         # 5 or more; the SDK default of 3 is too low
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
```

```python
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
```

## Leaderboard configuration

```python
# Update leaderboard config live — every mutable setting goes through update();
# only the arguments passed change, all in one PATCH request.
leaderboard.update(
    name="Realism (Updated)",                        # non-empty str
    level_of_detail="very high",                     # Named level or a positive int response budget
    min_responses_per_matchup=7,                     # 5 or more; the SDK rejects < 3 and bool
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

## Responses per matchup (`min_responses_per_matchup`)

Set `min_responses_per_matchup` to **5 or more** on every leaderboard (task design rule 6 in the main guide). The SDK default of 3 is too low: one labeler who misreads the question decides a third of a matchup. The SDK only rejects values below 3. Pick `level_of_detail` so the budget covers it: one leaderboard needs at least models × (models − 1) / 2 × prompts × `min_responses_per_matchup` responses for one round of every pair on every prompt (3 models, 6 prompts, 5 per matchup = 90).

## Response budgets (`level_of_detail`)

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

## Updating a leaderboard (`leaderboard.update()`)

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
| `min_responses_per_matchup` | `int` and ≥ `3`; `bool` is explicitly rejected, else `ValueError`. Use 5 or more (task design rule 6) |
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

## Vote aggregation (`VoteAggregation`)

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
    min_responses_per_matchup=5,
    vote_aggregation=VoteAggregation.ALL_VOTES,
)
print(leaderboard.vote_aggregation)   # VoteAggregation.ALL_VOTES
```

## Prompt-tag scoping (`included_tags` / `excluded_tags`)

These restrict **which benchmark prompts the leaderboard collects matchups for**. A prompt is used when it carries at least one `included_tags` value and no `excluded_tags` value; `excluded_tags` always wins, and a non-empty `included_tags` drops untagged prompts. Matching is on the tag value only — the category is irrelevant. The filter is applied when a run starts, not snapshotted at creation, and is fixed for the life of the leaderboard.

Distinct from `get_standings(tags=...)`, which filters what you read back rather than what gets collected.

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
    min_responses_per_matchup=5,  # 5 or more; the SDK default of 3 is too low
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
    min_responses_per_matchup=5,   # 5 or more; the SDK rejects < 3
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
