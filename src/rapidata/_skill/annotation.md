# Locate, draw, select words and free text

> Part of the Rapidata agent skill: `python -m rapidata skill annotation`. The **Task design rules** and **Key Gotchas** in the main guide (`python -m rapidata skill`) apply to everything here; parameters shared by every job type are in `python -m rapidata skill reference`.

Locate: labelers tap points. Draw: labelers color in regions. Select words: labelers pick words of a sentence. Free text: labelers type an answer. Audience qualification examples for each are in `python -m rapidata skill audiences`.

## Settings to consider here

Check these while writing the job definition; add one only when the case fits. Every setting with its arguments: `python -m rapidata skill settings`.

| The case | Add |
|---|---|
| Locate: how many points a labeler may tap | `LocateMaxPointsSetting(n)` (default 3) / `LocateMinPointsSetting(n)` (default 1) |
| Locate or draw on media that may have no error at all | `NoMistakeOptionSetting()`, a "No mistakes" button |
| Free text: the answer is a number | `KeyboardNumericSetting()` |
| Free text: the question demands a length | `FreeTextMinimumCharactersSetting(n)` / `FreeTextMaxCharactersSetting(n)`, with caution (see Free Text) |
| Videos the labeler must actually watch | `PlayPercentageVideoSetting(percentage)`; keep the clips short (task design rule 5) |

## Locate

Ask labelers to tap on the points in a datapoint that match your instruction. Results are the set of tapped coordinates per datapoint. No `answer_options`, `a_b_names`, `data_type`, `confidence_threshold`, or `quorum_threshold`.

```python
from rapidata import LocateMaxPointsSetting

job_def = client.job.create_locate_job_definition(
    name="Artifact Detection",
    instruction="Tap on any visual glitches or errors in the image.",
    datapoints=["img1.jpg", "img2.jpg"],
    responses_per_datapoint=35,
    contexts=["Optional text context"],
    media_contexts=[["optional_reference.jpg"]],
    settings=[LocateMaxPointsSetting(5)],
    private_metadata=[{"id": "abc"}],
)
```

Locate has no job-specific parameters — only the core parameters apply. `data_type`, `answer_options`, `a_b_names`, `confidence_threshold`, and `quorum_threshold` are not available for locate jobs. `datapoints` is `list[str]` (one item per row).

For locate audience examples, use `audience.add_locate_example(instruction, datapoint, truths, context=None, media_context=None, explanation=None, settings=None)` where `truths` is a `list[Box]` (import `Box` from `rapidata`); coordinates are image ratios (0.0–1.0).

## Draw

Ask labelers to draw (color in) regions of an image that match your instruction. Results are the set of drawn lines per datapoint. No `answer_options`, `a_b_names`, `data_type`, `confidence_threshold`, or `quorum_threshold`.

```python
job_def = client.job.create_draw_job_definition(
    name="Artifact Drawing",
    instruction="Color in any visual glitches or errors in the image.",
    datapoints=["img1.jpg", "img2.jpg"],
    responses_per_datapoint=35,
    contexts=["Optional text context"],
    media_contexts=[["optional_reference.jpg"]],
    private_metadata=[{"id": "abc"}],
)
```

Draw has no job-specific parameters — only the core parameters apply. `data_type`, `answer_options`, `a_b_names`, `confidence_threshold`, and `quorum_threshold` are not available for draw jobs. `datapoints` is `list[str]`.

For draw audience examples, use `audience.add_draw_example(instruction, datapoint, truths, context=None, media_context=None, explanation=None, settings=None)` where `truths` is a `list[Box]` (import `Box` from `rapidata`); coordinates are image ratios (0.0–1.0), and labelers pass when their lines fall within a box.

### Locate and draw results

```json
{
  "info": { "type": "Locate", "name": "Artifact Detection", "instruction": "Tap on any visual glitches.", "version": "4.1.0" },
  "results": [
    {
      "identifier": "img1.jpg", "originalFileName": "img1.jpg", "assetUrl": "https://assets.rapidata.ai/<random-uuid>.jpg",
      "notApplicable": 1, "notApplicableRatio": 0.0286,
      "aggregatedResults": [ { "x": 68.1007, "y": 32.4029 }, { "x": 23.3924, "y": 31.883 } ],
      "detailedResults": [ { "locations": [ { "x": 68.1007, "y": 32.4029 } ], "userDetails": { "country": "ES", "language": "es", "userScores": { "global": 0.67 } } } ]
    }
  ]
}
```

