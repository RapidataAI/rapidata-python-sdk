# Rapidata SDK — Code Examples

## Simple Classification

```python
from rapidata import RapidataClient

client = RapidataClient()
audience = client.audience.get_audience_by_id("global")

job_def = client.job.create_classification_job_definition(
    name="Image Classification",
    instruction="What's in this image?",
    answer_options=["Cat", "Dog", "Bird"],
    datapoints=["img1.jpg", "img2.jpg"],
)
job = audience.assign_job(job_def)
job.view()
job.display_progress_bar()
results = job.get_results()
df = results.to_pandas()
```

## Classification with Likert Scale

```python
from rapidata import RapidataClient, NoShuffleSetting

client = RapidataClient()
audience = client.audience.get_audience_by_id("global")

job_def = client.job.create_classification_job_definition(
    name="Quality Rating",
    instruction="How well does the video match the description?",
    answer_options=["1: Poor", "2: Fair", "3: Good", "4: Excellent"],
    datapoints=["video1.mp4", "video2.mp4"],
    contexts=["A cat playing piano", "A sunset over the ocean"],
    responses_per_datapoint=15,
    settings=[NoShuffleSetting()],  # Critical for ordered scales
)
job = audience.assign_job(job_def)
```

## Comparison with Early Stopping

```python
from rapidata import RapidataClient

client = RapidataClient()
audience = client.audience.get_audience_by_id("aud_MU1GZYoESyO")

job_def = client.job.create_compare_job_definition(
    name="Model Comparison",
    instruction="Which image follows the prompt better?",
    datapoints=[
        ["flux_cat.jpg", "mj_cat.jpg"],
        ["flux_sunset.jpg", "mj_sunset.jpg"],
    ],
    contexts=["A cat on a chair", "A sunset over mountains"],
    responses_per_datapoint=50,
    confidence_threshold=0.99,
    a_b_names=["Flux", "Midjourney"],
)
job = audience.assign_job(job_def)
job.view()
job.display_progress_bar()
results = job.get_results()
```

## Classification with Quorum Stopping

```python
from rapidata import RapidataClient

client = RapidataClient()
audience = client.audience.get_audience_by_id("global")

job_def = client.job.create_classification_job_definition(
    name="Animal Classification with Quorum",
    instruction="What animal is in this image?",
    answer_options=["Cat", "Dog"],
    datapoints=["pet1.jpg", "pet2.jpg"],
    responses_per_datapoint=10,  # Maximum responses
    quorum_threshold=7,          # Stop when 7 responses agree
)
job = audience.assign_job(job_def)
job.view()
job.display_progress_bar()
results = job.get_results()
```

## Comparison Allowing "Neither" / "Both"

```python
from rapidata import RapidataClient, AllowNeitherBothSetting

client = RapidataClient()
audience = client.audience.get_audience_by_id("global")

job_def = client.job.create_compare_job_definition(
    name="Text Comparison",
    instruction="Which response is more helpful?",
    # With data_type="text" each datapoint is the text itself, not a file path.
    datapoints=[[
        "Restart the router, then reconnect.",
        "Have you tried turning it off and on again?",
    ]],
    data_type="text",
    settings=[AllowNeitherBothSetting()],
)
job = audience.assign_job(job_def)
```

## Locate Job

```python
from rapidata import RapidataClient

client = RapidataClient()

# Simple: use the ready-to-go global pool
audience = client.audience.get_audience_by_id("global")

job_def = client.job.create_locate_job_definition(
    name="Artifact Detection",
    instruction="Tap on any visual glitches or errors in the image.",
    datapoints=["img1.jpg", "img2.jpg", "img3.jpg"],
    responses_per_datapoint=35,
)
job = audience.assign_job(job_def)
job.view()
job.display_progress_bar()
results = job.get_results()
```

Custom audience with locate qualification examples:

```python
from rapidata import RapidataClient, Box

client = RapidataClient()

audience = client.audience.create_audience(name="Artifact Detection Audience")

EXAMPLES = [
    ("example1.jpg", [Box(x_min=0.44, y_min=0.42, x_max=0.58, y_max=0.63)]),
    ("example2.jpg", [Box(x_min=0.07, y_min=0.37, x_max=0.39, y_max=0.71)]),
    ("example3.jpg", [Box(x_min=0.04, y_min=0.10, x_max=0.31, y_max=0.28)]),
]

for datapoint, truths in EXAMPLES:
    audience.add_locate_example(
        instruction="Tap on any visual glitches or errors in the image.",
        datapoint=datapoint,
        truths=truths,
        explanation="The artifact is within the highlighted region.",
    )

audience.start_recruiting()  # required — a job assigned before this can never receive responses

job_def = client.job.create_locate_job_definition(
    name="Artifact Detection",
    instruction="Tap on any visual glitches or errors in the image.",
    datapoints=["img1.jpg", "img2.jpg", "img3.jpg"],
    responses_per_datapoint=35,
)
job = audience.assign_job(job_def)
job.view()
job.display_progress_bar()
results = job.get_results()
```

## Draw Job

```python
from rapidata import RapidataClient

client = RapidataClient()

# Simple: use the ready-to-go global pool
audience = client.audience.get_audience_by_id("global")

job_def = client.job.create_draw_job_definition(
    name="Artifact Drawing",
    instruction="Color in any visual glitches or errors in the image.",
    datapoints=["img1.jpg", "img2.jpg", "img3.jpg"],
    responses_per_datapoint=35,
)
job = audience.assign_job(job_def)
job.view()
job.display_progress_bar()
results = job.get_results()
```

For a custom draw audience, follow the locate custom-audience example above with `audience.add_draw_example(...)` (same `truths=list[Box]` shape).

## Select Words Job

```python
from rapidata import RapidataClient

IMAGES = ["img1.jpg", "img2.jpg", "img3.jpg", "img4.jpg"]
PROMPTS = [
    "The black camera was next to the white tripod.",
    "Four cars on the street.",
    "Car is bigger than the airplane.",
    "One cat and two dogs sitting on the grass.",
]
SENTENCES = [p + " [No_mistakes]" for p in PROMPTS]

client = RapidataClient()
audience = client.audience.get_audience_by_id("global")

job_def = client.job.create_select_words_job_definition(
    name="Image-Text Alignment",
    instruction="The image is based on the text below. Select mistakes, i.e., words that are not aligned with the image.",
    datapoints=IMAGES,
    sentences=SENTENCES,
    responses_per_datapoint=15,
)
job = audience.assign_job(job_def)
job.view()
job.display_progress_bar()
results = job.get_results()
```

## Free Text Job

```python
from rapidata import RapidataClient

client = RapidataClient()
audience = client.audience.get_audience_by_id("global")

job_def = client.job.create_free_text_job_definition(
    name="Prompt Collection",
    instruction="What would you like to ask an AI? Please spell out the question.",
    datapoints=["image.jpg"],
    responses_per_datapoint=15,
)
job = audience.assign_job(job_def)
job.view()
job.display_progress_bar()
results = job.get_results()
```

## Free-Text Length Constraints

Use length constraints sparingly. Free-text responses are already filtered by a built-in reasonableness check, so these settings are usually unnecessary and will reject otherwise valid answers. Only set them when the question genuinely demands a specific length.

```python
from rapidata import (
    RapidataClient,
    FreeTextMinimumCharactersSetting,
    FreeTextMaxCharactersSetting,
)

client = RapidataClient()
audience = client.audience.get_audience_by_id("global")

job_def = client.job.create_free_text_job_definition(
    name="Caption Generation",
    instruction="Describe what's happening in this image in one sentence.",
    datapoints=["scene1.jpg", "scene2.jpg"],
    settings=[
        FreeTextMinimumCharactersSetting(20),
        FreeTextMaxCharactersSetting(200),
    ],
)
job = audience.assign_job(job_def)
```

## Custom Audience with Full Workflow

