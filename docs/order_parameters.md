# Order Parameter Reference

This guide provides a comprehensive reference for all parameters available when creating orders in the Rapidata Python SDK. Understanding these parameters will help you configure orders to collect high-quality labeled data tailored to your specific requirements.

## Overview

When creating an order, you'll use parameters to control:

- **What data** is shown to annotators (datapoints, contexts)
- **How many responses** you need (responses_per_datapoint)
- **How tasks are displayed** (settings)
- **Quality assurance** (validation_set_id, confidence_threshold)

Parameters can be categorized as **required** (must be provided) or **optional** (have sensible defaults).

---

## Core Parameters

These parameters are required or commonly used across all order types.

### `name`

| Property | Value |
|----------|-------|
| **Type** | `str` |
| **Required** | Yes |
| **Default** | None (must be provided) |

A descriptive name for your order. Used to identify the order in the Rapidata Dashboard and when retrieving orders programmatically. This name is **not shown to annotators**.

**Best Practices:**

- Use descriptive names that indicate the task type and version
- Include dates or identifiers for easy tracking

```python
name="Image Quality Rating v2 - January Batch"
```

---

### `instruction`

| Property | Value |
|----------|-------|
| **Type** | `str` |
| **Required** | Yes |
| **Default** | None (must be provided) |

The task instruction shown to annotators. This should clearly explain what action they need to take.

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
| **Default** | None (must be provided) |

The data to be labeled. The format depends on the order type:

| Order Type | Format | Description |
|------------|--------|-------------|
| Classification | `list[str]` | Single items to classify |
| Compare | `list[list[str]]` | Pairs of items (exactly 2 per inner list) |
| Ranking | `list[list[str]]` | Sets of items to rank (2+ per inner list) |
| Free Text | `list[str]` | Items to describe |
| Select Words | `list[str]` | Media items with associated sentences |
| Locate | `list[str]` | Images to locate objects in |
| Draw | `list[str]` | Images to draw on |
| Timestamp | `list[str]` | Videos/audio to mark timestamps |

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

# Ranking - list of sets to rank
datapoints=[[
    "https://example.com/img1.jpg",
    "https://example.com/img2.jpg",
    "https://example.com/img3.jpg",
]]
```

---

### `responses_per_datapoint`

| Property | Value |
|----------|-------|
| **Type** | `int` |
| **Required** | No |
| **Default** | `10` |

The minimum number of responses to collect for each datapoint. The actual number of responses may slightly exceed this due to concurrent annotators.

> Note: For Ranking orders, you controle the global number of comparisons to collect with `comparison_budget_per_ranking` as the matchups are created dynamically.

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
| **Available On** | Classification, Compare, Ranking, Free Text |

Specifies how datapoints should be interpreted and displayed.

| Value | Description |
|-------|-------------|
| `"media"` | Datapoints are URLs or paths to images, videos, or audio files |
| `"text"` | Datapoints are raw text strings to be displayed directly |

>Note: Use `data_type="text"` when comparing text outputs (e.g., LLM responses), evaluating grammar, or any task where the content to evaluate is textual rather than media-based. Can be combined with [`Markdown()`](reference/rapidata/rapidata_client/settings/markdown.md) setting to enable limited markdown rendering for text assets.

```python
# Comparing two text responses
order = rapi.order.create_compare_order(
    name="LLM Response Comparison",
    instruction="Which response is more helpful?",
    datapoints=[
        ["Response A text here...", "Response B text here..."],
    ],
    data_type="text",
).preview()
```

```python
# Comparing two text responses with markdown rendering
from rapidata import Markdown
order = rapi.order.create_compare_order(
    name="LLM Response Comparison",
    instruction="Which response is more helpful?",
    datapoints=[
        ["Response A text here... **bold** and _italic_", "Response B text here... **bold** and _italic_"],
    ],
    data_type="text",
    settings=[Markdown()],
).preview()
```
**WARNING**: Select Words, Locate, Draw, and Timestamp orders do not support `data_type` as they are media-only by design.

---

## Context Parameters

Context parameters allow you to provide additional information alongside each datapoint.

### `contexts`

| Property | Value |
|----------|-------|
| **Type** | `Optional[list[str]]` |
| **Required** | No |
| **Default** | `None` |
| **Available On** | Classification, Compare, Ranking, Free Text, Locate, Draw, Timestamp |

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
| **Available On** | Classification, Compare, Ranking, Free Text, Locate, Draw, Timestamp |

Media URLs shown as reference context alongside each datapoint. Useful when you need to show a reference image or video alongside the item being evaluated.

**Constraints:** If provided, must have the same length as `datapoints`.

```python
# Show original image as context while evaluating edited versions
datapoints=["edited1.jpg", "edited2.jpg"],
media_contexts=["original1.jpg", "original2.jpg"]
```

>Note: You can use both `contexts` and `media_contexts` together at the same time.

---

## Quality Control Parameters

Parameters for ensuring high-quality responses.

### `validation_set_id`

| Property | Value |
|----------|-------|
| **Type** | `Optional[str]` |
| **Required** | No |
| **Default** | `None` |
| **Available On** | Classification, Compare, Ranking, Select Words, Locate, Draw, Timestamp |

Reference to a pre-created validation set. When provided, annotators must correctly answer validation tasks, before being allowed to label the datapoints.

**How to obtain:** Create validation sets using `rapi.validation.create_*_set()` methods.

**Related:** [Improve Order Quality](improve_order_quality.md)

```python
# Find an existing validation set
validation_set = rapi.validation.find_validation_sets("My Validation Set")[0]

