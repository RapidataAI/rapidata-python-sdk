# Error Handling

## Introduction

When creating job definitions or orders with the Rapidata SDK, datapoints may fail to upload due to various reasons such as missing files, invalid formats, or network issues. Understanding how to handle these failures is essential for building robust integrations.

When one or more datapoints fail to upload, the SDK raises a `FailedUploadException`. This exception provides detailed information about what went wrong and gives you several recovery options:

- Inspect which datapoints failed and why
- Retry the failed datapoints
- Continue with the successfully uploaded datapoints

This guide shows you how to handle upload failures effectively.

## Understanding FailedUploadException

The `FailedUploadException` is raised during `JobDefinition` or `Order` creation when one or more datapoints cannot be uploaded. 
**Important**: Despite the exception being raised, a `JobDefinition` or `Order` object is still created with the successfully uploaded datapoints, allowing you to continue if you catch the exception.

### Exception Properties

The exception provides these properties to help you understand and recover from failures:

```python
FailedUploadException(
    dataset: RapidataDataset, # (1)!
    failed_uploads: list[FailedUpload], # (2)!
    order: Optional[RapidataOrder], # (3)!
    job_definition: Optional[JobDefinition] # (4)!
)
```

1. The dataset that was being created.
2. Basic list of failed datapoints.
3. The order object (only present during order creation).
4. The job definition object (only present during job definition creation).

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

### Types of Failures

**Asset Upload Failures**: When assets (images, videos, etc.) fail to upload, all affected datapoints will have the same error message: `"One or more required assets failed to upload"`. This happens before datapoint creation begins.

**Datapoint Creation Failures**: After assets are successfully uploaded, datapoints are created. These failures can have different reasons depending on what went wrong (e.g., validation errors, format issues, backend constraints). Each datapoint may fail for a unique reason.

## Recovery Strategies

### Strategy 1: Continue with Successfully Uploaded Datapoints

When a `FailedUploadException` is raised, the `JobDefinition` or `Order` is still created with the successfully uploaded datapoints. You can catch the exception and continue using the created object:

**For Job Definitions:**
```python
from rapidata import RapidataClient
from rapidata.rapidata_client.exceptions import FailedUploadException

client = RapidataClient()

try:
    job_def = client.job.create_classification_job_definition(
        name="Image Classification",
        instruction="What animal is in this image?",
        answer_options=["Cat", "Dog", "Bird"],
        datapoints=["cat1.jpg", "dog1.jpg", "missing.jpg"]
    )
except FailedUploadException as e:
    print(f"Warning: {len(e.failed_uploads)} datapoints failed to upload")

    if len(e.failed_uploads) > len(datapoints) * 0.1: # (1)!
        raise ValueError("Too many failures, aborting")

    job_def = e.job_definition # (2)!
```

1. Check if the failure rate is acceptable — here we abort if more than 10% failed.
2. The job definition was still created with the successfully uploaded datapoints. You can use it normally.

**For Orders:**
```python
from rapidata import RapidataClient
from rapidata.rapidata_client.exceptions import FailedUploadException

client = RapidataClient()

try:
    order = client.order.create(
        name="Image Classification Order",
        instruction="What animal is in this image?",
        answer_options=["Cat", "Dog", "Bird"],
        datapoints=["cat1.jpg", "dog1.jpg", "missing.jpg"]
    )
except FailedUploadException as e:
    print(f"Warning: {len(e.failed_uploads)} datapoints failed")

    order = e.order # (1)!
    order.run()
```

1. The order was still created with the successfully uploaded datapoints.

### Strategy 2: Retry Failed Datapoints

After catching the exception, you can fix the issues (e.g., correct file paths, fix formats) and retry the failed datapoints by adding them to the dataset:

```python
from rapidata import RapidataClient
from rapidata.rapidata_client.exceptions import FailedUploadException

client = RapidataClient()

try:
    job_def = client.job.create_classification_job_definition(
        name="Image Classification",
        instruction="What animal is in this image?",
        answer_options=["Cat", "Dog", "Bird"],
        datapoints=["cat1.jpg", "dog1.jpg", "missing.jpg"]
    )
except FailedUploadException as e:
    print(f"{len(e.failed_uploads)} datapoints failed:")
    for reason, datapoints in e.failures_by_reason.items():
        print(f"  {reason}: {len(datapoints)} datapoints")

    successful_retries, failed_retries = e.dataset.add_datapoints(e.failed_uploads) # (1)!
    print(f"{len(successful_retries)} datapoints successfully added on retry")

    if failed_retries:
        print(f"{len(failed_retries)} datapoints still failed after retry")
```

1. Fix the underlying issues (e.g., correct file paths) before retrying. This adds the previously failed datapoints back to the dataset.

### Strategy 3: Retrieve and Use After Exception (If Not Caught)

If you didn't catch the exception during creation, you can still retrieve and use the job definition or order. They were created with the successfully uploaded datapoints and can be used through code or the app.rapidata.ai UI:

**For Orders:**
```python
from rapidata import RapidataClient

client = RapidataClient()

order = client.order.get_order_by_id(order_id) # (1)!
order.run()
```

1. Retrieve the order using its ID (from the exception message or the [Rapidata Dashboard](https://app.rapidata.ai)).

**For Job Definitions:**
```python
from rapidata import RapidataClient

client = RapidataClient()

job_def = client.job.get_job_definition_by_id(job_definition_id) # (1)!
audience.assign_job(job_def)
```

1. Retrieve the job definition using its ID (from the exception message or the [Rapidata Dashboard](https://app.rapidata.ai)).