`x` / `y` are **percentages** (0–100) of the image width and height. `aggregatedResults` is every point from every labeler, flattened and not clustered; `detailedResults[].locations` is one labeler's points (empty when they marked it not applicable). `notApplicable` counts those labelers.

Draw (`"type": "Draw"`) has the same shape with lines instead of points: `aggregatedResults` is a list of `{ "size": 12, "points": [ { "x": 83.85, "y": 79.45 }, ... ] }` (`size` = brush size), and the per-labeler key is `detailedResults[].lines`.

## Select Words

Ask labelers to select the words from a sentence that match your instruction (e.g., words not depicted in an image). Each datapoint is paired with a `sentence` split by spaces. No `contexts`, `media_contexts`, `data_type`, `answer_options`, `a_b_names`, `confidence_threshold`, or `quorum_threshold`.

```python
job_def = client.job.create_select_words_job_definition(
    name="Image-Text Alignment",
    instruction="Select the words not correctly depicted in the image.",
    datapoints=["img1.jpg", "img2.jpg"],
    sentences=["A cat on a red couch [No_mistakes]", "A blue car in the rain [No_mistakes]"],
    responses_per_datapoint=15,
    private_metadata=[{"id": "abc"}],
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `sentences` | list[str] | One sentence per datapoint, split by spaces for labelers to select words from (must have same length as `datapoints`) |

`contexts`, `media_contexts`, `data_type`, `answer_options`, `a_b_names`, `confidence_threshold`, and `quorum_threshold` are not available for select words jobs.

For select words audience examples, use `audience.add_select_words_example(instruction, datapoint, sentence, truths, required_precision=1, required_completeness=1, explanation=None, settings=None)` where `truths` is a `list[int]` of 0-based word indices to select. `required_precision` is the minimum share of selected words that must be correct, `required_completeness` the minimum share of correct words that must be selected (both default `1` = exact match).

### Select words results

```json
{
  "info": { "type": "SelectWords", "name": "Image-Text Alignment", "instruction": "Select the words not shown in the image.", "version": "4.1.0" },
  "results": [
    {
      "identifier": "img1.jpg", "originalFileName": "img1.jpg", "assetUrl": "https://assets.rapidata.ai/<random-uuid>.jpg",
      "sentence": "Four cars on the street.",
      "aggregatedResults": [
        { "word": "Four", "wordIndex": 0, "selectedAmount": 0 },
        { "word": "cars", "wordIndex": 1, "selectedAmount": 4 }
      ],
      "detailedResults": [ { "selectedWords": [ { "word": "cars", "wordIndex": 1 } ], "userDetails": { "country": "BR", "language": "pt", "userScores": { "global": 0.71 } } } ]
    }
  ]
}
```

`aggregatedResults` has one entry per word of the sentence, in order, including unselected words. Match on `wordIndex` (position after splitting by spaces), not `word`, when a word repeats.

## Free Text

Ask labelers to answer your instruction with free-form text. No `answer_options`, `a_b_names`, `confidence_threshold`, or `quorum_threshold`. Note: free text answers cannot be graded against a ground truth, so audiences cannot be trained with free text qualification examples.

```python
job_def = client.job.create_free_text_job_definition(
    name="Prompt Collection",
    instruction="What would you like to ask an AI? Please spell out the question.",
    datapoints=["image.jpg"],
    responses_per_datapoint=15,
    contexts=["Optional text context"],
)
```

Free Text has no job-specific parameters — only the core parameters apply. `answer_options`, `a_b_names`, `confidence_threshold`, and `quorum_threshold` are not available.

### Free text results

```json
{
  "info": { "type": "FreeText", "name": "Prompt generation", "instruction": "What would you like to ask an AI?", "version": "4.1.0" },
  "results": [
    {
      "identifier": "img1.png", "originalFileName": "img1.png", "assetUrl": "https://assets.rapidata.ai/<random-uuid>.png",
      "aggregatedResults": [ "How do I bake bread?", "What is the tallest mountain?" ],
      "detailedResults": [ { "answerText": "How do I bake bread?", "userDetails": { "country": "US", "language": "en", "userScores": { "global": 0.81 } } } ]
    }
  ]
}
```

## Examples

### Locate Job

```python
from rapidata import RapidataClient

client = RapidataClient()

# Simple: use the ready-to-go global pool
audience = client.audience.get_audience_by_id("global")

