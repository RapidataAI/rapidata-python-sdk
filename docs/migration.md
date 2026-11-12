# Moving to the current SDK

The page you followed may describe an API or setting that is no longer available.
The current documentation uses audiences, job definitions, and jobs.

1. Follow the [Quick Start](quickstart.md) to create and run a job.
2. Use [Custom Audiences](audiences.md) to select and qualify labelers.
3. Check the [Parameter Reference](job_definition_parameters.md) for supported configuration and [Understanding Results](understanding_the_results.md) for result fields.

## Compare jobs stop adaptively

`create_compare_job_definition` now defaults to `responses_per_datapoint=AdaptiveStopping()`. Each pair stops once its verdict is settled instead of collecting exactly 10 responses: about 21 per pair on average, about 31 for the hardest pairs.

| Before | Now |
|--------|-----|
| no `responses_per_datapoint` on a compare job: 10 responses | adaptive stopping, about 21 responses per pair on average |
| `confidence_threshold=0.99` on a compare job | `responses_per_datapoint=AdaptiveStopping()` |

- To keep exactly 10 responses per pair, pass `responses_per_datapoint=10`.
- `confidence_threshold` still works with an `int` `responses_per_datapoint` but emits a `DeprecationWarning`. On compare jobs without `responses_per_datapoint`, it and `quorum_threshold` now cap at 15 responses instead of 10.
- `job_definition.responses_per_datapoint` returns an `AdaptiveStopping` for definitions that use it. Assigning an `int` sets a fixed number of responses.
- Compare results gain an `adaptiveStoppingState` per datapoint — see [Adaptive Stopping](confidence_stopping.md#analyzing-adaptive-stopping-results).
