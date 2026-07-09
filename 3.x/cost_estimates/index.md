# Cost Estimates

Before you commit to a large labeling run, you can ask Rapidata what a job is expected to cost. Every job definition and every running job exposes an `estimated_cost` property that returns a `CostEstimate`.

## Getting an Estimate

You can read the estimate straight from a job definition, before assigning it to an audience — useful for checking the cost of a run before you launch it:

```py
from rapidata import RapidataClient

client = RapidataClient()

job_definition = client.job.create_compare_job_definition(
    name="Example Image Prompt Alignment",
    instruction="Which image matches the description better?",
    datapoints=[
        ["https://assets.rapidata.ai/midjourney-5.2_37_3.jpg",
         "https://assets.rapidata.ai/flux-1-pro_37_0.jpg"]
    ],
    contexts=["A small blue book sitting on a large red book."],
)

estimate = job_definition.estimated_cost # (1)!
print(f"About {estimate.estimated_cost} for {estimate.required_responses} responses")
```

1. The estimate is priced shortly after the definition is created. Reading it right away blocks for a moment until it is ready, then returns.

The same property is available on a job once it is running:

```py
job = audience.assign_job(job_definition)
print(job.estimated_cost.estimated_cost)
```

## What the Estimate Contains

A `CostEstimate` has three fields:

| Field | Description |
|---|---|
| `estimated_cost` | The estimated total cost of running the job to completion, in your account's billing currency. |
| `datapoint_count` | The number of datapoints the job will label. |
| `required_responses` | The total number of responses the job collects to complete. |

!!! note
    This is an **estimate, not the final bill**. It is based on a sample of the job's tasks scaled to the number of responses requested, so the amount you are actually charged can differ. Features like [Early Stopping](confidence_stopping.md) can also lower the final cost by collecting fewer responses than the maximum.
