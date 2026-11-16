# Comparison jobs and model-comparison templates

> Part of the Rapidata agent skill: `python -m rapidata skill comparison`. The **Task design rules** and **Key Gotchas** in the main guide (`python -m rapidata skill`) apply to everything here; parameters shared by every job type are in `python -m rapidata skill reference`.

## Templates: compare two image or video models in one call

**Comparing two image or video models? Suggest a template first.** Rapidata runs model comparisons for its own benchmarks and for customers, and templates are the setups that work for the most common cases. The user only brings the pairs, plus the prompts for alignment. Everything else is Rapidata's field-tested setup: the question, the annotators and 11 votes per pair. There is no audience or job definition to build, and none of the usual first-job mistakes (too few votes, a long question with several criteria, the wrong annotators).

| The user wants to know | Call | Annotators answer |
|---|---|---|
| Which model follows the prompt better? | `run_alignment`, with one prompt per pair | "Which image matches the description better?" (trained Alignment audience) |
| Which model do people like more? | `run_preference` | "Which image do you prefer?" (broad global crowd) |
| Which model makes fewer AI mistakes? | `run_coherence` | "Which image is more likely AI-generated?" (trained Coherence audience). The winner is the side that looks **more** AI-generated, so the better model wins fewer pairs |

For a full picture of two models, run all three. Build a job definition instead (below) only when the user needs something a template doesn't do: another question, more than two options, audio or text, their own audience, or a different number of votes. To rank three or more models, use a benchmark (`python -m rapidata skill benchmarks`).

```python
job = client.job.template.run_alignment(
    name="my-model vs flux-2",
    datapoints=[["mine/cat.png", "flux/cat.png"], ["mine/dog.png", "flux/dog.png"]],
    contexts=["A cat wearing a red scarf", "A dog surfing at sunset"],
    a_b_names=["my-model", "flux-2"],
)
job.get_results()["summary"]  # {'my-model_wins_total': …, 'flux-2_wins_total': …}
```

Images and videos (`.mp4`, `.gif`) both work; send them as separate calls.

```python
client.job.template.run_alignment(name, datapoints, *, contexts, a_b_names=None) -> RapidataJob
client.job.template.run_preference(name, datapoints, *, a_b_names=None) -> RapidataJob
client.job.template.run_coherence(name, datapoints, *, a_b_names=None) -> RapidataJob
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | str | 1–256 characters; the name of the job and of the job definition the call creates |
| `datapoints` | list[list[str]] | Pairs of file paths or URLs, `[[a, b], ...]`; 2 different files per pair, all images (`.jpg`, `.jpeg`, `.png`, `.webp`) or all videos (`.mp4`, `.gif`) |
| `contexts` | list[str] | `run_alignment` only, keyword-only: one prompt per pair. Keep prompts under 200 characters (the SDK warns above); prompts over 400 characters are shortened automatically, billed like `client.context` |
| `a_b_names` | list[str] \| None | Keyword-only: 2 different names for the first and second file of every pair, shown in the results instead of A and B |

Every pair gets 11 votes from the template's audience; there is no `responses_per_datapoint`, `settings` or audience to pass.

Errors:

- `ValueError` before anything is uploaded: images and videos mixed in one call, a pair that isn't 2 different files, a file that is neither an image nor a video, a missing or empty prompt, a bad `name` or `a_b_names`.
- `FailedUploadException`: some pairs failed to upload, and no job was started. Call the method again; `retry()` raises `RuntimeError` for template runs.
- `RapidataError` saying "… so a job may have started": Rapidata didn't confirm the start. Look for the job with `client.job.find_jobs(name)` before calling again; the message gives the exact job name and the time the call began. Other `RapidataError`s carry Rapidata's reason.
- `ApiException` (a network error): no job started, so calling the method again is safe.

Template runs ignore three upload settings: `contextShortening` (only prompts over 400 characters are shortened), `failureTolerance` (any failed pair stops the run) and `checkForExplicitContent` (your account decides the content check; the SDK warns when it is `True`).

## Create a comparison job definition

Compare two items and choose the better one.

```python
from rapidata import AdaptiveStopping