```python
from rapidata import RapidataClient

client = RapidataClient()

# Create and train audience with diverse examples.
# The admission bar is optional: target_accuracy is the fraction of qualification
# tasks a labeler must get right (server default 0.75), min_tasks how many tasks
# before that verdict is trusted (default 10), max_tasks an optional cap after
# which a verdict is forced. Supplying just one is fine — the rest fall back to
# the defaults.
audience = client.audience.create_audience(
    name="Image Quality Experts",
    target_accuracy=0.8,
    min_tasks=12,
)

DATAPOINTS = [
    ["good_example.jpg", "bad_example.jpg"],
    ["clear.jpg", "blurry.jpg"],
    ["accurate.jpg", "inaccurate.jpg"],
]
PROMPTS = [
    "A cat on a chair",
    "A sunset over mountains",
    "A red sports car",
]

for prompt, datapoint in zip(PROMPTS, DATAPOINTS):
    audience.add_compare_example(
        instruction="Which image follows the prompt better?",
        datapoint=datapoint,
        truth=datapoint[0],
        context=prompt,
        data_type="media",
        explanation="The first image better matches the prompt description.",  # Shown to labelers who answer incorrectly
    )

# Inspect the examples we just added
print(audience.get_examples())

# Start recruiting once the examples are added and reviewed — required and explicit.
# A job assigned before this can never receive responses (get_results() raises).
# A backend failure here raises RapidataError instead of being swallowed.
audience.start_recruiting()

# Follow the recruiting funnel. Counts are mutually exclusive (one bucket per
# annotator) and all-zero for an audience that has not recruited anyone yet.
metrics = audience.get_recruiting_metrics()
print(
    f"{metrics.graduated} graduated, {metrics.distilling} distilling, "
    f"{metrics.dropped} dropped, {metrics.inactive} inactive"
)

# Create and run job
job_def = client.job.create_compare_job_definition(
    name="Production Comparison",
    instruction="Which image follows the prompt better?",
    datapoints=[
        ["model_a_1.jpg", "model_b_1.jpg"],
        ["model_a_2.jpg", "model_b_2.jpg"],
    ],
    contexts=["A wizard casting a spell", "A futuristic city"],
    responses_per_datapoint=20,
    a_b_names=["Model A", "Model B"],
)
job = audience.assign_job(job_def)
job.view()
job.display_progress_bar()
results = job.get_results()
```

## Audience with Demographic Filters

```python
from rapidata import (
    RapidataClient, CountryFilter, LanguageFilter,
)

client = RapidataClient()
audience = client.audience.create_audience(name="US English Evaluators")
audience.update_filters([
    CountryFilter(country_codes=["US", "CA"]),
    LanguageFilter(language_codes=["en"]),
])

# Recruiting is explicit: a custom audience recruits nobody until you add >=3 qualification
# examples AND then call start_recruiting(). A job assigned before recruiting starts can never
# receive responses (get_results() raises). So: add examples, start_recruiting, THEN assign.
EXAMPLES = [
    ("clear.jpg", ["Excellent"]),
    ("decent.jpg", ["Good"]),
    ("blurry.jpg", ["Poor"]),
]
for datapoint, truth in EXAMPLES:
    audience.add_classification_example(
        instruction="Rate the image quality",
        answer_options=["Poor", "Good", "Excellent"],
        datapoint=datapoint,
        truth=truth,
        data_type="media",
    )

audience.start_recruiting()  # required — without this the job below never gets responses

job_def = client.job.create_classification_job_definition(
    name="Image Quality (US/EN)",
    instruction="Rate the image quality",
    answer_options=["Poor", "Good", "Excellent"],
    datapoints=["img1.jpg", "img2.jpg"],
    responses_per_datapoint=10,
)
job = audience.assign_job(job_def)
job.display_progress_bar()
results = job.get_results()

# If you DON'T need task-specific qualification, skip create_audience + examples entirely
# and use the ready-to-go global pool: client.audience.get_audience_by_id("global").
#
# update_filters sets recruitment filters: CountryFilter / LanguageFilter (+ And/Or/Not).
# AgeFilter / GenderFilter / DeviceFilter narrow the graduates, so use them with
# audience.filter(...) (see below).
```

## Filtered Audience

Derive a filtered subset of a trained audience without re-onboarding labelers:

```python
from rapidata import RapidataClient, CountryFilter, LanguageFilter, AgeFilter, AgeGroup

client = RapidataClient()

base = client.audience.get_audience_by_id("audience_id")

# .filter() narrows an audience's graduates. Beyond CountryFilter / LanguageFilter it
# accepts AgeFilter, GenderFilter and DeviceFilter, plus And/Or/Not (& | ~).
# Multiple filters in the list are ANDed.
filtered = base.filter([
    CountryFilter(["US"]),
    LanguageFilter(["en"]),
    AgeFilter([AgeGroup.BETWEEN_18_29]),
])

job_def = client.job.create_classification_job_definition(
    name="US Young Adult Classification",
    instruction="What product is shown?",
    answer_options=["Phone", "Laptop", "Tablet"],
    datapoints=["p1.jpg", "p2.jpg"],
)
job = filtered.assign_job(job_def)
job.display_progress_bar()
results = job.get_results()
```

