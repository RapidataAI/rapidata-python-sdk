# Shared job API reference

> Part of the Rapidata agent skill: `python -m rapidata skill reference`. The **Task design rules** and **Key Gotchas** in the main guide (`python -m rapidata skill`) apply to everything here.

Parameters, methods and result fields shared by every job type. Task-specific parameters and results are in each task's guide. Failed uploads and other errors: `python -m rapidata skill errors`. Context shortening and shared token files: `python -m rapidata skill settings`.

## Common job-definition parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | str | Job identifier (not shown to labelers) |
| `instruction` | str | Question shown to labelers: one criterion, under 80 characters (see **Task design rules** in the main guide). Over 250 characters raises `ValueError` |
| `datapoints` | list | Data to label: URLs, local paths, or `UploadedAsset` references from `client.asset.upload(...)`, which are never uploaded again |
| `data_type` | `"media"` \| `"text"` | `"media"` (default, covers image/video/audio) or `"text"`. **Text assets are NOT translated** unless `TranslateTextAssetsSetting` is added (source assumed English) — otherwise labelers see them verbatim |
| `responses_per_datapoint` | `int \| AdaptiveStopping \| QuorumStopping` | When to stop collecting per item. Compare default `AdaptiveStopping()` (~21 responses per pair on average, ~31 for the hardest pairs); other default `10`. An `int` is a fixed count (never below 10 — see **Task design rules** in the main guide). `AdaptiveStopping` is compare-only; `QuorumStopping(threshold, max_responses)` works on classification and compare. See **Stopping rules** below |
| `contexts` | list[str] \| None | Text context per datapoint: one sentence under 150 characters with only what the instruction asks about (see **Task design rules** in the main guide). Max 400 characters each; contexts over the limit are always shortened against the instruction before upload — set `rapidata_config.upload.contextShortening = True` to shorten every context, or use `client.context` to shorten manually |
| `media_contexts` | list[list[str \| UploadedAsset]] \| None | Reference images per datapoint; each entry is a list of at most 10 image URLs/paths/`UploadedAsset` references (one inner list per datapoint). Shown in a collapsible drawer unless `PinContextMediaSetting` is added (only when there is enough space — check the preview); for a compare of two image edits, `ReferenceOverlaySetting` lays a single image context over both options instead |
| `confidence_threshold` | float \| None | **Deprecated** (`DeprecationWarning`). Confidence-based early stopping threshold (0-1); needs an `int` `responses_per_datapoint` as the cap (when omitted: 15 on compare jobs, 10 otherwise). Use adaptive stopping on compare jobs |
| `quorum_threshold` | int \| None | **Deprecated** (`DeprecationWarning`) — use `responses_per_datapoint=QuorumStopping(threshold, max_responses)`. Needs an `int` `responses_per_datapoint` as the cap (when omitted: 15 on compare jobs, 10 otherwise); cannot combine with `confidence_threshold` |
| `settings` | `Sequence[RapidataSetting] \| None` | Display/behavior settings |
| `failure_tolerance` | float \| None | Fraction of datapoints (0.0–1.0) allowed to fail upload while the definition is still created; `None` falls back to `rapidata_config.upload.failureTolerance` (default `0.0` = strict). See `python -m rapidata skill errors` |
| `private_metadata` | `list[dict[str, str]] \| None` | Hidden metadata per datapoint |

`instruction` is capped at 250 characters (`Workflow.MAX_INSTRUCTION_LENGTH`) for every job definition type and for every audience qualification example. Over-long values raise `ValueError: instruction is <n> characters; maximum is 250` at construction time. This is a hard cap, not a target: write instructions under 80 characters (see **Task design rules** in the main guide).

## Upload once, reuse the reference

`client.asset.upload(path_or_url)` uploads a local file or URL and returns an `UploadedAsset`. Every `create_*_job_definition` and `set_datapoints` accepts it wherever it takes a media datapoint or media context, alone or mixed with paths and URLs, and uses it as-is: it is never uploaded again.

```python
from rapidata import UploadedAsset

baseline = client.asset.upload("baseline.png")  # UploadedAsset(name='<uuid>.png')
job_def = client.job.create_compare_job_definition(
    name="Baseline vs candidates",
    instruction="Which image looks better?",
    datapoints=[[baseline, "candidate_1.png"], [baseline, "https://example.com/candidate_2.png"]],
)

saved_name = baseline.name               # keep the name to reuse this upload later,
baseline = UploadedAsset(saved_name)     # e.g. in another session
```

An `UploadedAsset` is media, so it cannot be a `data_type="text"` datapoint. Audience examples, validation sets, flows and benchmarks still take paths and URLs only.

## Finding, editing and managing job definitions and jobs

**Looking up existing jobs (`client.job`):** `get_job_definition_by_id(id, revision=None)` (latest revision by default), `find_job_definitions(name="", amount=10, page=1)`, `get_job_by_id(id)`, `find_jobs(name="", amount=10, page=1)`.

