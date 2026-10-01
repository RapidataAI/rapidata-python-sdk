# Rapidata SDK — Full API Reference

## Job Definition Parameters

The new job-definition API exposes **classification**, **comparison**, **locate**, **draw**, **select words**, **free text**, and **ranking** publicly.

### Common parameters (classification & comparison)

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | str | Job identifier (not shown to labelers) |
| `instruction` | str | Task description shown to labelers (max 250 characters — longer raises `ValueError`) |
| `datapoints` | list | Data to label (URLs or local paths) |
| `data_type` | `"media"` \| `"text"` | `"media"` (default, covers image/video/audio) or `"text"`. **Text assets are NOT translated** — labelers see them verbatim in their original language |
| `responses_per_datapoint` | int | Responses per item (default 10) |
| `contexts` | list[str] \| None | Text context per datapoint (max 400 characters each; contexts over the limit are always shortened against the instruction before upload — set `rapidata_config.upload.contextShortening = True` to shorten every context, or use `client.context` to shorten manually) |
| `media_contexts` | list[list[str]] \| None | Reference images per datapoint; each entry is a list of image URLs/paths (one inner list per datapoint) |
| `confidence_threshold` | float \| None | Confidence-based early stopping threshold (0-1); cannot combine with `quorum_threshold` |
| `quorum_threshold` | int \| None | Quorum-based early stopping: stop when this many responses agree; cannot combine with `confidence_threshold` |
| `settings` | `Sequence[RapidataSetting] \| None` | Display/behavior settings |
| `failure_tolerance` | float \| None | Fraction of datapoints (0.0–1.0) allowed to fail upload while the definition is still created; `None` falls back to `rapidata_config.upload.failureTolerance` (default `0.0` = strict). See Error Handling |
| `private_metadata` | `list[dict[str, str]] \| None` | Hidden metadata per datapoint |

### Instruction length

`instruction` is capped at 250 characters (`Workflow.MAX_INSTRUCTION_LENGTH`) for every job definition type and for every audience qualification example. Over-long values raise `ValueError: instruction is <n> characters; maximum is 250` at construction time.

### Classification-specific

| Parameter | Type | Description |
|-----------|------|-------------|
| `answer_options` | list[str] | Categories to choose from |

### Comparison-specific

| Parameter | Type | Description |
|-----------|------|-------------|
| `datapoints` | list[list[str]] | Pairs: `[["a1.jpg","b1.jpg"], ...]` |
| `a_b_names` | list[str] \| None | Custom labels for results, e.g. `["Model A","Model B"]` |

### Locate-specific

Locate has no job-specific parameters — only the core parameters apply. `data_type`, `answer_options`, `a_b_names`, `confidence_threshold`, and `quorum_threshold` are not available for locate jobs. `datapoints` is `list[str]` (one item per row).

```python
job_definition = client.job.create_locate_job_definition(
    name="Artifact Detection",
    instruction="Tap on any visual glitches or errors in the image.",
    datapoints=["image1.jpg", "image2.jpg"],
    responses_per_datapoint=35,
    contexts=["Optional context"],
    settings=[LocateMaxPointsSetting(5)],
)
```

For locate audience examples, use `audience.add_locate_example(instruction, datapoint, truths, context=None, media_context=None, explanation=None, settings=None)` where `truths` is a `list[Box]` (import `Box` from `rapidata`); coordinates are image ratios (0.0–1.0).

### Draw-specific

Draw has no job-specific parameters — only the core parameters apply. `data_type`, `answer_options`, `a_b_names`, `confidence_threshold`, and `quorum_threshold` are not available for draw jobs. `datapoints` is `list[str]`.

```python
job_definition = client.job.create_draw_job_definition(
    name="Object Marking",
    instruction="Color in all the blue books",
    datapoints=["image1.jpg", "image2.jpg"],
    responses_per_datapoint=35,
)
```

For draw audience examples, use `audience.add_draw_example(instruction, datapoint, truths, context=None, media_context=None, explanation=None, settings=None)` where `truths` is a `list[Box]` (import `Box` from `rapidata`); coordinates are image ratios (0.0–1.0).

### Select Words-specific

| Parameter | Type | Description |
|-----------|------|-------------|
| `sentences` | list[str] | One sentence per datapoint, split by spaces for labelers to select words from (must have same length as `datapoints`) |

`contexts`, `media_contexts`, `data_type`, `answer_options`, `a_b_names`, `confidence_threshold`, and `quorum_threshold` are not available for select words jobs.

```python
job_definition = client.job.create_select_words_job_definition(
    name="Prompt Alignment",
    instruction="Select the words that are not depicted in the image.",
    datapoints=["image1.jpg", "image2.jpg"],
    sentences=["A cat on a red couch [No_mistakes]", "A blue car in the rain [No_mistakes]"],
    responses_per_datapoint=15,
)
```

For select words audience examples, use `audience.add_select_words_example(instruction, datapoint, sentence, truths, required_precision=1, required_completeness=1, explanation=None, settings=None)` where `truths` is a `list[int]` of 0-based word indices to select. `required_precision` is the minimum share of selected words that must be correct, `required_completeness` the minimum share of correct words that must be selected (both default `1` = exact match).

### Free Text-specific

Free Text has no job-specific parameters — only the core parameters apply. `answer_options`, `a_b_names`, `confidence_threshold`, and `quorum_threshold` are not available. Note: free text answers cannot be graded against a ground truth; audiences cannot be trained with free text qualification examples.

```python
job_definition = client.job.create_free_text_job_definition(
    name="Prompt Collection",
    instruction="What would you like to ask an AI?",
    datapoints=["image1.jpg"],
    responses_per_datapoint=15,
)
```

### Ranking (`client.job.create_ranking_job_definition`)

| Parameter | Type | Description |
|-----------|------|-------------|
| `datapoints` | list[list[str]] | Groups: `[["img1","img2","img3"], ...]`; each inner list is one independent ranking set |
| `comparison_budget_per_ranking` | int | Total comparisons per ranking group |
| `responses_per_comparison` | int | Responses per individual comparison (default 1); replaces `responses_per_datapoint` for ranking |
| `random_comparisons_ratio` | float | Ratio of random vs targeted comparisons (0-1, default 0.5). Ignored for rankings of ≤10 datapoints (see below) |
| `data_type` | `"media"` \| `"text"` | Default `"media"` |
| `contexts` / `media_contexts` | list \| None | One entry per ranking group (not per datapoint) |

`responses_per_datapoint`, `answer_options`, `a_b_names`, `confidence_threshold`, `quorum_threshold`, and `private_metadata` are not available for ranking jobs.

**Matchup behavior by ranking size.** How a ranking group is compared depends on how many datapoints it holds:

- **More than 10 datapoints:** matched adaptively (Elo-style) within `comparison_budget_per_ranking`; `random_comparisons_ratio` applies as described above.
- **10 or fewer datapoints:** every unique pair is compared, with the budget spread evenly across pairs (the total is rounded down to a multiple of the pair count; every pair is compared at least once even if the budget is smaller than the pair count). `random_comparisons_ratio` does **not** apply in this case.

### Finding and updating job definitions and jobs

```python
job_def = client.job.get_job_definition_by_id("job_definition_id")
job_defs = client.job.find_job_definitions(name="", amount=10, page=1)
job = client.job.get_job_by_id("job_id")
jobs = client.job.find_jobs(name="", amount=10, page=1)

job_def.preview()          # open the labeler preview in the browser
job_def.update_dataset(    # replace the datapoints
    datapoints=[...], data_type="media", contexts=None, media_contexts=None,
    sentences=None,        # select-words definitions only
    private_metadata=None,
)
```

## Audiences

**Goal.** An audience selects a specific group of annotators for a **specific task**. You tailor the pool to that task two ways — by training it on **qualification examples** (tasks with a known-correct answer; only labelers who answer them correctly are recruited) and/or by attaching **recruitment filters** (country, language, demographics). The point is to get the *right* annotators onto *that* task.