job_def = client.job.create_compare_job_definition(
    name="Image Comparison",
    instruction="Which image is higher quality?",
    datapoints=[["img_a1.jpg", "img_b1.jpg"], ["img_a2.jpg", "img_b2.jpg"]],
    data_type="media",
    responses_per_datapoint=AdaptiveStopping(),  # The default; see below
    contexts=["Prompt that generated these"],
    media_contexts=[["reference.jpg"]],
    a_b_names=["Model A", "Model B"],
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `datapoints` | list[list[str \| UploadedAsset]] | Pairs: `[["a1.jpg","b1.jpg"], ...]` |
| `a_b_names` | list[str] \| None | Custom labels for results, e.g. `["Model A","Model B"]` |

## Adaptive stopping (the compare default)

Compare jobs do not collect a fixed 10 responses by default: `AdaptiveStopping()` stops each pair at its first settled verdict. Pass an `int` (e.g. `responses_per_datapoint=10`) for a fixed count, or `QuorumStopping(threshold, max_responses)` (see `python -m rapidata skill classification`). Read `adaptiveStoppingState.verdict` (`Decided` / `Ambiguous` / `Undecided` / `Open`) rather than `winner` on adaptive results: `Ambiguous` means the pair is genuinely close, not that too few responses came in.

```python
from rapidata import AdaptiveStopping

job_def = client.job.create_compare_job_definition(
    name="Image Comparison",
    instruction="Which image is higher quality?",
    datapoints=[["a.jpg", "b.jpg"]],
    responses_per_datapoint=AdaptiveStopping(),   # same as omitting it
)
```

`AdaptiveStopping(max_responses=None, min_confidence=None, ambiguity_threshold=None)` — `None` uses the default (100 / 0.9 / 0.64); unset fields are left out of the request:

- Each response is weighted by the labeler's user score. The SDK only sends the parameters and passes the state through; never recompute it.
- After every response the pair gets a verdict once it is settled: `Decided` (a winner, wrong with probability below `1 - min_confidence`), `Ambiguous` (the true split lies inside the band, 20/80–80/20 by default), or `Undecided` at `max_responses`. A winner takes priority over ambiguous, so a 70/30 pair can still be `Decided`; the threshold only decides which pairs may stop as ambiguous.
- Unanimous pairs stop after 7 responses, 50/50 pairs at about 16, ~21 per pair on average, ~31 for the hardest pairs (split around 35/65). `max_responses` is a safety cap the defaults never reach (the longest possible run is under 80 responses) — don't tune it.
- `ambiguity_threshold` is a normalized Gini impurity: **higher is stricter**. raise it to resolve less decisive pairs: `0.75` resolves pairs down to a 75/25 split (about a third more responses on average, ~49 for the hardest pairs); `0.91` gives 35/65–65/35. The defaults are calibrated; change them only if you know why.
- `max_responses` must be a positive int; `min_confidence` and `ambiguity_threshold` in (0, 1), else `ValueError`.
- Raises `ValueError` on any job type other than compare, on create and on revisions, before anything is sent.
- For now there is no forecast for the expected response count, so cost estimates and progress use the `max_responses` setting per pair, which is well above the expected cost.

Each adaptive compare result gets `adaptiveStoppingState`:

```json
"adaptiveStoppingState": {
  "verdict": "Decided",
  "winners": ["1"],
  "outcomes": {
    "0": { "weight": 1.485, "lower": 0.004, "upper": 0.496 },
    "1": { "weight": 10.515, "lower": 0.504, "upper": 0.996 }
  },
  "responseCount": 12, "minConfidence": 0.9, "ambiguityThreshold": 0.64
}
```

- `outcomes` keys: `"0"` = first asset of the pair, `"1"` = second. `winners` holds those keys; non-empty only for `Decided`
- `verdict`: `Decided` · `Ambiguous` · `Undecided` (`outcomes` may be empty if every response was a skip) · `Open` (still collecting, or the job was paused or stopped first). The first non-`Open` verdict is frozen with its outcomes and `responseCount`
- `weight`: user-score-weighted responses, scaled to sum to `responseCount`. `lower`/`upper`: the range the option's long-run response share lies in with `min_confidence` certainty; it narrows with every response. Wholly above 0.5 → `Decided`; wholly inside the toss-up zone (~0.2–0.8 by default) → `Ambiguous`
- The key is absent (never `null`) on a datapoint without a state; read it with `.get()`. The value is passed through verbatim: unknown fields and `null` values are kept, and `verdict` may gain new values — don't validate it strictly. There is no `stoppingState` key
- `to_pandas()` flattens it into `adaptiveStoppingState_*` columns. Never recompute the verdict client-side

## Results

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
      "adaptiveStoppingState": {
        "verdict": "Decided", "winners": ["1"],
        "outcomes": { "0": { "weight": 2.4, "lower": 0.03, "upper": 0.48 }, "1": { "weight": 5.6, "lower": 0.52, "upper": 0.97 } },
        "responseCount": 8, "minConfidence": 0.9, "ambiguityThreshold": 0.64
      },
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

## Examples

### Template Run: Two Models, One Call

The quickest way to compare two models: Rapidata's field-tested setup, with only the pairs and prompts from the user.

```python
from rapidata import RapidataClient

client = RapidataClient()

job = client.job.template.run_alignment(
    name="flux vs midjourney, cats",
    datapoints=[
        ["flux_cat.jpg", "mj_cat.jpg"],
        ["flux_sunset.jpg", "mj_sunset.jpg"],
    ],
    contexts=["A cat on a chair", "A sunset over mountains"],
    a_b_names=["Flux", "Midjourney"],
)
results = job.get_results()
print(results["summary"])  # {'Flux_wins_total': …, 'Midjourney_wins_total': …}
```

`run_preference` and `run_coherence` take the same arguments without `contexts`. Pass `contexts` and `a_b_names` by keyword. Send image pairs and video pairs as separate calls.

### Comparison with Adaptive Stopping

Compare jobs stop each pair once its verdict is settled — `AdaptiveStopping()` is the default, so no stopping argument is needed.

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
    a_b_names=["Flux", "Midjourney"],
)
job = audience.assign_job(job_def)
job.view()
job.display_progress_bar()
results = job.get_results()

for datapoint in results["results"]:
    state = datapoint.get("adaptiveStoppingState")  # absent until the pair has a state
    if state is None:
        continue
    # verdict: "Decided" (winners holds "0" or "1"), "Ambiguous" (too close to call),
    # "Undecided" (hit max_responses) or "Open" (no verdict yet); may gain new values
    print(state["verdict"], state["winners"], state["responseCount"])
```

### Comparison Allowing "Neither" / "Both"

```python
from rapidata import RapidataClient, AllowNeitherBothSetting, LanguageFilter

client = RapidataClient()
audience = client.audience.get_audience_by_id("global").filter([LanguageFilter(["en"])])

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