## Ranking via Job Definition API

```python
from rapidata import RapidataClient

client = RapidataClient()
audience = client.audience.get_audience_by_id("global")

job_def = client.job.create_ranking_job_definition(
    name="Image Quality Ranking",
    instruction="Which image looks better?",
    datapoints=[["img1.jpg", "img2.jpg", "img3.jpg", "img4.jpg"]],  # outer list = independent rankings
    comparison_budget_per_ranking=50,
    # With >10 datapoints, matchups are chosen adaptively (Elo-style) within the
    # budget and random_comparisons_ratio applies. With <=10 (as here), every
    # unique pair is compared with the budget spread evenly across pairs, and
    # random_comparisons_ratio has no effect.
    random_comparisons_ratio=0.5,
)
job = audience.assign_job(job_def)
job.view()
job.display_progress_bar()
results = job.get_results()
```

## Continuous Ranking Flow

```python
from rapidata import RapidataClient

client = RapidataClient()

flow = client.flow.create_ranking_flow(
    name="Ongoing Quality Ranking",
    instruction="Which image looks better?",
    max_response_threshold=200,  # Aim for 200 responses per item
    min_response_threshold=50,   # Accept as few as 50; fewer → item marked Incomplete
)

# Preheat for low-latency responses (call ~5 minutes before time-sensitive batches)
client.flow.preheat()

# Submit batches over time
batch1 = flow.create_new_flow_batch(
    datapoints=["gen1.jpg", "gen2.jpg", "gen3.jpg"],
    context="Generated from prompt A",
    time_to_live=300,
)

result1 = batch1.get_results()               # Blocks until complete
matrix1 = batch1.get_win_loss_matrix()       # Pandas DataFrame
print(result1.datapoints, result1.total_votes)

# Items sorted from best to worst (scores are Elo-style Bradley-Terry estimates)
ranked = sorted(result1.datapoints.items(), key=lambda item: item[1], reverse=True)

# Later, submit more batches to the same flow
batch2 = flow.create_new_flow_batch(
    datapoints=["gen4.jpg", "gen5.jpg", "gen6.jpg"],
    context="Generated from prompt B",
    time_to_live=300,
)

# Tune the flow as you learn more
flow.update_config(instruction="Which image looks better overall?", max_responses=250)
# drain_duration / serve_timeout (seconds) are also updatable; omitted args keep current values
flow.update_config(drain_duration=30, serve_timeout=60)
```

## Continuous Classify Flow

```python
from rapidata import RapidataClient, ClassifyFlowItemResult

client = RapidataClient()

flow = client.flow.create_classify_flow(
    name="Text Detection",
    instruction="Does this image contain text?",
    # 2-8 answer options. A plain string is shown and returned as-is; a
    # (label, value) tuple shows the label but returns the value in results.
    categories=[("Yes, clearly readable", "yes"), ("No", "no")],
    max_responses_per_datapoint=15,  # accepted responses that close an image; collection stops once reached
    min_responses_per_datapoint=10,  # avg responses/image needed (once TTL ends) to be Completed vs Incomplete; >= 1
    # Time-to-live is set per batch only (see create_new_flow_batch below).
)

# Preheat for low-latency responses (call ~5 minutes before time-sensitive batches)
client.flow.preheat()

# Submit batches over time. Classify flows attach context per datapoint via
# contexts / context_assets (NOT the ranking-only batch-level context=).
# contexts is one text string per datapoint; context_assets is one list of asset
# paths/URLs per datapoint (list[list[str]] — a list even for a single asset).
# Both must have exactly one entry per datapoint.
batch = flow.create_new_flow_batch(
    datapoints=["gen1.jpg", "gen2.jpg", "gen3.jpg"],
    contexts=["Generated from prompt A", "Generated from prompt B", "Generated from prompt C"],
    time_to_live=240,  # seconds (up to 3600; min 60 with default flow settings); set per batch only
)

result: ClassifyFlowItemResult = batch.get_results()  # Blocks until complete
print(result.total_responses)

# datapoints maps each asset (keyed by source URL, else original filename) to its
# classification outcome.
for asset, outcome in result.datapoints.items():
    # majority_value is the category value chosen most often, or None on a tie.
    # distribution maps EVERY category value defined in the flow (in flow category order)
    # to its response count, with 0 for categories nobody chose, e.g. {"yes": 0, "no": 5}.
    print(asset, outcome.majority_value, outcome.distribution, outcome.response_count)

# Only the drain duration (seconds) can be updated on a classify flow;
# instruction, categories and thresholds are fixed after creation.
flow.update_config(drain_duration=30)
```

