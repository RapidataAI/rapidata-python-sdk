# Error Handling

## Introduction

When creating job_definitions or orders with the Rapidata SDK, datapoints may fail to upload due to various reasons such as missing files, invalid formats, or network issues. Understanding how to handle these failures gracefully is essential for building robust integration.

When one or more datapoints fail to upload, the SDK raises a `FailedUploadException`. This exception provides detailed information about what went wrong and gives you several options for recovery:

- Inspect which datapoints failed and why
- Retry the failed datapoints
- Proceed with the `JobDefinition`/`Order` using only the successfully uploaded datapoints

This guide shows you how to handle upload failures effectively.

## Understanding FailedUploadException

The `FailedUploadException` is raised during job_definition or order creation when the SDK cannot upload one or more datapoints. Despite the exception, a job_definition or order object may still be created with the successfully uploaded datapoints.

### Key Properties

The exception provides three properties to help you understand and recover from failures:

- **`failed_uploads`**: List of datapoints that failed to upload
- **`detailed_failures`**: Dictionary mapping each failed datapoint to its error message
- **`failures_by_reason`**: Dictionary grouping datapoints by failure reason (useful for bulk analysis)

Additionally:
- **`job_definition`** or **`order`**: The created job_definition/order object

## Exception Properties Explained

### failed_uploads

A simple list of datapoints that failed:

```python
[Datapoint(asset=['https://assets.rapidata.ai/midjourney-5.2_37_3NOT_FOUND.jpg', 'https://assets.rapidata.ai/flux-1-pro_37_0.jpg'], data_type='media', context='A small blue book sitting on a large red book.', media_context=None, sentence=None, private_metadata=None, group=None)]
```

### detailed_failures

A list of FailedUpload objects, each containing the failed datapoint and its specific error message:

```python
[FailedUpload(item=Datapoint(asset=['https://assets.rapidata.ai/midjourney-5.2_37_3NOT_FOUND.jpg', 'https://assets.rapidata.ai/flux-1-pro_37_0.jpg'], data_type='media', context='A small blue book sitting on a large red book.', media_context=None, sentence=None, private_metadata=None, group=None), error_message='One or more required assets failed to upload', error_type='AssetUploadFailed', timestamp=datetime.datetime(2026, 2, 2, 15, 32, 30, 855335), exception=None)]
```

### failures_by_reason

Groups datapoints by their failure reason, making it easy to identify patterns:

```python
{
    'One or more assets failed to upload': [Datapoint(asset=['https://assets.rapidata.ai/midjourney-5.2_37_3NOT_FOUND.jpg', 'https://assets.rapidata.ai/flux-1-pro_37_0.jpg'], data_type='media', context='A small blue book sitting on a large red book.', media_context=None, sentence=None, private_metadata=None, group=None)],
}
```

## Strategy 1: Proceeding Without Failures

If you want to proceed with only the successfully uploaded datapoints, use the job_definition object from the exception:

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
    # Acceptable failure rate:
    if len(e.failed_uploads) > 10:
        raise ValueError("Too many failures, aborting")

    # Use the job that was created with successful datapoints
    job_def = e.job_definition
```

## Strategy 2: Retrying Failed Datapoints

If you want to retry the failed datapoints, you can use the `dataset` that is in the exception to retry the failed datapoints:

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
    print(f"{len(e.failed_uploads)} datapoints failed. Attempting to fix and retry...")
    successful_retries, failed_retries = e.dataset.add_datapoints(e.failed_uploads)
    print(f"{len(successful_retries)} datapoints successfully retried")
    print(f"{len(failed_retries)} datapoints failed to retry")
```

## Run Order after error occurred:

If you have already created an order and have not caught the exception, you can still run the order either through code or the app.rapidata.ai UI.

The order will run without the failed datapoints.

```python
from rapidata import RapidataClient

rapidata_client = RapidataClient()
order = rapidata_client.order.get_order_by_id(order_id)
order.run()
```