**Job / Job Definition methods:**
- `job_def.preview()` — open browser preview of what labelers see
- **Editing a job definition** — a `RapidataJobDefinition` holds one revision (`job_def.revision`; `create_*_job_definition` returns revision 1). Assigning `job_def.instruction`, `.answer_options` (classification only; one list for every datapoint), `.responses_per_datapoint` (an `int`, `AdaptiveStopping` (compare only) or `QuorumStopping`; reading returns the same kinds), `.settings` (replaces every setting) or `.validation_set_id` (None clears it) only stages the change. `job_def.save()` sends the whole revision in one request and returns the new revision number; the object moves to it. See the **Editing a Job Definition** example below
- `job_def.set_datapoints(datapoints=..., data_type=..., contexts=..., media_contexts=..., sentences=..., private_metadata=..., answer_options=...)` — upload a new dataset now and stage it for `save()`; raises `FailedUploadException` (nothing staged) if any datapoint fails. Pass `answer_options` for classification definitions whose options are set per datapoint. `update_dataset(...)` still works but is deprecated: it is `set_datapoints(...)` + `save()`
- `job_def.has_unsaved_changes`, `job_def.discard_changes()`, `job_def.reload(revision=None)` (raises while changes are unsaved), `job_def.revisions()` (list of `RevisionInfo`: `revision`, `base_revision`, `state`, `created_at`), `job_def.state` (`Pending` until the new revision's preview is built, then `Completed` / `Failed`), `job_def.wait_until_ready(timeout=300)`
- `job_def.estimated_cost` / `job.estimated_cost` — a `CostEstimate` (`estimated_cost`, `datapoint_count`, `required_responses`) for running to completion; available on a job definition *before* assigning it. The estimate is priced shortly after creation, so the first read blocks briefly until it's ready (raises `TimeoutError` if still unavailable after a few minutes), then caches. It's an estimate, not the final bill — early stopping can lower the actual cost. For adaptive compare jobs, for now there is no forecast for the expected response count, so the estimate uses the `max_responses` setting per pair, which is well above the expected cost.
- `job_def.delete()` — delete a job definition and all its revisions
- `job.display_progress_bar(refresh_rate=5)` — blocking progress bar
- `job.get_status()` — current status string
- `job.get_progress()` — non-blocking snapshot: a `JobProgress` with `state` (same value as `get_status()`), `completion_percentage` (0–100) and `recruiting` (a `RecruitingMetrics`, or `None` for curated audiences)
- `job.get_results(preliminary_results=False)` — with `preliminary_results=True` on an unfinished job, returns a snapshot of the responses collected so far without waiting (not final, may miss datapoints); on a completed job it returns the final results. Otherwise blocks until Completed/Failed (auto-regenerates if `StaleResults`), returns `RapidataResults`. If the job needs manual review (`ManualApproval`), runs out of funds mid-run (`SpendLimited`), is paused (`Paused`) or is blocked by a flagged rapid (`Blocked`) — none of these completes on its own — it raises an informative error naming the state instead of blocking; top up, wait for a reviewer, `resume()` or unflag the rapid on `job.job_details_page`, then call it again. It also raises up front when the job's audience **can never produce responses** (nobody graduated *and* nobody is being recruited); an audience that is merely still distilling does not raise.
- `job.pause()` / `job.resume()` — stop collecting responses / continue; both return the job. While `Paused`, `get_results()` and `display_progress_bar()` raise instead of blocking
- `job.view()` — open the job's details page in the browser
- `job.delete()` — delete a running job

## Stopping rules (`responses_per_datapoint`)

The stopping rule is the value of `responses_per_datapoint`:

| Value | Rule | Job types |
|-------|------|-----------|
| `AdaptiveStopping()` | Stop each pair at its first settled verdict. **Compare default** | Compare |
| `QuorumStopping(threshold, max_responses)` | Stop once `threshold` responses agree | Classification, Compare |
| `int` | Exactly that many responses. Default `10` for all other job types | All |

Adaptive stopping details: `python -m rapidata skill comparison`. Quorum stopping details: `python -m rapidata skill classification`.

### Deprecated `quorum_threshold` and `confidence_threshold`

Both emit a `DeprecationWarning` on every job type. Replace `quorum_threshold=7, responses_per_datapoint=10` with `responses_per_datapoint=QuorumStopping(7, 10)`, and `confidence_threshold` with adaptive stopping (the default) on compare jobs or `QuorumStopping` / a fixed count on classification. They still work with an `int` `responses_per_datapoint` as the cap.

They cannot be set together and raise `ValueError` combined with `AdaptiveStopping` or `QuorumStopping`. On a compare job with the default left in place, they use a cap of 15.

### Reading and editing the rule

`job_def.responses_per_datapoint` returns an `int`, `AdaptiveStopping` or `QuorumStopping` (a legacy `confidence_threshold` definition returns its cap as an `int`). Assigning `AdaptiveStopping` or `QuorumStopping` replaces the rule on `save()`; assigning an `int` sets a fixed count, except on a legacy `confidence_threshold` definition, where it changes the cap.

## Results: shared fields

Every job type returns `{"info": {type, name, instruction, version, createdAt}, "results": [...], "summary"?}`. What one `results` entry is, and where each labeler's answer sits in its `detailedResults`:

| Job type (`info.type`) | One `results` entry | Aggregate fields | Answer in `detailedResults[]` | `summary` |
|---|---|---|---|---|
| `Classification` | one datapoint | `aggregatedResults` (votes per option), `summedUserScores` (+ `…Ratios`) | `selectedCategory` | votes per option |
| `Compare` | one pair | `winner`/`winnerIndex`, `weightedWinner`, `aggregatedResults`, `summedUserScores`, `adaptiveStoppingState` | `votedFor` | `A_wins_total`/`B_wins_total` |
| `Ranking` | **one ranking** (`group` = its index in `datapoints`) | `summary`: datapoint → Elo score; `results`: its matchups, each shaped like a Compare pair | `votedFor` (inside each matchup) | none at top level |
| `Locate` | one datapoint | `aggregatedResults`: every tapped `{x, y}` (percent of width/height), `notApplicable` | `locations` | none |
| `Draw` | one datapoint | `aggregatedResults`: every `{size, points}` line, `notApplicable` | `lines` | none |
| `SelectWords` | one datapoint | `sentence`, `aggregatedResults`: `{word, wordIndex, selectedAmount}` per word | `selectedWords` | none |
| `FreeText` | one datapoint | `aggregatedResults`: list of answers | `answerText` | none |

Datapoint entries carry `identifier` (your URL, file name or text — join on it), `assetUrl`, and `context` / `privateMetadata` when set. Full examples are in each task's guide.

Datapoint-based results (all but Comparison and Ranking) carry `context`, `mediaContext` and `privateMetadata` when you set them; keys that don't apply are omitted rather than `null`.

| Field | Meaning |
|-------|---------|
| `info.type` / `info.name` / `info.instruction` | Task type (`Classification`, `Compare`, `Ranking`, `Locate`, `Draw`, `SelectWords`, `FreeText`), the job name, and the instruction shown to labelers |
| `assetUrls` | Maps each option to the Rapidata-hosted URL of the exact file shown to labelers (random-UUID filenames; not encrypted) |
| `winner` | Most-voted option by raw vote count (`argmax` of `aggregatedResults`); `null` when nothing was voted or the top count is tied |
| `winnerIndex` | Position of `winner` in the ordered option list (`0` = first asset, `1` = second; `Both`/`Neither` appear as trailing indexes when voted); `null` under the same conditions as `winner` |
| `weightedWinner` / `weightedWinnerIndex` | Reliability-weighted winner (`argmax` of `summedUserScores`) and its index, same index space and `null`-on-tie behavior. Can differ from `winner` on close votes |
| `winner_index` | **Deprecated** alias of `winnerIndex`, kept for backwards compatibility; will be removed in a future release |
| `aggregatedResults` | Raw vote counts |
| `aggregatedResultsRatios` | Vote percentages |
| `summedUserScores` | Per-option sum of each choosing labeler's aggregated `userScore` |
| `summedUserScoresRatios` | `summedUserScores` normalized to sum to 1 |
| `confidencePerCategory` | Confidence level per category (with `confidence_threshold`) |
| `adaptiveStoppingState` | Adaptive stopping only (the compare default): the `verdict`, `winners` (`"0"`/`"1"`), per-option `outcomes` (`weight`, `lower`, `upper`), `responseCount` and the parameters used. Absent on non-adaptive datapoints. Prefer it over `winner` on adaptive results — see `python -m rapidata skill comparison` |
| `userScore` | 0-1 value indicating individual labeler reliability |

A labeler's `demographics` may be empty when no demographic data was collected for them.

`winnerIndex`, `weightedWinner` and `weightedWinnerIndex` are only emitted by aggregator version `4.1.0`+ (`info.version`); results produced by older versions carry only `winner` and `winner_index`.

### Working with results

```python
results = job.get_results()              # RapidataResults — a dict subclass holding the raw JSON
snapshot = job.get_results(preliminary_results=True)  # unfinished job: responses so far, no waiting
df = results.to_pandas()                  # one row per datapoint; compare results get A_/B_ columns,
                                          # classification gets one row per datapoint and answer option,
                                          # ranking one row per ranked datapoint (group, datapoint, score, rank)
df = results.to_pandas(split_details=True)  # one row per individual response (ranking: per matchup response)
results.to_json("results.json")           # writes the file (default "./results.json"); returns None
```

Flow items have a different result shape: `python -m rapidata skill flows`.

## Job progress

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

## Examples

### Editing a Job Definition

```python
job_def = client.job.get_job_definition_by_id("job_definition_id")
job_def.instruction = "Which image looks more realistic?"
job_def.save()                      # creates a new revision; job_def now holds it

job = audience.assign_job(job_def)  # runs job_def.revision
```

### Checking Job Progress Without Blocking

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
