# Errors and failed uploads

> Part of the Rapidata agent skill: `python -m rapidata skill errors`. The **Task design rules** and **Key Gotchas** in the main guide (`python -m rapidata skill`) apply to everything here.

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

## Example

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