job_def = client.job.create_locate_job_definition(
    name="Artifact Detection",
    instruction="Tap on any visual glitches or errors in the image.",
    datapoints=["img1.jpg", "img2.jpg", "img3.jpg"],
    responses_per_datapoint=35,
)
job = audience.assign_job(job_def)
job.view()
job.display_progress_bar()
results = job.get_results()
```

Custom audience with locate qualification examples:

```python
from rapidata import RapidataClient, Box

client = RapidataClient()

audience = client.audience.create_audience(name="Artifact Detection Audience", min_tasks=3)

EXAMPLES = [
    ("example1.jpg", [Box(x_min=0.44, y_min=0.42, x_max=0.58, y_max=0.63)]),
    ("example2.jpg", [Box(x_min=0.07, y_min=0.37, x_max=0.39, y_max=0.71)]),
    ("example3.jpg", [Box(x_min=0.04, y_min=0.10, x_max=0.31, y_max=0.28)]),
]

for datapoint, truths in EXAMPLES:
    audience.add_locate_example(
        instruction="Tap on any visual glitches or errors in the image.",
        datapoint=datapoint,
        truths=truths,
        explanation="The artifact is within the highlighted region.",
    )

audience.start_recruiting()  # required — a job assigned before this can never receive responses

job_def = client.job.create_locate_job_definition(
    name="Artifact Detection",
    instruction="Tap on any visual glitches or errors in the image.",
    datapoints=["img1.jpg", "img2.jpg", "img3.jpg"],
    responses_per_datapoint=35,
)
job = audience.assign_job(job_def)
job.view()
job.display_progress_bar()
results = job.get_results()
```

### Draw Job

```python
from rapidata import RapidataClient

client = RapidataClient()

# Simple: use the ready-to-go global pool
audience = client.audience.get_audience_by_id("global")

job_def = client.job.create_draw_job_definition(
    name="Artifact Drawing",
    instruction="Color in any visual glitches or errors in the image.",
    datapoints=["img1.jpg", "img2.jpg", "img3.jpg"],
    responses_per_datapoint=35,
)
job = audience.assign_job(job_def)
job.view()
job.display_progress_bar()
results = job.get_results()
```

For a custom draw audience, follow the locate custom-audience example above with `audience.add_draw_example(...)` (same `truths=list[Box]` shape).

### Select Words Job

```python
from rapidata import RapidataClient

IMAGES = ["img1.jpg", "img2.jpg", "img3.jpg", "img4.jpg"]
PROMPTS = [
    "The black camera was next to the white tripod.",
    "Four cars on the street.",
    "Car is bigger than the airplane.",
    "One cat and two dogs sitting on the grass.",
]
SENTENCES = [p + " [No_mistakes]" for p in PROMPTS]

client = RapidataClient()
audience = client.audience.get_audience_by_id("global")

job_def = client.job.create_select_words_job_definition(
    name="Image-Text Alignment",
    instruction="Select the words that the image does not show.",
    datapoints=IMAGES,
    sentences=SENTENCES,
    responses_per_datapoint=15,
)
job = audience.assign_job(job_def)
job.view()
job.display_progress_bar()
results = job.get_results()
```

### Free Text Job

```python
from rapidata import RapidataClient

client = RapidataClient()
audience = client.audience.get_audience_by_id("global")

job_def = client.job.create_free_text_job_definition(
    name="Prompt Collection",
    instruction="What would you like to ask an AI? Please spell out the question.",
    datapoints=["image.jpg"],
    responses_per_datapoint=15,
)
job = audience.assign_job(job_def)
job.view()
job.display_progress_bar()
results = job.get_results()
```

### Free-Text Length Constraints

Use length constraints sparingly. Free-text responses are already filtered by a built-in reasonableness check, so these settings are usually unnecessary and will reject otherwise valid answers. Only set them when the question genuinely demands a specific length.

```python
from rapidata import (
    RapidataClient,
    FreeTextMinimumCharactersSetting,
    FreeTextMaxCharactersSetting,
)

client = RapidataClient()
audience = client.audience.get_audience_by_id("global")

job_def = client.job.create_free_text_job_definition(
    name="Caption Generation",
    instruction="Describe what's happening in this image in one sentence.",
    datapoints=["scene1.jpg", "scene2.jpg"],
    settings=[
        FreeTextMinimumCharactersSetting(20),
        FreeTextMaxCharactersSetting(200),
    ],
)
job = audience.assign_job(job_def)
```