## Model Benchmark (MRI)

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
    # By default an initial run evaluates the models already in the benchmark against
    # each other so the leaderboard starts with standings. Set skip_initial_run=True to
    # start with no responses and no standings — models added later still compare
    # against the whole existing field, and boosting still works. Create-only: it is
    # applied at creation and not recorded on the leaderboard, so there's no property to
    # read it back.
    skip_initial_run=False,
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

## Model Benchmark — Voter Demographics

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

## Model Benchmark — Staged Submission

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

## Model Benchmark — Recovering a Partial Upload

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

## Handling Failed Uploads

```python
from rapidata import RapidataClient
from rapidata.rapidata_client.exceptions import FailedUploadException

client = RapidataClient()
audience = client.audience.get_audience_by_id("global")

datapoints = ["valid1.jpg", "broken_url", "valid2.jpg", "missing.jpg"]

try:
    # failure_tolerance is the fraction of datapoints allowed to fail while still
    # creating the definition (default 0.0 = strict). At least one datapoint must
    # always upload successfully.
    job_def = client.job.create_classification_job_definition(
        name="With Failures",
        instruction="What's in this image?",
        answer_options=["Cat", "Dog"],
        datapoints=datapoints,
        failure_tolerance=0.1,
    )
except FailedUploadException as e:
    # Outside the tolerance NO job definition is created — e.job_definition is None.
    print(f"{len(e.failed_uploads)} of {len(datapoints)} failed to upload")
    for reason, failed in e.failures_by_reason.items():
        print(f"  {reason}: {len(failed)}")
    # Remote-URL failures are also grouped by ingestion stage (download, redirect,
    # content_type, decode, timeout, size, validation, internal). Only "internal" is
    # a Rapidata-side fault; the rest are caller-actionable. Local-file failures have
    # no stage, so this dict can be empty.
    for stage, failed in e.failures_by_stage.items():
        print(f"  stage {stage}: {len(failed)}")
    for fu in e.detailed_failures:
        print(f"    - {fu.item}: {fu.error_type}: {fu.error_message} "
              f"(stage={fu.stage}, http_status={fu.http_status})")

    # ...fix the failing datapoints (bad URLs, missing files, ...)...
    # retry() re-uploads ONLY the failed datapoints into the SAME dataset and
    # finishes creating the definition. It raises FailedUploadException again if
    # failures remain outside tolerance, so it can be looped.
    job_def = e.retry()

job = audience.assign_job(job_def)
```

## Queueing Jobs on One Audience

By default `assign_job` starts a job right away. Pass `run_after` to queue a job
that only starts once an earlier job **completes or fails** — this keeps a single
audience from splitting its annotators across two jobs at the same time. The queued
job is created immediately in the `Queued` state.

```python
from rapidata import RapidataClient

client = RapidataClient()
audience = client.audience.get_audience_by_id("global")

first_def = client.job.create_classification_job_definition(
    name="Batch 1",
    instruction="What's in this image?",
    answer_options=["Cat", "Dog", "Bird"],
    datapoints=["img1.jpg", "img2.jpg"],
)
second_def = client.job.create_classification_job_definition(
    name="Batch 2",
    instruction="What's in this image?",
    answer_options=["Cat", "Dog", "Bird"],
    datapoints=["img3.jpg", "img4.jpg"],
)

first = audience.assign_job(first_def)
# Starts only after `first` completes or fails.
second = audience.assign_job(second_def, run_after=first)

# You can also queue behind a job id (e.g. from an earlier session), and chain
# further by pointing each new job at its predecessor.
third_def = client.job.create_classification_job_definition(
    name="Batch 3",
    instruction="What's in this image?",
    answer_options=["Cat", "Dog", "Bird"],
    datapoints=["img5.jpg", "img6.jpg"],
)
third = audience.assign_job(third_def, run_after=second.id)
```