# Use it in your order
order = rapi.order.create_compare_order(
    name="Quality Controlled Comparison",
    instruction="Which image is higher quality?",
    datapoints=[["img_a.jpg", "img_b.jpg"]],
    validation_set_id=validation_set.id
)
```

---

### `confidence_threshold`

| Property | Value |
|----------|-------|
| **Type** | `Optional[float]` |
| **Required** | No |
| **Default** | `None` |
| **Range** | `0.0` to `1.0` (typically `0.99` to `0.999`) |
| **Available On** | Classification, Compare **only** |

Enables early stopping when a specified confidence level is reached. The system stops collecting responses once consensus is achieved, reducing costs while maintaining quality.

**How It Works:** Uses annotator trust scores (`userScore`) to calculate statistical confidence for each category.

**Related:** [Confidence Stopping](confidence_stopping.md)

```python
order = rapi.order.create_classification_order(
    name="Cat or Dog with Early Stopping",
    instruction="What animal is in this image?",
    answer_options=["Cat", "Dog"],
    datapoints=["pet1.jpg", "pet2.jpg"],
    responses_per_datapoint=50,  # Maximum responses
    confidence_threshold=0.99,   # Stop at 99% confidence
)
```

>Note: For unambiguous classification tasks, setting `confidence_threshold=0.99` with `responses_per_datapoint=50` typically requires only 4-6 actual responses to reach consensus.

---

## Settings

Settings allow you to customize how tasks are displayed and add quality control measures.

| Property | Value |
|----------|-------|
| **Type** | `Sequence[RapidataSetting]` |
| **Required** | No |
| **Default** | `[]` |
| **Available On** | All order types |

### Commonly Used Settings

#### `NoShuffle()`

Keeps answer options in the order you specified. By default, options are randomized to reduce bias. Use this for Likert scales or any ordered options.

```python
from rapidata import NoShuffle

order = rapi.order.create_classification_order(
    instruction="Rate the quality of this image",
    answer_options=["1: Poor", "2: Fair", "3: Good", "4: Excellent"],
    datapoints=["image.jpg"],
    settings=[NoShuffle()]
)
```

#### `FreeTextMinimumCharacters(n)`

Requires annotators to write at least `n` characters in free text responses. Helps ensure meaningful responses but will slow down the order. Use cautiously.

```python
from rapidata import FreeTextMinimumCharacters

