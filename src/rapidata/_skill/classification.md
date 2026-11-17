# Classification jobs

> Part of the Rapidata agent skill: `python -m rapidata skill classification`. The **Task design rules** and **Key Gotchas** in the main guide (`python -m rapidata skill`) apply to everything here; parameters shared by every job type are in `python -m rapidata skill reference`.

## Create a classification job definition

Labelers pick exactly one of the answer options; the task screen allows only one, so the instruction never needs to say so.

```python
from rapidata import NoShuffleSetting

job_def = client.job.create_classification_job_definition(
    name="Image Classification",
    instruction="What animal is in this image?",
    answer_options=["Cat", "Dog", "Bird", "Other"],
    datapoints=["img1.jpg", "img2.jpg"],
    data_type="media",              # "media" (default) or "text" — text assets are NOT translated unless TranslateTextAssetsSetting is added
    responses_per_datapoint=10,     # Fixed count, or QuorumStopping(threshold=7, max_responses=10) to stop once 7 agree
    contexts=["Optional text context per datapoint"],
    media_contexts=[["optional_reference.jpg"]],
    settings=[NoShuffleSetting()],         # Keep answer order
    failure_tolerance=0.01,         # Optional: fraction of datapoints allowed to fail the upload
    private_metadata=[{"id": "abc"}],
)
```

## Settings to consider here

Check these while writing the job definition; add one only when the case fits. Every setting with its arguments: `python -m rapidata skill settings`.

| The case | Add |
|---|---|
| Ordered options: ratings, Likert scales, "how much" | `NoShuffleSetting()`, since options are shuffled otherwise |
| Text datapoints (`data_type="text"`) | `TranslateTextAssetsSetting()` for English text, else a `LanguageFilter` on the audience (Key Gotcha 9) |
| Videos the labeler must actually watch | `PlayPercentageVideoSetting(percentage)`; keep the clips short (task design rule 5). `DisableAutoloopSetting()` stops looping |
| 360° media | `ClassifyEquirectangularSetting()` |
| Text with markdown formatting | `MarkdownSetting()` |

## Classification-specific parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `answer_options` | list[str] \| list[list[str]] | Categories to choose from. Pass one list per datapoint (same length as `datapoints`) to show different options per datapoint; 2–8 unique options each |

## Quorum stopping

Stop collecting responses once a fixed number of responses agree on the same answer.

```python
from rapidata import QuorumStopping

job_def = client.job.create_classification_job_definition(
    name="Animal Classification",
    instruction="What animal is in this image?",
    answer_options=["Cat", "Dog"],
    datapoints=["pet1.jpg", "pet2.jpg"],
    responses_per_datapoint=QuorumStopping(threshold=7, max_responses=10),
)
```

A datapoint stops when:
1. `threshold` responses agree on the same answer, **OR**
2. Quorum becomes mathematically impossible (e.g. responses are too split to reach the threshold), **OR**
3. `max_responses` total responses are collected

`QuorumStopping` is a frozen dataclass; both fields are positive ints and `threshold` ≤ `max_responses`, else `ValueError`. Other job types than classification and compare raise `ValueError`.

Quorum stopping works on comparison jobs too; there it replaces the adaptive default.

## Results

```json
{
  "info": { "type": "Classification", "version": "3.0.0" },
  "results": [
    {
      "identifier": "image1.jpg",
      "originalFileName": "image1.jpg",
      "assetUrl": "https://assets.rapidata.ai/<random-uuid>.jpg",
      "aggregatedResults": { "Cat": 15, "Dog": 8 },
      "aggregatedResultsRatios": { "Cat": 0.6522, "Dog": 0.3478 },
      "summedUserScores": { "Cat": 9.5, "Dog": 4.2 },
      "summedUserScoresRatios": { "Cat": 0.6934, "Dog": 0.3066 },
      "confidencePerCategory": { "Cat": 0.989, "Dog": 0.011 },
      "detailedResults": [
        { "selectedCategory": "Cat", "userDetails": { "country": "US", "language": "en", "userScores": { "global": 0.75 } } }
      ]
    }
  ],
  "summary": { "Cat": 15, "Dog": 8 }
}
```

`identifier` is the source URL, the original file name, or the text of the datapoint; `summary` is the category counts summed over all datapoints. `confidencePerCategory` appears only with `confidence_threshold`.

## Examples

### Simple Classification

```python
from rapidata import RapidataClient

client = RapidataClient()
audience = client.audience.get_audience_by_id("global")

job_def = client.job.create_classification_job_definition(
    name="Image Classification",
    instruction="What's in this image?",
    answer_options=["Cat", "Dog", "Bird"],
    datapoints=["img1.jpg", "img2.jpg"],
)
job = audience.assign_job(job_def)
job.view()
job.display_progress_bar()
results = job.get_results()
df = results.to_pandas()
```

### Classification with Likert Scale

```python
from rapidata import RapidataClient, NoShuffleSetting

client = RapidataClient()
audience = client.audience.get_audience_by_id("global")

job_def = client.job.create_classification_job_definition(
    name="Quality Rating",
    instruction="How well does the video match the description?",
    answer_options=["1: Poor", "2: Fair", "3: Good", "4: Excellent"],
    datapoints=["video1.mp4", "video2.mp4"],
    contexts=["A cat playing piano", "A sunset over the ocean"],
    responses_per_datapoint=15,
    settings=[NoShuffleSetting()],  # Critical for ordered scales
)
job = audience.assign_job(job_def)
```