## Updating a Job Definition's Dataset

```python
# Keep the job definition (and its config / audience) but swap in new datapoints.
job_def.update_dataset(
    datapoints=["new1.jpg", "new2.jpg", "new3.jpg"],
    data_type="media",
    contexts=["ctx 1", "ctx 2", "ctx 3"],
)
```

## Checking Job Progress Without Blocking

`get_progress()` returns immediately with the current state, unlike `display_progress_bar()` / `get_results()`.

```python
from rapidata import RapidataClient

client = RapidataClient()
job = client.job.get_job_by_id("job_id")

progress = job.get_progress()
print(f"{progress.state}: {progress.completion_percentage:.1f}% done")

# recruiting is None for curated audiences (e.g. "global"), which don't recruit.
if progress.recruiting:
    print(f"{progress.recruiting.graduated} graduated, "
          f"{progress.recruiting.distilling} still distilling")

# get_results() / display_progress_bar() raise up front if the job's audience can never
# produce responses — nobody graduated AND nobody is being recruited. An audience
# that is still distilling keeps waiting normally.
results = job.get_results()
```

## Estimating Job Cost Before Launch

Check what a run is expected to cost before committing to it. `estimated_cost` is available on a job definition (before assigning it to an audience) and on a running job.

```python
from rapidata import RapidataClient

client = RapidataClient()
audience = client.audience.get_audience_by_id("aud_MU1GZYoESyO")

job_def = client.job.create_compare_job_definition(
    name="Example Image Prompt Alignment",
    instruction="Which image matches the description better?",
    datapoints=[["midjourney.jpg", "flux.jpg"]],
    contexts=["A small blue book sitting on a large red book."],
)

# Reading estimated_cost blocks briefly until the estimate is priced.
estimate = job_def.estimated_cost
print(
    f"About {estimate.estimated_cost} for {estimate.required_responses} responses "
    f"across {estimate.datapoint_count} datapoints"
)

# The same property is available once the job is running.
job = audience.assign_job(job_def)
print(job.estimated_cost.estimated_cost)
```

## Checking Billing Spend and Remaining Credit

Read how much the current billing period has cost so far and how much credit is
left. Billing is settled per **organization**, so these figures cover everything
the organization spent, not only the jobs this client created.

```python
from rapidata import RapidataClient
from rapidata.rapidata_client.exceptions import RapidataError

client = RapidataClient()

try:
    # Returns the period currently accruing cost. All amounts are in US dollars,
    # rounded to the cent, and are a snapshot — fetch again for an up-to-date figure.
    period = client.billing.get_current_billing_period()
except RapidataError as e:
    # A period only opens once there is something to bill.
    if e.status_code == 404:
        print("No active billing period yet.")
        raise
    raise

# outstanding_cost is gross_cost minus discount — what the period would be
# invoiced for today. status is "Open" while still accruing cost.
print(
    f"[{period.status}] {period.start_date:%Y-%m-%d} → {period.end_date:%Y-%m-%d}: "
    f"${period.outstanding_cost} outstanding "
    f"(${period.gross_cost} gross - ${period.discount} discount) "
    f"over {period.response_count} responses"
)

# credits is the prepaid balance still available (an org-level balance that carries
# across periods), or None when billed for usage rather than from a prepaid balance.
# effective_limit is the most the org may spend this period, or None when uncapped.
if period.credits is not None:
    print(f"${period.credits} credit remaining of ${period.effective_limit} granted")

# The outstanding balance is what the organization currently owes: finalized-but-unpaid
# invoices plus the settled cost of ended periods not yet invoiced. It excludes the
# current, still-accruing period, is already net of vouchers and discounts, and is
# returned in US dollars rounded to the cent (0.0 when nothing is owed).
owed = client.billing.get_outstanding_balance()
print(f"Outstanding balance: ${owed}")
```

## Context Shortening

