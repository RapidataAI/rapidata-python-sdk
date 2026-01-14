# Migration Guide: Orders to Audiences

This guide helps you migrate from the legacy Order API to the recommended Audience & Job API.

> **Note:** The Order and Validation APIs (`client.order`, `client.validation`) remain available for backwards compatibility in the near term

## Side-by-Side Comparison

### Legacy: Orders

```python
from rapidata import RapidataClient

client = RapidataClient()

# Step 1: Create validation set with quality control examples
validation_set = client.validation.create_compare_set(
    name="Image Comparison Validation",
    instruction="Which image follows the prompt better?",
    datapoints=[["good_example.jpg", "bad_example.jpg"]],
    truths=["good_example.jpg"],
    contexts=["A sign that says 'Diffusion'."]
)

# Step 2: Create order with validation set reference
order = client.order.create_compare_order(
    name="Prompt Alignment Comparison",
    instruction="Which image follows the prompt better?",
    datapoints=[
        ["flux_image.jpg", "midjourney_image.jpg"],
        ["flux_image2.jpg", "midjourney_image2.jpg"]
    ],
    contexts=["A cat on a chair", "A sunset over mountains"],
    validation_set_id=validation_set.id,
    responses_per_datapoint=10
)

# Step 3: Run and get results
order.run()
results = order.get_results()
```

### New: Audiences & Jobs

```python
from rapidata import RapidataClient

client = RapidataClient()

# Step 1: Create audience with qualification examples built-in
audience = client.audience.create_audience(name="Prompt Alignment Judges")
audience.add_compare_example(
    instruction="Which image follows the prompt better?",
    datapoint=["good_example.jpg", "bad_example.jpg"],
    truth="good_example.jpg",
    context="A sign that says 'Diffusion'."
)

# Step 2: Create job definition
job_definition = client.job.create_compare_job_definition(
    name="Prompt Alignment Comparison",
    instruction="Which image follows the prompt better?",
    datapoints=[
        ["flux_image.jpg", "midjourney_image.jpg"],
        ["flux_image2.jpg", "midjourney_image2.jpg"]
    ],
    contexts=["A cat on a chair", "A sunset over mountains"],
    responses_per_datapoint=10
)

# Step 3: Assign and get results
job = audience.assign_job(job_definition)
results = job.get_results()
```

## What Changed

| Legacy | Recommended | Notes |
|--------|-------------|-------|
| `client.order.create_*_order()` | `client.job.create_*_job_definition()` | Same parameters |
| `client.validation.create_*_set()` | `audience.add_*_example()` | Simpler API |
| `validation_set_id` parameter | Not needed | Built into audience |
| `filters` parameter | `filters` on audience creation | Applied at audience level |
| `order.run()` | `audience.assign_job(job_def)` | Automatic |

## Key Benefits

- **Simpler**: No separate validation set management
- **Reusable**: One audience can run multiple jobs or a job on multiple audiences
- **Previewable & Editable**: `job_definition.preview()` before assigning
- **Result Alignment**: The labelers in an audience are filtered according to your examples, improving the quality of the results

## Quick Reference

**Classification:**

- `create_classification_order()` → `create_classification_job_definition()`
- `create_classification_set()` → `audience.add_classification_example()`

**Compare:**

- `create_compare_order()` → `create_compare_job_definition()`
- `create_compare_set()` → `audience.add_compare_example()`

Results work the same way: `results.to_pandas()`, `results.to_json()`
