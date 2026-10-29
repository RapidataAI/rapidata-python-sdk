# Moving to the current SDK

The page you followed may describe an API or setting that is no longer available.
The current documentation uses audiences, job definitions, and jobs.

1. Follow the [Quick Start](quickstart.md) to create and run a job.
2. Use [Custom Audiences](audiences.md) to select and qualify labelers.
3. Check the [Parameter Reference](job_definition_parameters.md) for supported configuration and [Understanding Results](understanding_the_results.md) for result fields.

## Compare jobs stop adaptively (4.0)

`create_compare_job_definition` now defaults to `responses_per_datapoint=AdaptiveStopping()`. Each pair stops once its verdict is settled, using up to 100 responses instead of exactly 10.

| Before | Now |
|--------|-----|
| no `responses_per_datapoint` on a compare job: 10 responses | adaptive stopping, up to 100 (about 21 on average) |
| `quorum_threshold=7, responses_per_datapoint=10` | `responses_per_datapoint=QuorumStopping(threshold=7, max_responses=10)` |
| `confidence_threshold=0.99` on a compare job | `responses_per_datapoint=AdaptiveStopping()` |
| `CostEstimate.estimated_cost`: cost of the fixed number of responses | expected cost; `max_cost` is the upper bound |

- To keep exactly 10 responses per pair, pass `responses_per_datapoint=10`.
- `AdaptiveStopping` cannot be combined with `AllowNeitherBothSetting`; pass an `int` or `QuorumStopping` there.
- `confidence_threshold` and `quorum_threshold` still work with an `int` `responses_per_datapoint` but emit a `DeprecationWarning`.
- `job_definition.responses_per_datapoint` now returns `AdaptiveStopping` or `QuorumStopping` for definitions that use them. Assigning an `int` sets a fixed number of responses.
- Compare results gain `verdict` and `responses` per datapoint — see [Early Stopping](confidence_stopping.md#analyzing-adaptive-stopping-results).
