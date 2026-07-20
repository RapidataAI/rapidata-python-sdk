# Job Progress

`job.get_status()` tells you the coarse state of a job — `Running`, `Completed`, and so on. Often you want more: is a running job labeling normally, still recruiting annotators, or genuinely stalled? `job.get_progress()` answers that in one call.

## Reading Progress

```py
from rapidata import RapidataClient

client = RapidataClient()

job = client.job.get_job_by_id("...")
progress = job.get_progress()

print(f"{progress.state}: {progress.completion_percentage:.1f}% done")

if progress.recruiting:
    r = progress.recruiting
    print(f"{r.graduated} annotators ready, {r.distilling} still qualifying")
```

`get_progress()` does not block — it reports the current progress and returns immediately.

## What Progress Contains

A `JobProgress` has three fields:

| Field | Description |
|---|---|
| `state` | The job's current state, the same value returned by `get_status()`. |
| `completion_percentage` | How much of the requested labeling is done, from 0 to 100. |
| `recruiting` | A `RecruitingMetrics` snapshot of the annotator pool, or `None` for curated audiences. |

## The Recruiting Funnel

Custom audiences recruit their own pool of annotators, and `recruiting` shows how that pool is distributed. The counts are mutually exclusive — each annotator is in exactly one bucket:

| Field | Description |
|---|---|
| `graduated` | Annotators who passed qualification and are eligible to work now. |
| `distilling` | Annotators still going through qualification. |
| `dropped` | Annotators removed from the pool (score too low, limits reached, etc.). |
| `inactive` | Previously graduated or distilling annotators who went quiet. |

This is what lets you tell recruiting from stalling: a running job at 0% with `graduated == 0` is still assembling its pool, not stuck.

The same snapshot is available straight from the audience, which is useful when one audience feeds several jobs:

```py
audience = client.audience.get_audience_by_id("aud_...")
print(audience.get_recruiting_metrics())
```

!!! note
    Only custom audiences recruit their own pool. For curated audiences, `job.get_progress().recruiting` is `None`, and `audience.get_recruiting_metrics()` returns all zeros.
