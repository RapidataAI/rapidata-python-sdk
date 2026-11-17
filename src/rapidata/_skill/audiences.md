# Audiences

> Part of the Rapidata agent skill: `python -m rapidata skill audiences`. The **Task design rules** and **Key Gotchas** in the main guide (`python -m rapidata skill`) apply to everything here.

Recruitment filters (country, language) and filtered audiences (age, gender, device): `python -m rapidata skill filters`.

## What an audience is

**Goal.** An audience selects a specific group of annotators for a **specific task**. You tailor the pool to that task two ways — by training it on **qualification examples** (tasks with a known-correct answer; only labelers who answer them correctly are recruited) and/or by attaching **recruitment filters** (country, language, demographics). The point is to get the *right* annotators onto *that* task.

A task-specific audience is meant for that task and its repeated or scheduled runs — **not** for reuse on a different, unrelated task. The qualification examples encode what "good" means for the original task; once the task changes they no longer describe the work, so reusing the audience silently loses the quality it was built for. Create a new audience per distinct task. (The `global` audience is the exception: it's the generic baseline pool for tasks that need no special qualification.)

**Three kinds:**

| Kind | How to get it | When to use |
|------|---------------|-------------|
| global | `client.audience.get_audience_by_id("global")` | Instant, baseline quality, no setup |
| curated | `client.audience.get_audience_by_id("aud_MU1GZYoESyO")` (alignment) | Pre-trained on a domain |
| custom | `client.audience.create_audience(name=...)` + `add_*_example(...)` | You need labelers qualified on *your* task |

## Custom audiences

Create an audience trained on your specific task.

⚠️ **Recruiting is explicit — you must start it yourself.** A custom audience recruits nobody until you (1) add **at least `min_tasks` qualification examples** (default 10, never fewer than 3) with `add_*_example(...)` and (2) call `audience.start_recruiting()`. With fewer examples than `min_tasks`, `start_recruiting()` raises `RapidataError` ("The graduation rule needs 10 validation tasks, but the audience only has 8") — add examples, or pass a lower `min_tasks` to `create_audience`. Adding examples does **not** start recruiting; until `start_recruiting()` is called the audience stays in its `Created` state. A job assigned to such an audience is still created (with a warning), but it can never receive responses — `display_progress_bar()` / `get_results()` raise an error explaining that nobody graduated and nobody is being recruited. Call `start_recruiting()` **once**, after all examples are added and reviewed, before `assign_job`. If you don't need task-specific qualification, skip all of this and use the ready-to-go global pool with no setup: `client.audience.get_audience_by_id("global")`.

**Important:** Every qualification example and its associated truth must be manually and thoroughly reviewed by a human before use. If an example has a wrong or ambiguous truth value, the qualification process will filter out good labelers who answer correctly while letting through bad labelers who happen to match the incorrect answer — completely inverting quality control. Always verify that each example has a clear, unambiguous correct answer.

```python
from rapidata import Box, NoShuffleSetting, AllowNeitherBothSetting

audience = client.audience.create_audience(
    name="Expert Evaluators",
    # target_accuracy=0.8,   # Optional: fraction of qualification tasks (0-1) a labeler must get right (server default 0.75)
    # min_tasks=12,          # Optional: qualification tasks before the accuracy verdict is trusted (server default 10)
    # max_tasks=30,          # Optional: cap on admission-trial tasks before a verdict is forced (default: no cap)
    # accelerate_graduation=True,  # Optional: labelers who already qualified on the same examples or kind of task take a 5-task trial instead of the full one (default False)
)

# Add classification examples
audience.add_classification_example(
    instruction="Rate image quality",
    answer_options=["Poor", "Good", "Excellent"],
    datapoint="example.jpg",
    truth=["Excellent"],
    context="Optional context",
    data_type="media",
    explanation="This image is excellent due to its high resolution and sharp focus.",  # Shown to labelers who answer incorrectly
    settings=[NoShuffleSetting()],  # Optional: match job settings so labelers qualify on the same UI
)

# Add comparison examples
audience.add_compare_example(
    instruction="Which image follows the prompt better?",
    datapoint=["good.jpg", "bad.jpg"],
    truth="good.jpg",
    context="A cat on a chair",
    data_type="media",
    explanation="The first image clearly shows a cat sitting on a chair as described.",  # Shown to labelers who answer incorrectly
    settings=[AllowNeitherBothSetting()],  # Optional: match job settings so labelers qualify on the same UI
)

# Add locate examples — Box coordinates are image ratios (0.0–1.0)
audience.add_locate_example(
    instruction="Tap on any visual glitches or errors in the image.",
    datapoint="example_with_artifact.jpg",
    truths=[Box(x_min=0.44, y_min=0.42, x_max=0.58, y_max=0.63)],
    context="Optional context",
    explanation="The artifact is in the highlighted region.",  # Shown to labelers who answer incorrectly
    settings=[...],  # Optional: match job settings so labelers qualify on the same UI
)

# Add draw examples — graded on whether the drawn lines fall within a box
audience.add_draw_example(
    instruction="Color in any visual glitches or errors in the image.",
    datapoint="example_with_artifact.jpg",
    truths=[Box(x_min=0.44, y_min=0.42, x_max=0.58, y_max=0.63)],
    explanation="The artifact is within the highlighted region.",  # Shown to labelers who answer incorrectly
    settings=[...],  # Optional: match job settings so labelers qualify on the same UI
)

# Add select words examples
audience.add_select_words_example(
    instruction="Select the words not correctly depicted in the image.",
    datapoint="image.jpg",
    sentence="a white cat on a sunny beach [No_mistakes]",
    truths=[1],  # 0-based word indices to select; index 1 = "white" if the cat is black
    # required_precision=1, required_completeness=1,  # defaults: no wrong words, all correct words
    explanation="The cat in the image is black, not white.",  # Shown to labelers who answer incorrectly
    settings=[...],  # Optional: match job settings so labelers qualify on the same UI
)

# Inspect the examples currently on the audience
examples_df = audience.get_examples(amount=10, page=1)

# Remove one with a wrong or ambiguous truth; ids are in the "id" column
audience.delete_example(examples_df["id"].iloc[0])

# Once >= min_tasks examples (default 10) are added and reviewed, start recruiting. This is required and explicit:
# adding examples does not start it, and a job assigned before this can never get responses.
audience.start_recruiting()

# Watch the funnel fill up (graduated / distilling / dropped / inactive)
metrics = audience.get_recruiting_metrics()
print(metrics.graduated, metrics.distilling)

# Now the audience recruits against the examples; assign a job as usual.
job = audience.assign_job(job_def)
```

## Managing audiences

**Managing audiences (`client.audience`):**
- `client.audience.create_audience(name, filters=None, target_accuracy=None, min_tasks=None, max_tasks=None)` — create a custom audience. The last three set the admission bar for qualification: `target_accuracy` (0–1, server default `0.75`), `min_tasks` (server default `10`), `max_tasks` (no cap by default). Supplying only some of them is fine — the SDK fills in the defaults. Raises `ValueError` for an accuracy outside 0–1, `min_tasks < 1`, or `max_tasks < min_tasks`.
- `client.audience.get_audience_by_id(audience_id)` — fetch by id; pass `"global"` for the ready-to-go global audience
- `client.audience.find_audiences(name="", amount=10, page=1)` — list your audiences (newest first), optionally filtered by name

**Audience methods:**
- `audience.start_recruiting()` — begin recruiting/onboarding annotators against the audience's qualification examples. **Required and explicit for custom audiences**: call it once, after adding at least `min_tasks` examples (default 10, min 3) and before `assign_job` — adding examples never starts recruiting on its own, and a job assigned before recruiting has started can never receive responses. Calling it again on the same audience object is a no-op; a backend failure raises `RapidataError` rather than being swallowed. Returns the audience, so it chains. Not needed for the global/curated pools.
- `audience.get_recruiting_metrics()` — snapshot of the audience's recruiting funnel as a `RecruitingMetrics` (`graduated` = eligible to work now, `distilling` = still qualifying, `dropped`, `inactive`; one bucket per annotator). All zeros before `start_recruiting()` has pulled anyone in, and for curated audiences.
- `audience.assign_job(job_definition, run_after=None)` — start a job. Never blocks on funds: the job is always created, but if its estimated cost exceeds your account balance a cost warning is logged (with the estimate, your balance, and the shortfall) and the job may pause partway until you top up. A warning is also logged if the audience has no graduated annotators yet. Pass `run_after` (a `RapidataJob`, a job id string, or `None`) to queue this job behind an earlier one: the new job is created immediately in the `Queued` state and only starts once the preceding job **completes or fails**, so a single audience never splits its annotators across two jobs at once. Default `None` starts the job right away. Chain further by pointing each new job at its predecessor.

- `audience.find_jobs(name="filter", amount=10, page=1)` — find assigned jobs
- `audience.update_filters([...])` — replace the recruitment filters on this audience (audience-supported filters only — see below)
- `audience.filter([filters])` — derive a filtered slice of this audience's graduated labelers without re-onboarding; multiple filters are ANDed. Returns a `RapidataFilteredAudience` (id prefixed `fau_`) that exposes only `assign_job` and `find_jobs` (plus `id`, `name`, `filters`) — no examples, `update_filters`, `delete`, or nested `.filter()`. Its id (or the object) can be passed as a leaderboard's `audience_id`
- `audience.update_name("New Name")` — rename
- `audience.get_examples(amount=10, page=1)` — list qualification examples (DataFrame with columns `id`, `asset`, `truth`, `context`, `contextAsset`)
- `audience.delete_example(example_id)` — delete one qualification example by its `id` from `get_examples`, e.g. one whose truth turned out wrong or ambiguous. Returns the audience, so it chains.
- `audience.delete()` — delete the audience

**Audience-supported filters:** `CountryFilter`, `LanguageFilter`, `AgeFilter` (`AgeGroup`), `GenderFilter` (`Gender`), and `DeviceFilter` (`DeviceType`), plus the `AndFilter`/`OrFilter`/`NotFilter` combinators (also via `&` / `|` / `~`). `UserScoreFilter`, `CampaignFilter`, and `CustomFilter` are **not supported on audiences** and raise `NotImplementedError`.

## Admission bar (`create_audience`)

Three optional parameters set how strict qualification is:

| Parameter | Type | Description |
|-----------|------|-------------|
| `target_accuracy` | float \| None | Fraction of qualification tasks (0.0–1.0) a labeler must answer correctly. Server default `0.75` |
| `min_tasks` | int \| None | Qualification tasks a labeler must complete before the accuracy verdict is trusted. Server default `10` |
| `max_tasks` | int \| None | Upper bound on admission-trial tasks before a verdict is forced. Default `None` (no cap) |

Supplying only one of the three is fine — the SDK fills the others in from the defaults (`0.75` / `10`). Passing none of them sends no graduation rule at all and lets the server default apply. Client-side `ValueError`s: `target_accuracy` outside `0.0..1.0`, `min_tasks < 1`, `max_tasks < min_tasks`.

## `RecruitingMetrics`

`audience.get_recruiting_metrics()` returns a frozen `RecruitingMetrics` dataclass (importable from the top-level `rapidata` package) — a snapshot of the recruiting funnel. All counts are zero for audiences that have not recruited anyone and for curated audiences.

| Field | Type | Meaning |
|-------|------|---------|
| `graduated` | int | Passed qualification, eligible to work now |
| `distilling` | int | Still going through qualification |
| `dropped` | int | Removed from the pool (score too low, limits hit, …) |
| `inactive` | int | Previously graduated/distilling, went quiet |

Buckets are mutually exclusive — each annotator is counted exactly once.

## Queueing jobs (`assign_job(..., run_after=...)`)

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

## Warnings on `assign_job`

The job is always created, but three advisory warnings may be logged afterwards:

- the estimated cost exceeds the account balance — the warning gives the estimate, the balance and the shortfall; the job runs as far as the balance allows (`python -m rapidata skill errors`, **Jobs under review or out of funds**);
- the explicit-content-check skip requested via `rapidata_config.upload.checkForExplicitContent = False` was denied by the account (the check still runs);
- the audience has **no graduated annotators yet** — the warning names the audience, how many are still distilling, and the job, and points at adding examples + `start_recruiting()`, or at using the `"global"` audience. Only `RapidataAudience` emits this; filtered audiences reuse their base pool.

## Examples

### Custom Audience with Full Workflow

```python
from rapidata import RapidataClient

client = RapidataClient()

# Create and train audience with diverse examples.
# The admission bar is optional: target_accuracy is the fraction of qualification
# tasks a labeler must get right (server default 0.75), min_tasks how many tasks
# before that verdict is trusted (default 10), max_tasks an optional cap after
# which a verdict is forced. Supplying just one is fine — the rest fall back to
# the defaults. start_recruiting() raises if fewer than min_tasks examples exist.
audience = client.audience.create_audience(
    name="Image Quality Experts",
    target_accuracy=0.8,
    min_tasks=3,
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

### Queueing Jobs on One Audience

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