A task-specific audience is meant for that task and its repeated or scheduled runs — **not** for reuse on a different, unrelated task. The qualification examples encode what "good" means for the original task; once the task changes they no longer describe the work, so reusing the audience silently loses the quality it was built for. Create a new audience per distinct task. (The `global` audience is the exception: it's the generic baseline pool for tasks that need no special qualification.)

**Three kinds:**

| Kind | How to get it | When to use |
|------|---------------|-------------|
| global | `client.audience.get_audience_by_id("global")` | Instant, baseline quality, no setup |
| curated | `client.audience.get_audience_by_id("aud_MU1GZYoESyO")` (alignment) | Pre-trained on a domain |
| custom | `client.audience.create_audience(name=...)` + `add_*_example(...)` | You need labelers qualified on *your* task |

**Lifecycle / management:**

```python
# Create / fetch / discover
audience = client.audience.create_audience(
    name="Expert Evaluators",
    filters=None,
    # target_accuracy=0.8,   # Optional: fraction of qualification tasks (0.0–1.0) a labeler must get right
    # min_tasks=12,          # Optional: qualification tasks before the accuracy verdict is trusted
    # max_tasks=30,          # Optional: cap on admission-trial tasks before a verdict is forced
)
audience = client.audience.get_audience_by_id("global")            # or "aud_..." / any audience id
audiences = client.audience.find_audiences(name="", amount=10, page=1)   # your audiences, newest first

# Train a custom audience (every truth must be human-reviewed):
audience.add_classification_example(instruction=..., answer_options=[...], datapoint=..., truth=[...])
audience.add_compare_example(instruction=..., datapoint=[...], truth=...)
audience.add_locate_example(instruction=..., datapoint=..., truths=[Box(...)])     # requires: from rapidata import Box
audience.add_draw_example(instruction=..., datapoint=..., truths=[Box(...)])
audience.add_select_words_example(instruction=..., datapoint=..., sentence=..., truths=[1])
df = audience.get_examples(amount=10, page=1)                       # inspect examples (DataFrame)

# Start recruiting — REQUIRED and EXPLICIT for a custom audience. Recruiting begins only when
# you call this, once >=3 examples are added and reviewed. Adding examples does NOT start it; an
# audience left un-recruited stays in `Created` and a job assigned to it can never get responses
# (get_results()/display_progress_bar() raise — see "Jobs on an audience that can never respond").
# Skip all of this and use get_audience_by_id("global") when you need no task-specific qualification.
audience.start_recruiting()                                         # returns self; calling again is a no-op.
                                                                    # A backend failure raises RapidataError — it is
                                                                    # not swallowed, so recruiting never starts silently.
metrics = audience.get_recruiting_metrics()                         # snapshot of the recruiting funnel

# Manage
audience.update_name("New Name")
audience.update_filters([CountryFilter(["US"]), LanguageFilter(["en"])])  # audience-supported filters only
filtered = audience.filter([CountryFilter(["US"])])                 # slim subset, reuses the pool (no re-recruiting);
                                                                    # a RapidataFilteredAudience only has assign_job / find_jobs
audience.delete()

# Use
job = audience.assign_job(job_def)                                  # start a job on the pool (after start_recruiting)
jobs = audience.find_jobs(name="", amount=10, page=1)              # jobs assigned to this audience
```

Note: free-text answers can't be graded against a ground truth, so there is no `add_free_text_example` — custom audiences cannot be trained for free-text tasks.

### Admission bar (`create_audience`)

Three optional parameters set how strict qualification is:

| Parameter | Type | Description |
|-----------|------|-------------|
| `target_accuracy` | float \| None | Fraction of qualification tasks (0.0–1.0) a labeler must answer correctly. Server default `0.75` |
| `min_tasks` | int \| None | Qualification tasks a labeler must complete before the accuracy verdict is trusted. Server default `10` |
| `max_tasks` | int \| None | Upper bound on admission-trial tasks before a verdict is forced. Default `None` (no cap) |

Supplying only one of the three is fine — the SDK fills the others in from the defaults (`0.75` / `10`). Passing none of them sends no graduation rule at all and lets the server default apply. Client-side `ValueError`s: `target_accuracy` outside `0.0..1.0`, `min_tasks < 1`, `max_tasks < min_tasks`.

### `RecruitingMetrics`

`audience.get_recruiting_metrics()` returns a frozen `RecruitingMetrics` dataclass (importable from the top-level `rapidata` package) — a snapshot of the recruiting funnel. All counts are zero for audiences that have not recruited anyone and for curated audiences.

| Field | Type | Meaning |
|-------|------|---------|
| `graduated` | int | Passed qualification, eligible to work now |
| `distilling` | int | Still going through qualification |
| `dropped` | int | Removed from the pool (score too low, limits hit, …) |
| `inactive` | int | Previously graduated/distilling, went quiet |

Buckets are mutually exclusive — each annotator is counted exactly once.

### Queueing jobs (`assign_job(..., run_after=...)`)

`assign_job` takes an optional `run_after` parameter that queues a job to start only
after an earlier job finishes, so a single audience never splits its annotators across
two jobs at the same time.

```python
def assign_job(
    self,
    job_definition: RapidataJobDefinition,
    run_after: RapidataJob | str | None = None,
) -> RapidataJob:
    ...
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_after` | `RapidataJob \| str \| None` | Job (or job id) the new job must wait for. `None` (default) starts the job right away |

When `run_after` is set, the new job is created immediately in the `Queued` state and
begins once the preceding job **completes or fails**. A `RapidataJob` contributes its
`.id`; a string is used directly as the job id. The value is sent to the API as the
`precedingJobId` field on the create-job request (`None` sends no preceding job).

```python
# Queue behind a returned job object
first = audience.assign_job(job_def)
second = audience.assign_job(other_job_def, run_after=first)

# Queue behind a job id (e.g. from an earlier session)
second = audience.assign_job(other_job_def, run_after="job_id")
```

Jobs can be chained further by pointing each new job at its predecessor.

### Warnings on `assign_job`

The job is always created, but three advisory warnings may be logged afterwards:

- the estimated cost exceeds the account balance — the warning gives the estimate, the balance and the shortfall; the job runs as far as the balance allows (see "Jobs under review or out of funds");
- the explicit-content-check skip requested via `rapidata_config.upload.checkForExplicitContent = False` was denied by the account (the check still runs);
- the audience has **no graduated annotators yet** — the warning names the audience, how many are still distilling, and the job, and points at adding examples + `start_recruiting()`, or at using the `"global"` audience. Only `RapidataAudience` emits this; filtered audiences reuse their base pool.

## Demographic Filters

All filters are importable from the top-level `rapidata` package.

```python
from rapidata import (
    CountryFilter, LanguageFilter, UserScoreFilter,
    AgeFilter, GenderFilter, DeviceFilter, CampaignFilter, CustomFilter,
    AgeGroup, Gender, DeviceType,
    NotFilter, OrFilter, AndFilter,
)

# --- Recruitment filters on an audience: CountryFilter and LanguageFilter
#     (plus the And/Or/Not combinators). UserScoreFilter/CampaignFilter/CustomFilter
#     raise NotImplementedError here; demographic/device targeting belongs on .filter() (below). ---
audience.update_filters([
    CountryFilter(country_codes=["US", "CA", "GB"]),                  # 2-letter ISO codes (uppercased)
    LanguageFilter(language_codes=["en", "fr"]),                      # 2-letter ISO language codes
])

# Combine filters with logic operators
combined = OrFilter([filter1, filter2])
audience.update_filters([NotFilter(combined)])

# Derive a filtered subset of a trained audience without re-onboarding labelers.
# Supported filters for .filter(): CountryFilter, LanguageFilter, AgeFilter,
# GenderFilter, DeviceFilter (plus And/Or/Not combinators). Multiple filters are ANDed.
filtered = base_audience.filter([
    CountryFilter(["US"]),
    LanguageFilter(["en"]),
    AgeFilter([AgeGroup.BETWEEN_18_29]),
])
job = filtered.assign_job(job_def)  # filtered is a RapidataFilteredAudience

# Combine filters with &, |, ~ operators
us_or_ca_not_fr = base_audience.filter([
    (CountryFilter(["US"]) | CountryFilter(["CA"])) & ~LanguageFilter(["fr"]),
])
```

### Filter signatures

| Filter | Signature | Works on audiences? |
|--------|-----------|---------------------|
| `CountryFilter` | `(country_codes: list[str])` | yes |
| `LanguageFilter` | `(language_codes: list[str])` | yes |
| `UserScoreFilter` | `(lower_bound: float = 0.0, upper_bound: float = 1.0, dimension: str \| None = None)` — bounds 0–1 | no (raises `NotImplementedError`) |
| `AgeFilter` | `(age_groups: list[AgeGroup])` | `.filter()` only |
| `GenderFilter` | `(genders: list[Gender])` | `.filter()` only |
| `DeviceFilter` | `(device_types: list[DeviceType])` | `.filter()` only |
| `CampaignFilter` | `(campaign_ids: list[str])` | no (raises `NotImplementedError`) |
| `CustomFilter` | `(identifier: str, values: list[str])` | no (raises `NotImplementedError`) |
| `NotFilter` | `(filter: RapidataFilter)` | both |
| `OrFilter` | `(filters: list[RapidataFilter])` | both |
| `AndFilter` | `(filters: list[RapidataFilter])` | both |

Note: use `CountryFilter`, `LanguageFilter`, and the `And`/`Or`/`Not` combinators as recruitment filters (`create_audience(filters=...)` / `audience.update_filters(...)`). Target by age, gender or device with `audience.filter(...)` (deriving a filtered audience from graduates) using `AgeFilter`, `GenderFilter`, and `DeviceFilter`. There is no `DemographicFilter` class. `AgeGroup` members: `UNDER_18`, `BETWEEN_18_29`, `BETWEEN_30_39`, `BETWEEN_40_49`, `BETWEEN_50_64`, `OVER_65`; `Gender`: `MALE`, `FEMALE`, `OTHER`; `DeviceType`: `UNKNOWN`, `PHONE`, `TABLET`. `UserScoreFilter`, `CampaignFilter`, and `CustomFilter` cannot be attached to audiences at all (they raise `NotImplementedError`).

## Results Format

### Classification Results

```json
{
  "info": { "type": "Classify", "version": "3.0.0" },
  "results": [
    {
      "identifier": "image1.jpg",
      "originalFileName": "image1.jpg",
      "assetUrl": "https://assets.rapidata.ai/<random-uuid>.jpg",
      "aggregatedResults": { "Cat": 15, "Dog": 8 },
      "aggregatedResultsRatios": { "Cat": 0.6522, "Dog": 0.3478 },
      "summedUserScores": { "Cat": 9.5, "Dog": 4.2 },
      "summedUserScoresRatios": { "Cat": 0.6934, "Dog": 0.3066 },
      "confidencePerCategory": { "Cat": 0.989, "Dog": 0.011 },
      "detailedResults": [
        { "selectedCategory": "Cat", "userDetails": { "country": "US", "language": "en", "userScores": { "global": 0.75 } } }
      ]
    }
  ],
  "summary": { "Cat": 15, "Dog": 8 }
}
```

`identifier` is the source URL, the original file name, or the text of the datapoint; `summary` is the category counts summed over all datapoints. `confidencePerCategory` appears only with `confidence_threshold`.

### Comparison Results

```json
{
  "info": { "type": "Compare", "name": "Image Comparison", "instruction": "Which image is higher quality?", "version": "4.1.0" },
  "results": [
    {
      "context": "A small blue book...",
      "winner": "model_b.jpg",
      "winnerIndex": 1,
      "weightedWinner": "model_b.jpg",
      "weightedWinnerIndex": 1,
      "winner_index": 1,
      "assetUrls": {
        "model_a.jpg": "https://assets.rapidata.ai/<random-uuid>.jpg",
        "model_b.jpg": "https://assets.rapidata.ai/<random-uuid>.jpg"
      },
      "aggregatedResults": { "model_a.jpg": 3, "model_b.jpg": 5 },
      "aggregatedResultsRatios": { "model_a.jpg": 0.375, "model_b.jpg": 0.625 },
      "summedUserScores": { "model_a.jpg": 1.0, "model_b.jpg": 2.5 },
      "summedUserScoresRatios": { "model_a.jpg": 0.286, "model_b.jpg": 0.714 },
      "detailedResults": [
        {
          "votedFor": "model_b.jpg",
          "userDetails": {
            "country": "US", "language": "en",
            "userScores": { "global": 0.75 },
            "demographics": { "age": "25-34", "gender": "Female" }
          }
        }
      ]
    }
  ],
  "summary": { "A_wins_total": 5, "B_wins_total": 3 }
}
```

### Key Result Fields

| Field | Meaning |
|-------|---------|
| `info.type` / `info.name` / `info.instruction` | Task type (e.g. `Compare`, `Classify`), the job name, and the instruction shown to labelers |
| `assetUrls` | Maps each option to the Rapidata-hosted URL of the exact file shown to labelers (random-UUID filenames; not encrypted) |
| `winner` | Most-voted option by raw vote count (`argmax` of `aggregatedResults`); `null` when nothing was voted or the top count is tied |
| `winnerIndex` | Position of `winner` in the ordered option list (`0` = first asset, `1` = second; `Both`/`Neither` appear as trailing indexes when voted); `null` under the same conditions as `winner` |
| `weightedWinner` / `weightedWinnerIndex` | Reliability-weighted winner (`argmax` of `summedUserScores`) and its index, same index space and `null`-on-tie behavior. Can differ from `winner` on close votes |
| `winner_index` | **Deprecated** alias of `winnerIndex`, kept for backwards compatibility; will be removed in a future release |
| `aggregatedResults` | Raw vote counts |
| `aggregatedResultsRatios` | Vote percentages |
| `summedUserScores` | Per-option sum of each choosing labeler's aggregated `userScore` |
| `summedUserScoresRatios` | `summedUserScores` normalized to sum to 1 |
| `confidencePerCategory` | Confidence level per category (with early stopping) |
| `userScore` | 0-1 value indicating individual labeler reliability |

A labeler's `demographics` may be empty when no demographic data was collected for them.

`winnerIndex`, `weightedWinner` and `weightedWinnerIndex` are only emitted by aggregator version `4.1.0`+ (`info.version`); results produced by older versions carry only `winner` and `winner_index`.

### Working with Results

```python
results = job.get_results()              # RapidataResults — a dict subclass holding the raw JSON
snapshot = job.get_results(preliminary_results=True)  # unfinished job: responses so far, no waiting
df = results.to_pandas()                  # one row per datapoint; compare results get A_/B_ columns
df = results.to_pandas(split_details=True)  # one row per individual response
results.to_json("results.json")           # writes the file (default "./results.json"); returns None
```

Flow items have a different result shape — see the Flows section.

## Early Stopping

Two mutually exclusive strategies are available for Classification and Comparison jobs. You cannot set both on the same job.

### Confidence Stopping

Stop collecting responses once a statistical confidence threshold (weighted by labeler trust scores) is reached.

```python
job_def = client.job.create_classification_job_definition(
    name="Animal Classification",
    instruction="What animal is in this image?",
    answer_options=["Cat", "Dog"],
    datapoints=["pet1.jpg", "pet2.jpg"],
    responses_per_datapoint=50,   # Maximum
    confidence_threshold=0.99,    # Stop at 99% confidence
)
```

- System calculates confidence using labeler userScores
- Stops when target confidence is reached
- Saves cost by collecting fewer responses when consensus is clear
- Best for unambiguous tasks with clear correct answers
- Not recommended for subjective preference tasks

### Quorum Stopping

Stop collecting responses once a fixed number of responses agree on the same answer.

```python
job_def = client.job.create_classification_job_definition(
    name="Animal Classification",
    instruction="What animal is in this image?",
    answer_options=["Cat", "Dog"],
    datapoints=["pet1.jpg", "pet2.jpg"],
    responses_per_datapoint=10,   # Maximum
    quorum_threshold=7,           # Stop when 7 responses agree
)
```

A datapoint stops when:
1. `quorum_threshold` responses agree on the same answer, **OR**
2. Quorum becomes mathematically impossible (e.g. votes are too split to reach the threshold), **OR**
3. `responses_per_datapoint` total votes are collected

- Simpler than confidence stopping — based on raw vote counts, not statistics
- Good when you want predictable cost bounds with early termination
- Best for unambiguous tasks with a clear correct answer

## Job Progress

`job.get_progress()` returns a frozen `JobProgress` dataclass immediately — it never blocks, unlike `get_results()` / `display_progress_bar()`. `JobProgress` is importable from the top-level `rapidata` package.

| Field | Type | Description |
|-------|------|-------------|
| `state` | str | Same value as `job.get_status()` |
| `completion_percentage` | float | 0–100 |
| `recruiting` | `RecruitingMetrics \| None` | Recruiting funnel of the job's audience; `None` for curated audiences |

```python
progress = job.get_progress()
print(f"{progress.state}: {progress.completion_percentage:.1f}% done")
if progress.recruiting:
    print(progress.recruiting.graduated, progress.recruiting.distilling)
```

## Cost Estimates

Both `RapidataJobDefinition` and `RapidataJob` expose an `estimated_cost` property returning a `CostEstimate` — an approximate estimate of what the job will cost to run to completion. Reading it from a job definition lets you check the cost of a run **before** assigning it to an audience. `CostEstimate` is importable from the top-level `rapidata` package.

The estimate is priced shortly after the definition/job is created, so the first read blocks briefly while polling until the estimate is available (raising `TimeoutError` if it is still not ready after a few minutes), then caches the result.

```python
job_def = client.job.create_compare_job_definition(
    name="Example Image Prompt Alignment",
    instruction="Which image matches the description better?",
    datapoints=[["midjourney.jpg", "flux.jpg"]],
    contexts=["A small blue book sitting on a large red book."],
)

estimate = job_def.estimated_cost   # blocks briefly until priced
print(f"About {estimate.estimated_cost} for {estimate.required_responses} responses")

# The same property is available once the job is running
job = audience.assign_job(job_def)
print(job.estimated_cost.estimated_cost)
```

### `CostEstimate` fields

| Field | Type | Description |
|-------|------|-------------|
| `estimated_cost` | float | Estimated total cost of running the job to completion, in your account's billing currency |
| `datapoint_count` | int | Number of datapoints the job will label |
| `required_responses` | int | Total number of responses the job collects to complete |

This is an **estimate, not the final bill**: it is based on a sample of the job's tasks scaled to the number of responses requested, so the amount actually charged can differ. Early stopping can also lower the final cost by collecting fewer responses than the maximum.

## Billing

`client.billing` (a `RapidataBillingManager`, created during client construction) reads how much the current billing period has cost so far and how much credit is left. Billing is settled per **organization**, so its figures cover everything the organization spent — not only the jobs this client created.

```python
period = client.billing.get_current_billing_period()   # BillingPeriod
print(f"${period.outstanding_cost} accrued over {period.response_count} responses")
```

### `client.billing.get_current_billing_period() → BillingPeriod`

Returns the billing period currently accruing cost. Raises `RapidataError` with status `404` if the organization has no active billing period (a period only opens once there is something to bill).

### `client.billing.get_outstanding_balance() → float`

Returns the total the organization currently owes, in US dollars rounded to the cent (`0.0` when nothing is owed). Covers finalized-but-unpaid invoices plus the settled cost of ended periods not yet invoiced; it does **not** include the current, still-accruing period. The figure is already net of vouchers and discounts, and is settled per organization.

```python
owed = client.billing.get_outstanding_balance()   # e.g. 42.50
print(f"${owed} outstanding")
```

### `BillingPeriod` fields

A frozen dataclass. All amounts are in **US dollars**, rounded to the cent. Values are a snapshot — fetch again for an up-to-date figure. `BillingPeriod` (and `RapidataBillingManager`) are importable from the top-level `rapidata` package (and re-exported from `rapidata.rapidata_client`).

```python
from rapidata import BillingPeriod, RapidataBillingManager
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | The billing period's id |
| `start_date` / `end_date` | datetime | When the period starts and ends |
| `status` | str | Lifecycle status: `"Open"` while still accruing cost; otherwise one of `"Invoiced"`, `"Void"`, `"Reconciling"`, `"PendingReview"`, `"Closed"` |
| `outstanding_cost` | float | Net cost accrued so far (`gross_cost` minus `discount`) — what the period would be invoiced for today |
| `gross_cost` | float | Cost accrued so far, before discounts |
| `discount` | float | Discounts applied to the period so far |
| `response_count` | int | Number of billable responses collected in the period |
| `credits` | `float \| None` | Prepaid credit still available, or `None` when the organization is billed for usage rather than from a prepaid balance. An organization-level balance that carries across periods |
| `effective_limit` | `float \| None` | The most the organization may spend this period, or `None` when it spends without a cap. On a prepaid plan this is the total credit granted, and `credits` is what remains of it |

## Settings Reference

All settings inherit from `RapidataSetting` and are importable from `rapidata`.

Most settings only apply to specific task types. If you add a setting that the job's task type does not support, the SDK logs a non-fatal warning and still sends the flag — it is never dropped and no error is raised. Ranking jobs are treated as Compare for this check.

| Class | Constructor | Effect |
|-------|-------------|--------|
| `NoShuffleSetting` | `(value: bool = True)` | Disable shuffling of answer options (Likert scales) |
| `AllowNeitherBothSetting` | `(delay_ms: int = 5000)` — ≥ 0 | Comparison: show an "Unsure" button (answers "Neither" / "Both") after `delay_ms` milliseconds |
| `MarkdownSetting` | `(value: bool = True)` | Render markdown in text |
| `MuteVideoSetting` | `(value: bool = True)` | Start videos muted |
| `FreeTextMinimumCharactersSetting` | `(value: int)` — must be ≥ 1 (prints a warning above 40) | Min chars for free-text tasks. Use with caution — see note below the table |
| `FreeTextMaxCharactersSetting` | `(value: int = 1024)` — must be ≥ 1 | Max chars for free-text tasks. Use with caution — see note below the table |
| `SwapContextInstructionSetting` | `(value: bool = True)` | Swap positions of context and instruction |
| `PlayPercentageVideoSetting` | `(percentage: int = 95)` — 0–95 | Require labelers to watch N% of video |
| `OriginalLanguageOnlySetting` | `(value: bool = True)` | Skip translation; show task in original language. Text assets (`data_type="text"`) are never translated, with or without this setting |
| `NoMistakeOptionSetting` | `(value: bool = True)` | Hide the "mark as mistake" option |
| `DisableAutoloopSetting` | `(value: bool = True)` | Disable automatic media looping |
| `NoInstructionDisplaySetting` | `(value: bool = True)` | Hide instruction from task screen |
| `KeyboardNumericSetting` | `(value: bool = True)` | Open numeric keyboard on mobile |
| `LocateMaxPointsSetting` | `(value: int = 3)` — ≥ 1 | Locate tasks: max points per labeler |
| `LocateMinPointsSetting` | `(value: int = 1)` — ≥ 1 | Locate tasks: min points per labeler |
| `ComparePanoramaSetting` | `(value: bool = True)` | Render comparison media as 360° panorama |
| `CompareEquirectangularSetting` | `(value: bool = True)` | Render comparison media as equirectangular VR |
| `ClassifyEquirectangularSetting` | `(value: bool = True)` | Render classification media as equirectangular 360° view |
| `CustomSetting` | `(key: str, value: str, target: "rapids" \| "campaign" = "rapids")` | Pass a custom key/value through to the backend; `target` controls whether the flag is applied at the rapid level (`"rapids"`) or campaign level (`"campaign"`) |

**Note on `FreeTextMinimumCharactersSetting` / `FreeTextMaxCharactersSetting`:** use these with caution. Free-text responses already pass through a reasonableness check by default, so tightening the bounds is usually unnecessary and will reject otherwise valid answers. Only set them when the question genuinely demands a specific length (e.g. a single word, or a full paragraph).

## Error Handling

### FailedUploadException

Job-definition creation is **atomic**: the remote definition is persisted only once the datapoint upload lands within the failure tolerance. If too many datapoints fail, **no job definition is created** and `e.job_definition` is `None` — recover with `e.retry()`, which re-uploads only the failed datapoints into the *same* dataset (never a new one) and finishes creating the definition.

```python
from rapidata import FailedUploadException

try:
    job_def = client.job.create_classification_job_definition(
        name="My Job",
        instruction="...",
        answer_options=[...],
        datapoints=["valid.jpg", "missing.jpg", "valid2.jpg"],
        failure_tolerance=0.01,          # Fraction allowed to fail (default 0.0 = strict)
    )
except FailedUploadException as e:
    print(f"Failed: {len(e.failed_uploads)}")
    for reason, dps in e.failures_by_reason.items():
        print(f"  {reason}: {len(dps)} datapoints")
    for stage, dps in e.failures_by_stage.items():
        print(f"  stage {stage}: {len(dps)} datapoints")
    for fu in e.detailed_failures:
        print(fu.item, fu.stage, fu.http_status, fu.error_message, fu.error_type)
    # ...fix the failing datapoints...
    job_def = e.retry()                  # Raises FailedUploadException again if failures remain — loopable
```

Tolerance behaviour:

- Within tolerance but with some failures: the definition **is** created and a warning reports `n/total` failed and the tolerance in effect.
- Outside tolerance: nothing is created; `job_definition` is `None`.
- Regardless of tolerance, at least one datapoint must upload successfully — a definition over an empty dataset is never created.
- The failure ratio is always measured against the **original** datapoint count, so it stays meaningful across `retry()` calls.

**Properties:** `failed_uploads` (list[Datapoint]), `detailed_failures` (list[FailedUpload[Datapoint]]), `failures_by_reason` (dict[str, list[Datapoint]]), `failures_by_stage` (dict[str, list[Datapoint]] — grouped by remote-URL ingestion stage; failures without a stage, e.g. local files, are omitted, so this can be empty), `job_definition`, `dataset`, `machine` (the creation state machine backing `retry()`).

**`retry()`** raises `RuntimeError` when the exception did not come from job-definition creation — for those, use `dataset.add_datapoints(exception.failed_uploads)` instead.

The exception message annotates each item with `stage=…`, `http_status=…` and `trace_id=…`, appends a `Too many open files` hint (naming `ulimit -n`, `RAPIDATA_cacheShards`, `RAPIDATA_maxWorkers`) when a failure looks like file-descriptor exhaustion, and points at `exception.retry()` whenever a creation machine is attached.

### `FailedUpload` fields

| Field | Type | Description |
|-------|------|-------------|
| `item` | Datapoint \| SampleUpload | The item that failed. A `Datapoint` for job uploads; a `SampleUpload` (media/identifier pair) for benchmark participant uploads (`upload_media` / `retry_missing`) |
| `error_message` / `error_type` | str | Failure reason and exception type |
| `stage` | `str \| None` | Remote-URL ingestion stage: `"download"`, `"redirect"`, `"content_type"`, `"decode"`, `"timeout"`, `"size"`, `"validation"`, `"internal"`. `None` for local-file and datapoint-creation failures |
| `http_status` | `int \| None` | Origin server's HTTP status, e.g. `403` |
| `trace_id` | `str \| None` | Backend trace id for the failure, taken from the `RapidataError` (the `x-trace-id` response header, falling back to the `traceId` in the problem+json body) |

Only `internal` is a Rapidata-side fault — every other stage is caller-actionable. `format_error_details()` emits `Stage:` and `HTTP Status:` lines when these are present. Datapoint-level asset failures only propagate `stage` / `http_status` when all blocking asset failures agree on a single value; otherwise both are `None`.

### `AssetWarning`

Non-fatal advisories the backend attaches to **successful** uploads (e.g. a video longer than annotators can solve). Importable from `rapidata.rapidata_client.exceptions`.

```python
@dataclass(frozen=True)
class AssetWarning(Generic[T]):
    item: T        # the asset (file path or URL)
    message: str   # backend advisory text, surfaced verbatim
```

Collected from both single-asset and batch upload paths, de-duplicated on `(item, message)`, and logged once at the end of an upload as `Upload warning for '<item>': <message>`. They never fail the upload.

**Recovery docs:** https://docs.rapidata.ai/error_handling/

### Jobs under review or out of funds

`assign_job` never blocks on funds: the job is always created. If its estimated cost exceeds your account balance, `assign_job` logs a warning with the estimate, your balance, and the expected shortfall — the job still runs, but may pause partway until you top up.

Some jobs don't go straight to running. A job can enter manual review (`ManualApproval`) or, once out of funds mid-run, become spend-limited (`SpendLimited`); a job you paused with `job.pause()` sits in `Paused`. None of these completes on its own, so `get_results()` raises an informative error naming the state (and the review reason, when available) instead of blocking indefinitely — top up, wait for a reviewer or call `job.resume()`, then call it again.

### Jobs on an audience that can never respond

`get_results()` and `display_progress_bar()` also raise up front when the job's audience can never produce responses — nobody graduated **and** nobody is being recruited (recruiting was never started, or the audience is `Ready` with an empty pool). This catches the case where `start_recruiting()` was forgotten, instead of blocking forever at 0 responses.

An audience that is still distilling, an audience in `Pending`/`Recruiting`, a curated audience, or a failed metrics read do **not** raise — those can still deliver responses.

## Flows (Continuous Response Collection)

Flows continuously collect human responses in small batches without full job/audience setup. Two flow types exist: **ranking flows** (`create_ranking_flow`) and **classify flows** (`create_classify_flow`), backed by two concrete subclasses of the shared base `RapidataFlow`:

```python
from rapidata import RapidataFlow, RapidataRankingFlow, RapidataClassifyFlow
```

- `RapidataFlow` — shared base class; holds only the shared listing/deletion behavior (`get_flow_items`, `delete`). It does **not** expose `create_new_flow_batch` or `update_config`.
- `RapidataRankingFlow` — concrete ranking flow; adds `create_new_flow_batch` (batch-level shared context) and `update_config` (instruction, thresholds, starting Elo, drain duration, serve timeout).
- `RapidataClassifyFlow` — concrete classify flow; adds `create_new_flow_batch` (per-datapoint context) and `update_config` (drain duration only).

Each flow and `RapidataFlowItem` carries a `flow_type` (`"ranking"` or `"simple"` — classify flows are `"simple"`, since they run on the backend's simple-flow routes), which determines the result shape and which methods are available. `get_flow_by_id` and `find_flows` populate the type from the API and return the matching subclass. Because `create_ranking_flow` → `RapidataRankingFlow`, `create_classify_flow` → `RapidataClassifyFlow`, and `get_flow_by_id` / `find_flows` return `RapidataRankingFlow | RapidataClassifyFlow`, narrow a retrieved flow (e.g. `isinstance(flow, RapidataClassifyFlow)`) before passing kind-specific batch arguments.

### Ranking Flows

Lightweight continuous ranking:

```python
# Create flow
flow = client.flow.create_ranking_flow(
    name="Image Quality Ranking",
    instruction="Which image looks better?",
    max_response_threshold=100,       # Target responses per flow item (default 100)
    min_response_threshold=50,        # Minimum acceptable responses; item is Incomplete if TTL expires below this
    # validation_set_id="...",        # Optional: validation-set id to interleave validation rapids
    # settings=[...],                 # Optional: flow-wide RapidataSettings
    # drain_duration=30,              # Optional: drain duration in seconds (sent as drainDurationSeconds)
    # serve_timeout=60,               # Optional: serve timeout in seconds (sent as serveTimeoutSeconds)
)

# Add items to rank (RapidataRankingFlow.create_new_flow_batch — batch-level shared context)
flow_item = flow.create_new_flow_batch(
    datapoints=["img1.jpg", "img2.jpg", "img3.jpg"],
    context="Generated by Model X",   # Optional: batch-level text context shared by all comparisons
    context_assets=["reference.jpg"], # Optional: 1–10 image/video/audio paths/URLs shown alongside instruction
    data_type="media",                # "media" (default) or "text"
    private_metadata=[...],           # Optional
    accept_failed_uploads=False,      # If True, proceed even if some uploads fail
    time_to_live=300,                 # Seconds until expiry (up to 3600; defaults to 4 minutes for ranking flows).
                                      #   Client-side check is 10–3600 (else ValueError("Time to live must be
                                      #   between 10 seconds and 1 hour.")); with default flow settings the minimum is 60
)
# context (singular) and context_assets are the shared, batch-level context for all comparisons.
# Ranking batches take no per-datapoint `contexts` (TypeError: unexpected keyword argument).

# Get results — ranking flow items return FlowItemResult, NOT RapidataResults
result = flow_item.get_results()      # Blocks until completed/failed/stopped/incomplete
# result.datapoints: dict[str, int]   # asset → Bradley-Terry strength estimate on Elo-scale (default start 1200);
#                                     # keyed by source URL when provided, otherwise by original filename
# result.total_votes: int             # total pairwise comparisons collected across all items

# Items sorted from best to worst
ranked = sorted(result.datapoints.items(), key=lambda item: item[1], reverse=True)

status = flow_item.get_status()       # Non-blocking check; one of Pending, Running, Completed,
                                      #   Failed, Stopping, Stopped, Incomplete
matrix = flow_item.get_win_loss_matrix()  # Pandas DataFrame (blocks until completed). Ranking flow items only —
                                          #   raises ValueError on a classify flow item
count = flow_item.get_response_count()    # responses collected (waits for completion)

# Query flow items (returned newest first; defaults: 10 per page, page 1)
items = flow.get_flow_items(amount=10, page=1)

# Update a ranking flow after creation. Every argument is optional; drain_duration and
#   serve_timeout (seconds) are sent only when not None, so omitting them keeps the current values
flow.update_config(
    instruction="New instruction",
    starting_elo=1000,
    min_responses=40,
    max_responses=120,
    drain_duration=30,
    serve_timeout=60,
)

# Preheat for low-latency responses (call ~5 minutes before time-sensitive batches)
client.flow.preheat()

# Manage flows
all_flows = client.flow.find_flows(name="", amount=10, page=1)
flow = client.flow.get_flow_by_id("flow_id")
flow.delete()

# Pause / resume a job (both return the job)
job.pause()
job.resume()

# Delete other resources
job_def.delete()   # Deletes the job definition and all its revisions
job.delete()       # Deletes a running job
audience.delete()  # Deletes the audience
```

(`preheat()`, `find_flows`, `get_flow_by_id` and `delete()` apply to both flow types.)

### Classify Flows

Continuously sort each datapoint of every flow item into one of the flow's categories:

```python
flow = client.flow.create_classify_flow(
    name="Text Detection",
    instruction="Does this image contain text?",   # question shown with every datapoint
    categories=[("Yes, clearly readable", "yes"), ("No", "no")],  # 2–8 options; a plain str is shown and
                                                                  #   returned as-is, a (label, value) tuple
                                                                  #   shows label but returns value
    max_responses_per_datapoint=15,     # default 15; accepted responses that close an image — collection for
                                        #   that image stops once reached
    min_responses_per_datapoint=10,     # default 10, must be >= 1; average responses per image an item needs
                                        #   (once it ends by its time to live) to be Completed rather than Incomplete.
                                        #   max_responses_per_datapoint must be >= min_responses_per_datapoint
    # validation_set_id="...",          # Optional: validation-set id
    # settings=[...],                   # Optional: flow-wide RapidataSettings
    # drain_duration=30,                # Optional: drain duration in seconds (sent as drainDurationSeconds)
    # serve_timeout=60,                 # Optional: serve timeout in seconds (sent as serveTimeoutSeconds)
)
# Time-to-live is controlled per batch only — set it on each create_new_flow_batch call (below).

# Add a batch — one flow item classifying each of its datapoints into a category
# (RapidataClassifyFlow.create_new_flow_batch — per-datapoint context)
flow_item = flow.create_new_flow_batch(
    datapoints=["img1.jpg", "img2.jpg"],
    contexts=["Per-datapoint text", "..."],                    # Optional: one entry per datapoint (len must match)
    context_assets=[["ref1.jpg"], ["ref2a.jpg", "ref2b.jpg"]], # Optional: one list of asset paths/URLs per datapoint
                                                               #   (each entry is a list even for a single asset; len must match)
    data_type="media",                                         # "media" (default) or "text"
    private_metadata=[...],                                    # Optional
    accept_failed_uploads=False,                               # If True, proceed even if some uploads fail
    time_to_live=300,                                          # Seconds until expiry (up to 3600; defaults to 4 minutes;
                                                               #   client-side check 10–3600; with default flow settings the minimum is 60)
)
# Classify batches take no batch-level `context` (singular) and no `media_contexts` (TypeError).
# Validation: `contexts` must be a list of strings matching the datapoint count
#   (else ValueError); `context_assets` must be a list of lists of strings
#   (else ValueError("Context assets must be a list of lists of strings.")) with matching length
#   (else ValueError("Number of context assets entries must match number of datapoints.")).

# Get results — classify flow items return ClassifyFlowItemResult
result = flow_item.get_results()      # Blocks until terminal state
# result.datapoints: dict[str, ClassifyDatapointResult]  # asset identifier → outcome; keyed by source URL
#                                     # when available, else original filename
# result.total_responses: int

for key, dp in result.datapoints.items():
    print(key, dp.majority_value, dp.distribution, dp.response_count)

# Update the drain duration (seconds) after creation — the only updatable classify setting.
#   drain_duration=None (the default) is not sent, so the current value stays.
flow.update_config(drain_duration=30)
```

Validation performed before any API call: 2–8 categories (else `ValueError("Categories must contain between 2 and 8 entries.")`), unique category values, `min_responses_per_datapoint >= 1` (else `ValueError("Min responses per datapoint must be at least 1.")`), and `max_responses_per_datapoint >= min_responses_per_datapoint` (else `ValueError("Max responses per datapoint must be at least min responses per datapoint.")`). Time-to-live is set per batch on `create_new_flow_batch`, not on the flow.

`get_win_loss_matrix()` is ranking-only; calling it on a classify flow item raises `ValueError`. `update_config()` on `RapidataClassifyFlow` accepts only `drain_duration`; the instruction, categories and response thresholds can't be changed after creation. `get_response_count()` works on both — for classify flow items it returns `total_responses`.

A classify batch becomes `Incomplete` when its `time_to_live` expires with total responses below `min_responses_per_datapoint × number of images` (an average per image); otherwise it is `Completed` — including when every image already reached `max_responses_per_datapoint`. (For ranking flows, `Incomplete` instead occurs when `time_to_live` expires with fewer than `min_response_threshold` responses.)

**Classify result classes** — both are frozen dataclasses importable from the top-level `rapidata` package (alongside `FlowItemResult`):

```python
from rapidata import FlowItemResult, ClassifyFlowItemResult, ClassifyDatapointResult
```

`ClassifyDatapointResult` — classification outcome of a single datapoint:

| Field | Type | Meaning |
|-------|------|---------|
| `majority_value` | `str \| None` | Category value chosen most often, or `None` on a tie |
| `distribution` | `dict[str, int]` | Category value → number of responses that chose it. Includes **every** category value defined in the flow, in the flow's category order, with `0` for categories nobody chose (e.g. `{"yes": 0, "no": 5}`); any unexpected backend values not in the blueprint are appended after the blueprint categories. Computing results makes an extra API call to fetch the flow blueprint's categories |
| `response_count` | int | Responses collected for this datapoint |

`ClassifyFlowItemResult` — result of a classify flow item:

| Field | Type | Meaning |
|-------|------|---------|
| `datapoints` | `dict[str, ClassifyDatapointResult]` | Asset identifier → outcome |
| `total_responses` | int | Total responses collected across the item |

## Model Ranking Insights (MRI / Benchmarks)

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
    # skip_initial_run=False,            # Optional: when True, skip the initial run that evaluates the models already in the benchmark against each other (start with no responses/standings; later models still compare against the whole field). Create-only — not readable back
)

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

participant.disable()             # Exclude from evaluation and standings (reversible)
participant.enable()              # Re-enable a previously disabled participant
participant.get_elo()             # Aggregated Elo across all leaderboards (None if not yet computed)
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

## Signals (Scheduled Labeling)

A signal runs a job definition against an audience on a repeating schedule. Each firing creates one `RapidataJob`.

### `client.signals.create_signal`

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | str | Human-readable name for the signal |
| `audience` | `RapidataAudience` \| str | Audience (or id string) the spawned jobs will target |
| `job_definition` | `RapidataJobDefinition` \| str | Job definition (or id string) each firing creates a job from |
| `interval_hours` | float | Hours between consecutive firings; must be positive (`ValueError` otherwise) |
| `description` | str \| None | Optional description |
| `revision_number` | int \| None | Optional: pin a specific job-definition revision; omit for "latest at fire time" |
| `is_public` | bool | Default `False`. If `True`, the signal is readable by every authenticated user in your org |

```python
signal = client.signals.create_signal(
    name="Daily prompt alignment",
    audience=audience,           # RapidataAudience or id string
    job_definition=job_def,      # RapidataJobDefinition or id string
    interval_hours=24,
    # revision_number=2,         # Optional: pin a revision
    # is_public=True,            # Optional: org-wide visibility
)
```

### Signal methods

| Method | Description |
|--------|-------------|
| `signal.get_jobs(page=1, page_size=20, sort_descending=True)` | List `RapidataJob` objects created by this signal (newest first by default) |
| `signal.trigger()` | Fire one job immediately; returns right away — job created asynchronously |
| `signal.wait_for_next_job(timeout=300, poll_interval=5.0)` | Block until the next firing creates its job and return it |
| `signal.pause()` | Pause the scheduler (manual `trigger()` calls still fire); returns the signal |
| `signal.resume()` | Resume a paused signal; returns the signal |
| `signal.update(name=..., description=..., interval_hours=...)` | Keyword-only; update any of name, description, cadence; returns the signal |
| `signal.delete()` | Delete the signal and all its runs |

### Signal manager methods

| Method | Description |
|--------|-------------|
| `client.signals.get_signal_by_id("signal_id")` | Look up a signal by id |
| `client.signals.find_signals(name="", amount=10, page=1)` | Find signals by name |

### Signal properties

| Property | Description |
|----------|-------------|
| `id` | Unique signal id |
| `name` / `description` | Display name and optional description |
| `audience_id` | The audience each job targets |
| `job_definition_id` | The job definition each job is created from |
| `revision_number` | Pinned revision, or `None` for "latest at fire time" |
| `interval_hours` | How often the signal fires, in hours (float) |
| `next_run_at` / `last_run_at` | Timestamps of the next and most recent firings |
| `is_paused` | Whether the scheduler is currently skipping this signal |
| `is_public` | Whether other users can discover and read it |
| `created_at` | When the signal was created |

## Configuration

```python
from rapidata import rapidata_config, logger, CompressionConfig

# Logging
rapidata_config.logging.level = "INFO"       # DEBUG, INFO, WARNING, ERROR, CRITICAL
rapidata_config.logging.log_file = "/path/to/log.txt"
rapidata_config.logging.silent_mode = False  # also suppresses the dashboard preview link printed on job creation
rapidata_config.logging.enable_otlp = True   # OpenTelemetry tracing (auto-disabled for environments without an OTLP collector — only rapidata.ai and rabbitdata.ch have one). Defaults to True, except under pytest (where it defaults to False); can also be disabled via RAPIDATA_DISABLE_OTLP=1, or forced on by passing it explicitly
rapidata_config.logging.environment = "rapidata.ai"  # API environment; derives the OTLP collector host (otlp-sdk.<environment>). Set automatically by RapidataClient from its environment

# Upload tuning
rapidata_config.upload.maxWorkers = 25        # Concurrent upload threads (warns above 200)
rapidata_config.upload.maxRetries = 3
rapidata_config.upload.cacheToDisk = True
rapidata_config.upload.cacheTimeout = 1.0
rapidata_config.upload.batchSize = 1000       # URLs per batch (100–5000; below 100 raises ValueError)
rapidata_config.upload.batchPollInterval = 0.5
rapidata_config.upload.compression = CompressionConfig(
    enabled=True,
    quality=70,        # WebP quality 1–100
    max_dimension=1024, # Max width or height in pixels (images only)
)  # Optional: per-upload compression override for images and videos (None = server default)
rapidata_config.upload.contextShortening = False   # When True, shorten EVERY context (over-long ones are always shortened)
rapidata_config.upload.failureTolerance = 0.0      # Fraction of a job's datapoints allowed to fail (0.0–1.0, 0.0 = strict)
rapidata_config.upload.checkForExplicitContent = None  # None = account default, True = force on, False = request skip

# Client-level maintenance
client.clear_all_caches()
client.reset_credentials()
```

`CompressionConfig` fields (all default `None` = defer to server):

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool \| None` | Force compression on or off for **both images and videos**. `False` preserves the original image *and* video (resolution and bitrate) |
| `quality` | `int \| None` | WebP quality (1–100) when image compression runs. **Images only** |
| `max_dimension` | `int \| None` | Max width or height in pixels (≥ 1) when image compression runs. **Images only** (videos have no equivalent knob) |

Governs compression of images **and** videos. Applies to single-asset uploads (`/asset/file` and `/asset/url`) and batched URL uploads (`/asset/batch-upload`).

`failureTolerance` is validated to `0.0..1.0` (`ValueError` otherwise) and is overridden per call by `failure_tolerance` on `create_*_job_definition`.

`checkForExplicitContent = False` only *requests* a skip of the server-side explicit-content check applied on job assignment — it is honored only if your account is permitted; otherwise the check still runs and `assign_job` logs a warning.

`cacheLocation` (`~/.cache/rapidata/upload_cache`) and `cacheShards` (default 32) are immutable at runtime — don't try to assign them; set `cacheShards` via `RAPIDATA_cacheShards`. Each shard holds open file handles, and 32 comfortably covers the default `maxWorkers` of 25.

**`OSError: [Errno 24] Too many open files`:** raise `ulimit -n`, lower `RAPIDATA_cacheShards` / `RAPIDATA_maxWorkers`, or set `cacheToDisk = False` (in-memory cache, no cache file descriptors, but you lose cross-run upload dedup).

All config fields support environment-variable overrides with the `RAPIDATA_` prefix (e.g., `RAPIDATA_maxWorkers=10`, `RAPIDATA_failureTolerance=0.0`, `RAPIDATA_DISABLE_OTLP=1`).

**Client authentication** is also resolved from environment variables: `RAPIDATA_CLIENT_ID` and `RAPIDATA_CLIENT_SECRET` are used before falling back to `~/.config/rapidata/credentials.json` and browser login. Without saved credentials, `RapidataClient()` blocks on a browser login for up to 5 minutes; the login URL is always printed to stderr (even in silent mode). `RAPIDATA_ENVIRONMENT` overrides the API endpoint (default: `rapidata.ai`). `RAPIDATA_TOKEN_FILE` points the client at a shared access-token file (equivalent to `token_file=`). Empty values are treated as unset and fall through to the next resolution layer.

**Checking and establishing auth from the CLI** (`--environment` defaults to `RAPIDATA_ENVIRONMENT`, else `rapidata.ai`). Both commands check `RAPIDATA_TOKEN_FILE`, then `RAPIDATA_CLIENT_ID` + `RAPIDATA_CLIENT_SECRET`, then the credentials saved for `https://auth.{environment}`:

```bash
python -m rapidata status [--environment ENV]  # exit 0 "Authenticated for {env} via {source}."; exit 1 if not logged in. Never starts a login
python -m rapidata login  [--environment ENV]  # browser login; saves credentials (exit 0), or "Login did not complete..." on stderr (exit 1).
                                               #   Exits 0 immediately if already authenticated; otherwise blocks up to 5 minutes
```

Run `status` before the first `RapidataClient()`. If it reports not logged in, run `login` in the background (or with a tool timeout above 5 minutes) and show the user the URL it prints. Every later `RapidataClient()` reuses the saved credentials. For headless runs, set `RAPIDATA_CLIENT_ID` / `RAPIDATA_CLIENT_SECRET` instead.

## Shared Token Files (Distributed Training)

When Rapidata is queried from a large distributed job (e.g. hundreds or thousands of GPU workers hitting a ranking flow), don't let every worker authenticate on its own: each `RapidataClient()` exchanges the client credentials for an access token that expires ~1 hour later, so all workers re-auth in the same instant and the burst gets rate-limited. Authenticate **once** and share the token via a file that all workers can read.

### `RapidataClient` authentication parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `leeway` | int | Seconds before token expiry at which the SDK refreshes/re-reads the token (default 60). A coordinator typically uses a larger value, e.g. `leeway=300`, to renew well before workers need a fresh token |
| `token_file` | str | Path to a shared token file to read the access token from; the SDK re-reads it whenever the in-memory token is within `leeway` of expiry. Also settable via the `RAPIDATA_TOKEN_FILE` env var |
| `token` | dict | An access-token dict passed directly; the SDK never re-reads it, so inject a fresh one with `client.set_token(...)` (or construct a new client) once the token expires |

### `client.maintain_token_file(path, interval=60) → threading.Thread`

Writes the token file at `path` immediately, then keeps rewriting it atomically from a background daemon thread every `interval` seconds, creating the directory if needed. Returns the thread; `.join()` blocks the process forever (drop it if the coordinator also does other work).

### `client.get_token() → dict`

Returns the current access token as a dict. Cheap to call at any frequency: it only contacts the auth server once the token is within `leeway` of expiry. Use it to write the shared token file yourself (write atomically, and keep the absolute `expires_at` field so workers know when to re-read).

### `client.set_token(token) → None`

The counterpart to `get_token()`: replace the token a running client authenticates with, effective from its next request, without reconstructing the client. Expects the complete token object (`access_token`, `token_type`, and an absolute `expires_at` timestamp — pass what `get_token()` returned). Together, `get_token()` and `set_token()` let you move the token over any transport (key-value store, RPC, secret manager, message queue) — a **push** system (the coordinator distributes a fresh token to every worker before the old one expires, each worker applies it with `set_token`) or a **pull** system (each worker periodically fetches the current token from your own endpoint).

```python
from rapidata import RapidataClient

# Coordinator: holds the client credentials and keeps the file fresh
coordinator = RapidataClient(leeway=300)
coordinator.maintain_token_file("/shared/rapidata_token.json").join()

# Worker: reads the shared token, never sees the client secret
client = RapidataClient(token_file="/shared/rapidata_token.json")

# Any transport: export from the coordinator, inject into a worker
token = coordinator.get_token()          # refreshes first if near expiry
worker = RapidataClient(token=token)     # bootstrap a worker from a token object
worker.set_token(coordinator.get_token())  # renew a running worker later
```

## Validation Sets (`client.validation`)

Validation sets hold tasks with known answers used to check labeler quality. Attach one to a flow by passing its id as `validation_set_id` to `create_ranking_flow` / `create_classify_flow`. For job definitions, train an audience with qualification examples instead.

```python
vs = client.validation.create_classification_set(
    name="Animal check",
    instruction="What animal is in this image?",
    answer_options=["Cat", "Dog"],
    datapoints=["cat.jpg", "dog.jpg"],
    truths=[["Cat"], ["Dog"]],           # list of correct answers per datapoint
    # data_type="media", contexts=None, media_contexts=None, explanations=None, dimensions=[],
)
flow = client.flow.create_classify_flow(..., validation_set_id=vs.id)
```

Other constructors: `create_compare_set(name, instruction, datapoints, truths: list[str], ...)`, `create_select_words_set(name, instruction, truths: list[list[int]], datapoints, sentences, required_precision=1.0, required_completeness=1.0, ...)`, `create_locate_set(...)` / `create_draw_set(...)` (`truths: list[list[Box]]`), `create_timestamp_set(...)` (`truths: list[list[tuple[int, int]]]`). Look up with `client.validation.get_validation_set_by_id(id)` and `client.validation.find_validation_sets(name="", amount=10, page=1)`. A `RapidataValidationSet` has `view()`, `delete()`, `update_dimensions(...)`, `update_should_alert(bool)`, `update_can_be_flagged(bool)`.

## Context Management

Datapoint contexts have a backend maximum of **400 characters** (`MAX_CONTEXT_LENGTH`). Contexts over that limit are shortened automatically before upload — this cannot be turned off.

`ContextManager` is importable from the top-level `rapidata` package and is exposed as `client.context` on every `RapidataClient` instance.

### `client.context.shorten_context(context, question) → str`

Shorten a single context for the given question. Results are cached server-side.

### `client.context.shorten_contexts(pairs) → list[str]`

Shorten a batch of `(context, question)` pairs. Returns shortened contexts in the same order as `pairs`. Batches of ≤10 pairs go out as a single request; larger batches are split into chunks of 10 and sent concurrently using `rapidata_config.upload.maxWorkers`, with a `Shortening contexts` progress bar (suppressed by `rapidata_config.logging.silent_mode`).

```python
# Single context
short = client.context.shorten_context(
    context="<a very long description ...>",
    question="Does the main character wear the right clothing?",
)

# Batch
shortened = client.context.shorten_contexts([
    (context_a, question_a),
    (context_b, question_b),
])
```

### Automatic shortening at job creation

Any context exceeding 400 characters is **always** shortened against the task instruction before upload — there is no way to disable this. A warning reports how many contexts were shortened, and per-context before/after lengths are logged at info level. If shortening returns an empty result the original context is kept and a warning is logged.

Set `rapidata_config.upload.contextShortening = True` (default `False`) to shorten **every** context, not just over-long ones.

```python
from rapidata import rapidata_config
rapidata_config.upload.contextShortening = True
```

## Human Prompting Best Practices

- **Be concise** — labelers have ~25 seconds per task
- **Positive framing** — "Which is more realistic?" not "Which is less AI-generated?"
- **Distinct options** — "Poor / Acceptable / Excellent" not "Bad / Not Good / Fine / Good / Great"
- **Single criterion per task** — "What animal is in the image?" not "Does this contain a rabbit, dog, or cat?"
- **Use `NoShuffleSetting()` for scales** — always for Likert or ordered answer options
