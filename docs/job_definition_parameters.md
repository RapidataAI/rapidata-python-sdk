# Job Definition Parameter Reference

This guide provides a comprehensive reference for all parameters available when creating job definitions in the Rapidata Python SDK.

## Overview

When creating a job definition, you'll use parameters to control:

- **What data** is shown to labelers (datapoints, contexts)
- **How many responses** you need (responses_per_datapoint)
- **How tasks are displayed** (settings)
- **Quality assurance** (confidence_threshold)

---

## Core Parameters

These parameters are required or commonly used across all job types.

### `name`

| Property | Value |
|----------|-------|
| **Type** | `str` |
| **Required** | Yes |

A descriptive name for your job definition. Used to identify the job in the Rapidata Dashboard and when retrieving jobs programmatically. This name is **not shown to labelers**.

```python
name="Image Quality Rating v2 - January Batch"
```

---

### `instruction`

| Property | Value |
|----------|-------|
| **Type** | `str` |
| **Required** | Yes |

The task instruction shown to labelers. This should clearly explain what action they need to take.

**Best Practices:**

- Be specific and unambiguous
- Use action verbs ("Select", "Choose", "Identify")
- For comparisons, use comparative language ("Which looks better?")
- See [Human Prompting](human_prompting.md) for detailed guidance

```python
instruction="Which image follows the prompt more accurately?"
```

---

### `datapoints`

| Property | Value |
|----------|-------|
| **Type** | `list[str]` or `list[list[str]]` |
| **Required** | Yes |

The data to be labeled. The format depends on the job type:

| Job Type | Format | Description |
|----------|--------|-------------|
| Classification | `list[str]` | Single items to classify |
| Compare | `list[list[str]]` | Pairs of items (exactly 2 per inner list) |

**Supported Formats:**