order = rapi.order.create_free_text_order(
    name="Image Description",
    instruction="Describe what you see in this image",
    datapoints=["image.jpg"],
    settings=[FreeTextMinimumCharacters(5)]
).preview()
```

#### `Markdown()`

Enables limited markdown rendering for text datapoints. Useful when comparing formatted text like LLM outputs or math equations.

> Note: This will only be correcly displayed in the preview and not the order details page.

```python
from rapidata import Markdown

from rapidata import Markdown
order = client.order.create_compare_order(
    name="LLM Response Comparison",
    instruction="Which response is better formatted?",
    datapoints=[["**Bold** and _italic_", "Plain text only"], ["$$x^2 + y^2 = z^2$$", "$$a^2 + b^2 = c^2$$"]],
    data_type="text",
    settings=[Markdown()]
).preview()
```

#### `AllowNeitherBoth()`

For Compare orders, allows annotators to select "Neither" or "Both" instead of forcing a choice.

```python
from rapidata import AllowNeitherBoth

order = rapi.order.create_compare_order(
    name="Image Quality Comparison",
    instruction="Which image is higher quality?",
    datapoints=[["img_a.jpg", "img_b.jpg"]],
    settings=[AllowNeitherBoth()]
).preview()
```

For a complete list of available settings, see the [Settings Reference](reference/rapidata/rapidata_client/settings/rapidata_settings.md).

---

## Order-Specific Parameters

Some parameters are unique to specific order types. See the individual order documentation for details:

| Order Type | Unique Parameters | Documentation |
|------------|-------------------|---------------|
| Classification | `answer_options` - List of categories to classify into | [Classification](examples/classify_order.md) |
| Compare | `a_b_names` - Custom labels for the two options | [Compare](examples/compare_order.md) |
| Ranking | `comparison_budget_per_ranking`, `responses_per_comparison`, `random_comparisons_ratio` | [Ranking](examples/ranking_order.md) |
| Select Words | `sentences` - Text to select words from | [Select Words](examples/select_words_order.md) |

---

## Parameter Availability Matrix

Quick reference showing which parameters are available for each order type.

| Parameter | Classification | Compare | Ranking | Free Text | Select Words | Locate | Draw | Timestamp |
|-----------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **Core** |
| `name` | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| `instruction` | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| `datapoints` | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| `responses_per_datapoint` | :white_check_mark: | :white_check_mark: | :material-asterisk:^1^ | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| **Data Type** |
| `data_type` | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :x: | :x: | :x: | :x: |
| **Context** |
| `contexts` | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :x: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| `media_contexts` | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :x: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| **Quality Control** |
| `validation_set_id` | :white_check_mark: | :white_check_mark: | :white_check_mark: | :x: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| `confidence_threshold` | :white_check_mark: | :white_check_mark: | :x: | :x: | :x: | :x: | :x: | :x: |

^1^ Ranking uses `comparison_budget_per_ranking` instead of `responses_per_datapoint`

---

## Related Documentation

### Advanced Configurations

- [Filters Reference](reference/rapidata/rapidata_client/filter/rapidata_filters.md) - Complete filter documentation
- [Settings Reference](reference/rapidata/rapidata_client/settings/rapidata_settings.md) - Complete settings documentation
- [Selections Reference](reference/rapidata/rapidata_client/selection/rapidata_selections.md) - Complete selections documentation

### Task Examples

- [Classification Orders](examples/classify_order.md)
- [Compare Orders](examples/compare_order.md)
- [Ranking Orders](examples/ranking_order.md)
- [Free Text Orders](examples/free_text_order.md)
- [Select Words Orders](examples/select_words_order.md)
- [Locate Orders](examples/locate_order.md)
- [Draw Orders](examples/draw_order.md)
