# Error Handling

## Introduction

When creating job definitions with the Rapidata SDK, datapoints may fail to upload for various reasons such as missing files, invalid formats, or network issues. Understanding how to handle these failures is essential for building robust integrations.

Job creation is **atomic by default**: if any datapoint fails to upload, the SDK does **not** create the job definition — so you never end up with an incomplete definition — and raises a `FailedUploadException`. You then fix the problem and call `exception.retry()`, which re-uploads only the failed datapoints into the **same** dataset and finishes creating the definition. Retrying never creates a duplicate dataset or definition.

If you would rather tolerate a small fraction of failures instead, raise the [failure tolerance](#failure-tolerance).

## Failure tolerance

`failure_tolerance` is the fraction of a job's datapoints (`0.0`–`1.0`) allowed to fail while still creating the definition:

- `0.0` (default) — strict. Any failed upload aborts creation; no definition is left behind and the failed datapoints can be retried.
- `0.01` — up to 1% of datapoints may fail; the definition is created with the rest, and the failures are logged.
- `1.0` — the definition is created regardless of how many datapoints failed, as long as at least one datapoint uploads successfully (a definition over an empty dataset is never created).

Set it globally, via the config object or the `RAPIDATA_failureTolerance` environment variable:

```python
from rapidata import rapidata_config
rapidata_config.upload.failureTolerance = 0.01
```

or per call, which overrides the global default for that job:

```python
job_def = client.job.create_classification_job_definition(
    name="Image Classification",
    instruction="What animal is in this image?",
    answer_options=["Cat", "Dog", "Bird"],
    datapoints=["cat1.jpg", "dog1.jpg", "missing.jpg"],
    failure_tolerance=0.01,
)
```

The ratio is measured against the whole job, so it stays meaningful across retries.

## Understanding FailedUploadException

The `FailedUploadException` is raised during job-definition creation when the upload stays outside the failure tolerance. When it comes from job creation, no job definition was created — recover with `exception.retry()` (see below).

### Exception Properties

The exception exposes these to help you understand and recover from failures:

- `dataset` — the dataset that was being uploaded to. `retry()` reuses it.
- `failed_uploads` / `detailed_failures` / `failures_by_reason` — which datapoints failed and why (see below).
- `retry()` — re-upload the failed datapoints into `dataset` and finish creating the definition. Returns the `RapidataJobDefinition`.
- `job_definition` — `None` for job creation (nothing was persisted). Populated only when tolerating failures on a legacy order.

### Understanding Failure Information

The exception provides two ways to inspect failures, depending on your needs:

#### `detailed_failures` - Full Error Details

Use this when you need complete information about each failure, including error type, timestamp, and the original exception:

```python
exception.detailed_failures
# Returns: list[FailedUpload[Datapoint]]
```

Each `FailedUpload` object contains:

- `item`: The datapoint that failed
- `error_message`: Human-readable explanation of what went wrong
- `error_type`: The type of error (e.g., "AssetUploadFailed", "RapidataError")
- `timestamp`: When the failure occurred
- `exception`: The original exception (if available)
- `stage`: For remote-URL assets, the ingestion stage that failed — one of `download`, `redirect`, `content_type`, `decode`, `timeout`, `size`, `validation`, or `internal`. Only `internal` is a Rapidata-side fault; every other stage is caller-actionable (e.g. a bad URL, an unreachable host, an unsupported content type). `None` for local-file or datapoint-creation failures.
- `http_status`: For a failed remote URL, the origin server's HTTP status (e.g. `403` when the asset host forbids access). `None` when the failure wasn't an HTTP response from the host.

**Example:**
```python
[
    FailedUpload(
        item=Datapoint(asset=['missing.jpg', 'valid.jpg'], ...),
        error_message='One or more required assets failed to upload',
        error_type='AssetUploadFailed',
        timestamp=datetime(2026, 2, 2, 15, 32, 30),
        exception=None
    )
]
```

#### `failures_by_reason` - Grouped by Error Type

Use this when you want to identify patterns and handle different failure types differently:

```python
exception.failures_by_reason
# Returns: dict[str, list[Datapoint]]
```

This groups all failed datapoints by their error message, making it easy to see common issues at a glance.

**Example:**
```python
{
    'One or more required assets failed to upload': [
        Datapoint(asset=['missing1.jpg', 'valid.jpg'], ...),
        Datapoint(asset=['missing2.jpg', 'valid.jpg'], ...)
    ],
    'Invalid datapoint format': [
        Datapoint(asset=['test.jpg'], ...)
    ]
}
```

#### `failures_by_stage` - Grouped by Ingestion Stage

Use this when your datapoints are **remote URLs** and you want to know *which stage* of ingestion failed rather than reading messages. It groups the failed datapoints by their `stage` (see the field list above); datapoints without a stage (local files, datapoint-creation failures) are omitted.

```python
exception.failures_by_stage
# Returns: dict[str, list[Datapoint]]
```

**Example:**
```python
{
    'download': [  # the host returned a non-2xx (check http_status on the FailedUpload)
        Datapoint(asset=['https://host/a.jpg'], ...)
    ],
    'content_type': [  # the URL served a type that isn't a supported asset
        Datapoint(asset=['https://host/page.html'], ...)
    ]
}
```

Because only `internal` is a Rapidata-side fault, this makes it easy to separate URLs you need to fix from the rare failure worth reporting to us.

### Types of Failures

**Asset Upload Failures**: When assets (images, videos, etc.) fail to upload, all affected datapoints will have the same error message: `"One or more required assets failed to upload"`. This happens before datapoint creation begins. For **remote-URL** assets the failure additionally carries a `stage` and, where applicable, an origin `http_status` — inspect these (or `failures_by_stage`) to see whether the URL was unreachable, forbidden, the wrong content type, too large, or timed out.

**Datapoint Creation Failures**: After assets are successfully uploaded, datapoints are created. These failures can have different reasons depending on what went wrong (e.g., validation errors, format issues, backend constraints). Each datapoint may fail for a unique reason.

## Recovery

### Fix and retry

The recommended recovery path is to catch the exception, fix whatever caused the failures (for example correct the file paths), and call `exception.retry()`. This re-uploads **only** the failed datapoints into the **same** dataset and finishes creating the definition — no new dataset, no duplicate definition, and nothing to re-specify:

```python
from rapidata import RapidataClient
from rapidata.rapidata_client.exceptions import FailedUploadException

client = RapidataClient()

try:
    job_def = client.job.create_classification_job_definition(
        name="Image Classification",
        instruction="What animal is in this image?",
        answer_options=["Cat", "Dog", "Bird"],
        datapoints=["cat1.jpg", "dog1.jpg", "missing.jpg"],
    )
except FailedUploadException as e:
    for reason, datapoints in e.failures_by_reason.items():  # (1)!
        print(f"  {reason}: {len(datapoints)} datapoints")

    # ...fix the failing datapoints (e.g. correct the paths on disk)...
    job_def = e.retry()  # (2)!

audience = client.audience.get_audience_by_id("global")
job = audience.assign_job(job_def)
```

1. Inspect what failed and why before retrying.
2. Returns the created `RapidataJobDefinition`. If some datapoints still fail beyond the tolerance, `retry()` raises `FailedUploadException` again (with the same dataset attached), so you can keep fixing and retrying.

!!! warning
    Don't re-call `create_*_job_definition(...)` to retry — that starts a fresh dataset and creates a **second** definition. Use `exception.retry()` so the existing dataset is reused.

### Tolerate a fraction of failures

If a few failures are acceptable, set a [failure tolerance](#failure-tolerance). When the failed fraction is within tolerance the definition is created with the datapoints that succeeded, the failures are logged, and no exception is raised:

```python
job_def = client.job.create_classification_job_definition(
    name="Image Classification",
    instruction="What animal is in this image?",
    answer_options=["Cat", "Dog", "Bird"],
    datapoints=["cat1.jpg", "dog1.jpg", "missing.jpg"],
    failure_tolerance=0.5,  # tolerate up to 50% failures for this job
)
```

### Manual control (advanced)

`exception.retry()` covers the common case. If you need to drive the retry yourself — for example to substitute corrected datapoints — the failed dataset is available on the exception and you can add datapoints to it directly:

```python
except FailedUploadException as e:
    successful_retries, failed_retries = e.dataset.add_datapoints(e.failed_uploads)
```

Note that this only re-uploads the datapoints; it does not create the job definition. Prefer `exception.retry()` unless you specifically need the lower-level control.

## Too many open files

If uploads fail with `OSError: [Errno 24] Too many open files`, the process has hit its file-descriptor limit — the upload cache, worker pool, and HTTP connections all consume descriptors. When the SDK detects this it appends a hint to the `FailedUploadException` message pointing at the relevant knobs.

Raise the OS limit (`ulimit -n 8192`), lower the SDK's footprint with `RAPIDATA_cacheShards` / `RAPIDATA_maxWorkers`, or turn the disk cache off entirely with `cacheToDisk=False` (no cache descriptors at all, at the cost of cross-run upload dedup). See [Too many open files](config.md#too-many-open-files) in the configuration guide for details.