- Public URLs (https://...)
- Local file paths (will be uploaded automatically)

```python
# Classification - list of single items
datapoints=["https://example.com/img1.jpg", "https://example.com/img2.jpg"]

# Compare - list of pairs
datapoints=[
    ["https://example.com/a1.jpg", "https://example.com/b1.jpg"],
    ["https://example.com/a2.jpg", "https://example.com/b2.jpg"],
]
```

---

### `responses_per_datapoint`

| Property | Value |
|----------|-------|
| **Type** | `int` |
| **Required** | No |
| **Default** | `10` |

The minimum number of responses to collect for each datapoint. The actual number may slightly exceed this due to concurrent labelers.

**Best Practices:**

- Use 15-25 for ambiguous or subjective tasks
- Use 5-10 for clear-cut decisions

```python
responses_per_datapoint=15
```

---

## Data Type

### `data_type`

| Property | Value |
|----------|-------|
| **Type** | `Literal["media", "text"]` |
| **Required** | No |
| **Default** | `"media"` |

Specifies how datapoints should be interpreted and displayed.

| Value | Description |
|-------|-------------|
| `"media"` | Datapoints are URLs or paths to images, videos, or audio files |
| `"text"` | Datapoints are raw text strings to be displayed directly |

```python
# Comparing two text responses
job_definition = client.job.create_compare_job_definition(
    name="LLM Response Comparison",
    instruction="Which response is more helpful?",
    datapoints=[
        ["Response A text here...", "Response B text here..."],
    ],
    data_type="text",
)
```

---

## Context Parameters

Context parameters allow you to provide additional information alongside each datapoint.

### `contexts`

| Property | Value |
|----------|-------|
| **Type** | `Optional[list[str]]` |
| **Required** | No |
| **Default** | `None` |

Text context shown alongside each datapoint. Commonly used to provide prompts, descriptions, or additional instructions specific to each item.

**Constraints:** If provided, must have the same length as `datapoints`.

```python
datapoints=["image1.jpg", "image2.jpg"],
contexts=["A cat sitting on a red couch", "A blue car in the rain"]
```

---

### `media_contexts`

| Property | Value |
|----------|-------|
| **Type** | `Optional[list[str]]` |
| **Required** | No |
| **Default** | `None` |

Media URLs shown as reference context alongside each datapoint. Useful when you need to show a reference image or video alongside the item being evaluated.

**Constraints:** If provided, must have the same length as `datapoints`.

```python
# Show original image as context while evaluating edited versions
datapoints=["edited1.jpg", "edited2.jpg"],
media_contexts=["original1.jpg", "original2.jpg"]
```

---

## Quality Control Parameters

### `confidence_threshold`

| Property | Value |
|----------|-------|
| **Type** | `Optional[float]` |
| **Required** | No |
| **Default** | `None` |
| **Range** | `0.0` to `1.0` (typically `0.99` to `0.999`) |

Enables early stopping when a specified confidence level is reached. The system stops collecting responses once consensus is achieved, reducing costs while maintaining quality.

**How It Works:** Uses labeler trust scores (`userScore`) to calculate statistical confidence for each category.

**Related:** [Confidence Stopping](confidence_stopping.md)

```python
job_definition = client.job.create_classification_job_definition(
    name="Cat or Dog with Early Stopping",
    instruction="What animal is in this image?",
    answer_options=["Cat", "Dog"],
    datapoints=["pet1.jpg", "pet2.jpg"],
    responses_per_datapoint=50,  # Maximum responses
    confidence_threshold=0.99,   # Stop at 99% confidence
)
```

---

## Settings

Settings allow you to customize how tasks are displayed.

| Property | Value |
|----------|-------|
| **Type** | `Sequence[RapidataSetting]` |
| **Required** | No |
| **Default** | `[]` |

### Commonly Used Settings

#### `NoShuffle()`

Keeps answer options in the order you specified. By default, options are randomized to reduce bias. Use this for Likert scales or any ordered options.

```python
from rapidata import NoShuffle

job_definition = client.job.create_classification_job_definition(
    instruction="Rate the quality of this image",
    answer_options=["1: Poor", "2: Fair", "3: Good", "4: Excellent"],
    datapoints=["image.jpg"],
    settings=[NoShuffle()]
)
```

#### `Markdown()`

Enables limited markdown rendering for text datapoints. Useful when comparing formatted text like LLM outputs.

```python
from rapidata import Markdown

job_definition = client.job.create_compare_job_definition(
    name="LLM Response Comparison",
    instruction="Which response is better formatted?",
    datapoints=[["**Bold** and _italic_", "Plain text only"]],
    data_type="text",
    settings=[Markdown()]
)
```

#### `AllowNeitherBoth()`

For Compare jobs, allows labelers to select "Neither" or "Both" instead of forcing a choice.

```python
from rapidata import AllowNeitherBoth

job_definition = client.job.create_compare_job_definition(
    name="Image Quality Comparison",
    instruction="Which image is higher quality?",
    datapoints=[["img_a.jpg", "img_b.jpg"]],
    settings=[AllowNeitherBoth()]
)
```

---

## Job-Specific Parameters

### Classification Job

| Parameter | Type | Description |
|-----------|------|-------------|
| `answer_options` | `list[str]` | List of categories to classify into |

```python
job_definition = client.job.create_classification_job_definition(
    name="Animal Classification",
    instruction="What animal is in the image?",
    answer_options=["Cat", "Dog", "Bird", "Other"],
    datapoints=["image1.jpg", "image2.jpg"],
)
```

### Compare Job

| Parameter | Type | Description |
|-----------|------|-------------|
| `a_b_names` | `Optional[list[str]]` | Custom labels for the two options (list of exactly 2 strings) |

```python
job_definition = client.job.create_compare_job_definition(
    name="Model Comparison",
    instruction="Which image is better?",
    datapoints=[["model_a.jpg", "model_b.jpg"]],
    a_b_names=["Flux", "Midjourney"],  # Results will show these names
)
```

---

## Parameter Availability Matrix

| Parameter | Classification | Compare |
|-----------|:-:|:-:|
| `name` | :white_check_mark: | :white_check_mark: |
| `instruction` | :white_check_mark: | :white_check_mark: |
| `datapoints` | :white_check_mark: | :white_check_mark: |
| `responses_per_datapoint` | :white_check_mark: | :white_check_mark: |
| `data_type` | :white_check_mark: | :white_check_mark: |
| `contexts` | :white_check_mark: | :white_check_mark: |
| `media_contexts` | :white_check_mark: | :white_check_mark: |
| `confidence_threshold` | :white_check_mark: | :white_check_mark: |
| `settings` | :white_check_mark: | :white_check_mark: |
| `answer_options` | :white_check_mark: | :x: |
| `a_b_names` | :x: | :white_check_mark: |