Contexts longer than 400 characters are **always** shortened automatically at job creation time (a warning reports how many were shortened) — this cannot be turned off. Use `client.context` to shorten them yourself beforehand, or opt into shortening *every* context.

```python
from rapidata import RapidataClient, rapidata_config

client = RapidataClient()

# Shorten a single context for a specific question
short = client.context.shorten_context(
    context="<a very long, detailed scene description ...>",
    question="Does the main character wear the right clothing?",
)

# Shorten a batch of (context, question) pairs in one request
shortened = client.context.shorten_contexts([
    ("Long scene description A ...", "What is the dominant color?"),
    ("Long scene description B ...", "How many people are visible?"),
])

# Or shorten EVERY context (not just over-long ones) at job creation time
rapidata_config.upload.contextShortening = True

job_def = client.job.create_classification_job_definition(
    name="Outfit check",
    instruction="Does the main character wear the right clothing?",
    answer_options=["Yes", "No"],
    datapoints=["scene.jpg"],
    contexts=["<a very long, detailed scene description ...>"],
)
```

## Signal (Scheduled Labeling)

```python
from rapidata import RapidataClient

client = RapidataClient()

audience = client.audience.get_audience_by_id("aud_MU1GZYoESyO")

job_def = client.job.create_compare_job_definition(
    name="Prompt Alignment Job",
    instruction="Which image follows the prompt more accurately?",
    datapoints=[["flux_book.jpg", "mj_book.jpg"]],
    contexts=["A small blue book sitting on a large red book."],
)

# Create a signal that fires every 24 hours
signal = client.signals.create_signal(
    name="Daily prompt alignment",
    audience=audience,
    job_definition=job_def,
    interval_hours=24,
)

# Inspect jobs created by the signal so far
for job in signal.get_jobs(page_size=10):
    print(job, job.get_status())

# Trigger a job immediately without waiting for the schedule
signal.trigger()
job = signal.wait_for_next_job(timeout=600)
results = job.get_results()

# Pause / resume / update
signal.pause()
signal.resume()
signal.update(name="Hourly prompt alignment", interval_hours=1)

# Look up later
signal = client.signals.get_signal_by_id("signal_id")
signals = client.signals.find_signals(name="alignment")

# Delete when no longer needed
signal.delete()
```

## Sharing a Token Across Workers (Distributed Training)

Authenticate once in a coordinator process and share the token with many workers via a file, so thousands of workers don't all re-authenticate at the same instant.

```python
# --- Coordinator (holds the client credentials) ---
from rapidata import RapidataClient

coordinator = RapidataClient(leeway=300)  # renew 5 min before expiry
# Writes the file now, then keeps it fresh from a background thread.
# .join() blocks forever; drop it if the coordinator also does other work.
coordinator.maintain_token_file("/shared/rapidata_token.json").join()
```

```python
# --- Worker (never sees the client secret) ---
from rapidata import RapidataClient

client = RapidataClient(token_file="/shared/rapidata_token.json")
# or set RAPIDATA_TOKEN_FILE and construct with no arguments.
# The SDK re-reads the file whenever the in-memory token nears expiry.
```

Rolling your own file writer with `get_token()`:

```python
import json, os, time
from rapidata import RapidataClient

TOKEN_FILE = "/shared/rapidata_token.json"
coordinator = RapidataClient(leeway=300)
os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)

def write_token(token: dict) -> None:
    tmp = TOKEN_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(token, f)          # keep the absolute expires_at field
    os.replace(tmp, TOKEN_FILE)      # atomic: workers never read a half-written file

while True:
    write_token(coordinator.get_token())  # only re-auths when near expiry
    time.sleep(60)
```

The file is just one transport. To move the token over any transport (key-value store, RPC, secret manager, message queue), pair `get_token()` on the coordinator with `set_token()` on the worker — no shared file needed:

```python
from rapidata import RapidataClient

# --- Coordinator: export the current token (refreshes it first if near expiry) ---
coordinator = RapidataClient(leeway=300)
token = coordinator.get_token()
# ... distribute `token` through any transport you like ...

# --- Worker: bootstrap directly from a token object, then renew in place ---
worker = RapidataClient(token=token)
# Later, when a fresh token arrives, inject it without reconstructing the client:
fresh_token = coordinator.get_token()  # in practice received over your transport
worker.set_token(fresh_token)  # used from the next request on
```
