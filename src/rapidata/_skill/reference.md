# Shared job API reference

> Part of the Rapidata agent skill: `python -m rapidata skill reference`. The **Task design rules** and **Key Gotchas** in the main guide (`python -m rapidata skill`) apply to everything here; parameters shared by every job type are in `python -m rapidata skill reference`.

Parameters, methods, errors and configuration shared by every job type. Task-specific parameters and results are in each task's guide.

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
| `failure_tolerance` | float \| None | Fraction of datapoints (0.0–1.0) allowed to fail upload while the definition is still created; `None` falls back to `rapidata_config.upload.failureTolerance` (default `0.0` = strict). See Error Handling |
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

## Error handling

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

Some jobs don't go straight to running. A job can enter manual review (`ManualApproval`) or, once out of funds mid-run, become spend-limited (`SpendLimited`); a job you paused with `job.pause()` sits in `Paused`; a job with a flagged rapid sits in `Blocked` until that rapid is inspected and unflagged on the job's page in the app (`job.job_details_page`). None of these completes on its own, so `get_results()` raises an informative error naming the state (and the review reason, when available) instead of blocking indefinitely — top up, wait for a reviewer, call `job.resume()` or unflag the rapid, then call it again.

### Jobs on an audience that can never respond

`get_results()` and `display_progress_bar()` also raise up front when the job's audience can never produce responses — nobody graduated **and** nobody is being recruited (recruiting was never started, or the audience is `Ready` with an empty pool). This catches the case where `start_recruiting()` was forgotten, instead of blocking forever at 0 responses.

An audience that is still distilling, an audience in `Pending`/`Recruiting`, a curated audience, or a failed metrics read do **not** raise — those can still deliver responses.

## Context management

Write contexts as one sentence under 150 characters (**Task design rules**, rule 3, in the main guide); shortening is a fallback, not a substitute, and rarely gets a context under 150 characters. Datapoint contexts have a backend maximum of **400 characters** (`MAX_CONTEXT_LENGTH`) and the backend rejects longer ones, so any context over 400 characters is **always** shortened against the task instruction before upload. This cannot be turned off. A warning reports how many contexts were shortened, per-context before/after lengths are logged at info level, and if shortening returns an empty result the original context is kept and a warning is logged.

A context tuned to the question focuses the labeler even when it already fits the limit. Set `rapidata_config.upload.contextShortening = True` (default `False`) to have **every** context shortened, not just the over-long ones:

```python
from rapidata import rapidata_config

rapidata_config.upload.contextShortening = True
```

Shorten contexts directly, without creating a job, via `client.context` (a `ContextManager`, also importable directly: `from rapidata import ContextManager`):

- `client.context.shorten_context(context, question) → str`: shorten a single context for the given question. Results are cached server-side.
- `client.context.shorten_contexts(pairs) → list[str]`: shorten a batch of `(context, question)` pairs, returned in the same order. Batches of ≤10 pairs go out as a single request; larger batches are split into chunks of 10 and sent concurrently using `rapidata_config.upload.maxWorkers`, with a `Shortening contexts` progress bar (suppressed by `rapidata_config.logging.silent_mode`).

```python
short = client.context.shorten_context(
    context="<a very long description ...>",
    question="Does the main character wear the right clothing?",
)
shortened = client.context.shorten_contexts([
    (context_a, question_a),
    (context_b, question_b),
])
```

## Shared token files (distributed training)

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

The token file contains a bearer token: write it only to storage your job alone can access. The SDK reads the token at startup and re-reads the file whenever the in-memory token is within `leeway` of expiry. Whatever the transport, pass the complete token object around and keep its absolute `expires_at` field. On older SDKs without `token_file`, pass the token dict directly with `RapidataClient(token=json.load(f))`; the SDK never re-reads it, so each worker must call `set_token()` (or construct a new client) when the token expires.

## Examples

### Handling Failed Uploads

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

### Sharing a Token Across Workers (Distributed Training)

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
