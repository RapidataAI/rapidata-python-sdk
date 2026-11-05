# Moving to the current SDK

The page you followed may describe an API or setting that is no longer available.
The current documentation uses audiences, job definitions, and jobs.

1. Follow the [Quick Start](quickstart.md) to create and run a job.
2. Use [Custom Audiences](audiences.md) to select and qualify labelers.
3. Check the [Parameter Reference](job_definition_parameters.md) for supported configuration and [Understanding Results](understanding_the_results.md) for result fields.

## Compare jobs stop adaptively (4.0)

`create_compare_job_definition` now defaults to `responses_per_datapoint=AdaptiveStopping()`. Each pair stops when a decision is reached or its response cap is met, instead of collecting exactly 10 responses.

| Before | Now |
|--------|-----|
| no `responses_per_datapoint` on a compare job: 10 responses | adaptive stopping, with a variable response count |
| `quorum_threshold=7, responses_per_datapoint=10` | `responses_per_datapoint=QuorumStopping(threshold=7, max_responses=10)` |
| `confidence_threshold=0.99` on a compare job | `responses_per_datapoint=AdaptiveStopping()` |
| `CostEstimate.estimated_cost`: cost of the fixed number of responses | expected cost |

- To keep exactly 10 responses per pair, pass `responses_per_datapoint=10`.
- `quorum_threshold` still works with an `int` `responses_per_datapoint` but emits a `DeprecationWarning`. `confidence_threshold` does the same on compare jobs; on classification it stays supported without a warning.
- `job_definition.responses_per_datapoint` now returns `AdaptiveStopping` or `QuorumStopping` for definitions that use them. Assigning an `int` sets a fixed number of responses.
- New adaptive results retain `adaptiveStopping` and expose canonical `verdict`, `responses`, and `leadingOutcomeIds` per datapoint. Older `stoppingState` exports keep their legacy decoding — see [Adaptive Stopping](confidence_stopping.md#analyzing-adaptive-stopping-results).

## Categorical adaptive stopping

`ambiguity_threshold=0.64` replaces the unmerged `ambiguity_range=0.6` argument; the old keyword is not a public alias. For an earlier binary range \(r\), the equivalent normalized threshold is \(1-r^2\). Saved legacy wire `ambiguityRange` is accepted on reads and converted; new writes use `ambiguityThreshold`.

`AdaptiveStopping` also exposes `max_outcome_count=1` and `unsolvable_threshold=0.5`. The resolved workflow config always contains the latter, while snapshot `parameters.unsolvableThreshold` is `null` if can't solve is disabled. Blueprint enablement and the annotator response are separate from the threshold.

Single-select classification now accepts explicit `AdaptiveStopping()` while retaining the fixed-10 default. Leading-set limits are checked against each datapoint's category count. Existing integer configurations remain fixed counts.
