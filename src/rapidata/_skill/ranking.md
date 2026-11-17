# Ranking jobs

> Part of the Rapidata agent skill: `python -m rapidata skill ranking`. The **Task design rules** and **Key Gotchas** in the main guide (`python -m rapidata skill`) apply to everything here; parameters shared by every job type are in `python -m rapidata skill reference`.

## Create a ranking job definition

Ranking is available as a job definition or via **continuous ranking flows** (`python -m rapidata skill flows`).

```python
job_def = client.job.create_ranking_job_definition(
    name="Image Quality Ranking",
    instruction="Which image looks better?",
    datapoints=[["img1.jpg", "img2.jpg", "img3.jpg"]],  # outer list = independent rankings
    comparison_budget_per_ranking=50,
    responses_per_comparison=1,
    random_comparisons_ratio=0.5,
    contexts=["Optional context"],
)
job = audience.assign_job(job_def)
job.display_progress_bar()
results = job.get_results()  # one entry per ranking: results["results"][0]["summary"] = {datapoint: Elo score}
df = results.to_pandas()     # one row per ranked datapoint: group, datapoint, score, rank
```

## Settings to consider here

Check these while writing the job definition; add one only when the case fits. Every setting with its arguments: `python -m rapidata skill settings`.

Ranking is checked as a comparison for settings, so the video, 360° and text-translation rows of the comparison guide's settings table apply (`python -m rapidata skill comparison`).

## Ranking parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `datapoints` | list[list[str]] | Groups: `[["img1","img2","img3"], ...]`; each inner list is one independent ranking set |
| `comparison_budget_per_ranking` | int | Total comparisons per ranking group |
| `responses_per_comparison` | int | Responses per individual comparison (default 1); replaces `responses_per_datapoint` for ranking |
| `random_comparisons_ratio` | float | Ratio of random vs targeted comparisons (0-1, default 0.5). Ignored for rankings of ≤10 datapoints (see below) |
| `data_type` | `"media"` \| `"text"` | Default `"media"` |
| `contexts` / `media_contexts` | list \| None | One entry per ranking group (not per datapoint) |

`responses_per_datapoint`, `answer_options`, `a_b_names`, `confidence_threshold`, `quorum_threshold`, and `private_metadata` are not available for ranking jobs.

**Matchup behavior by ranking size.** How a ranking group is compared depends on how many datapoints it holds:

- **More than 10 datapoints:** matched adaptively (Elo-style) within `comparison_budget_per_ranking`; `random_comparisons_ratio` applies as described above.
- **10 or fewer datapoints:** every unique pair is compared, with the budget spread evenly across pairs (the total is rounded down to a multiple of the pair count; every pair is compared at least once even if the budget is smaller than the pair count). `random_comparisons_ratio` does **not** apply in this case.

## Results

One `results` entry **per ranking** (per inner list of `datapoints`), not per matchup. There is no top-level `summary`.

```json
{
  "info": { "type": "Ranking", "name": "Image Quality Ranking", "instruction": "Which image looks better?", "version": "4.1.0" },
  "results": [
    {
      "group": "0",
      "context": "Optional context",
      "summary": { "img3.jpg": 1335, "img1.jpg": 1200, "img2.jpg": 1064 },
      "results": [
        {
          "winner": "img3.jpg", "winnerIndex": 1, "weightedWinner": "img3.jpg", "weightedWinnerIndex": 1,
          "assetUrls": { "img1.jpg": "https://assets.rapidata.ai/<random-uuid>.jpg", "img3.jpg": "https://assets.rapidata.ai/<random-uuid>.jpg" },
          "aggregatedResults": { "img1.jpg": 0, "img3.jpg": 1 },
          "aggregatedResultsRatios": { "img1.jpg": 0.0, "img3.jpg": 1.0 },
          "summedUserScores": { "img1.jpg": 0.0, "img3.jpg": 0.73 },
          "summedUserScoresRatios": { "img1.jpg": 0.0, "img3.jpg": 1.0 },
          "detailedResults": [ { "votedFor": "img3.jpg", "userDetails": { "country": "DE", "language": "de", "userScores": { "global": 0.73 } } } ]
        }
      ]
    }
  ]
}
```

`group` is the ranking's index in `datapoints`, as a string. `summary` is **the ranking**: each datapoint's identifier → Elo score, highest first, starting from 1200. The inner `results` are the matchups, shaped like Comparison datapoints (no `adaptiveStoppingState`, no `winner_index`). If two datapoints in one ranking share a file name, every identifier in it gets an index prefix (`0/img.jpg`, `1/img.jpg`).

## Example

```python
from rapidata import RapidataClient

client = RapidataClient()
audience = client.audience.get_audience_by_id("global")

job_def = client.job.create_ranking_job_definition(
    name="Image Quality Ranking",
    instruction="Which image looks better?",
    datapoints=[["img1.jpg", "img2.jpg", "img3.jpg", "img4.jpg"]],  # outer list = independent rankings
    comparison_budget_per_ranking=50,
    # With >10 datapoints, matchups are chosen adaptively (Elo-style) within the
    # budget and random_comparisons_ratio applies. With <=10 (as here), every
    # unique pair is compared with the budget spread evenly across pairs, and
    # random_comparisons_ratio has no effect.
    random_comparisons_ratio=0.5,
)
job = audience.assign_job(job_def)
job.view()
job.display_progress_bar()
results = job.get_results()
```
