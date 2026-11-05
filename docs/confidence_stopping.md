# Adaptive Stopping

Adaptive stopping ends response collection for a datapoint once a stopping condition is met, so you pay for the responses that change the outcome and not for the ones after it.

You choose the stopping rule with `responses_per_datapoint`:

| Value | Rule | Job types |
|-------|------|-----------|
| `AdaptiveStopping()` | Stops each pair once its verdict is statistically settled. **Default for compare jobs.** | Compare |
| `QuorumStopping(threshold, max_responses)` | Stops once `threshold` responses agree. | Classification, Compare |
| an `int` | Collects exactly that many responses. Default (`10`) for every other job type. | All |

## How it Works

Each response is weighted by the labeler's [user score](understanding_the_results.md#understanding-the-user-scores) at response time. The categorical model reports one leading outcome (`Winner`), a set of leading alternatives (`TopSet`), disagreement (`Ambiguous`), explicit can't solve (`Unsolvable`), no decision yet (`Open`), or the response cap without a decision (`Undecided`).

A `TopSet` does not assert that multiple labels are independently true in a single-select task. BothGood and BothBad remain distinct substantive outcomes. Can't solve is an explicit exclusive response, separate from Both, Neither, skips, or empty selections, and has its own threshold and solvability gate.

Confidence bounds are heuristic for score-weighted responses. A confidence parameter of `0.9` does not establish proven 90% coverage. Response counts vary with the configured outcomes and stopping conditions; binary averages and worst-case bounds do not generalize to additional categories or can't solve.

## Using Adaptive Stopping in Your Job

Compare jobs use adaptive stopping unless you pass something else:

```python
from rapidata import RapidataClient, AdaptiveStopping

client = RapidataClient()

job_definition = client.job.create_compare_job_definition(
    name="Prompt alignment",
    instruction="Which image matches the description better?",
    datapoints=[["https://assets.rapidata.ai/a.jpg", "https://assets.rapidata.ai/b.jpg"]],
    contexts=["A small blue book sitting on a large red book."],
    responses_per_datapoint=AdaptiveStopping(), # (1)!
)
```

1. The same as leaving the argument out.

The resolved configuration is included in each new snapshot's `parameters`. Normalized ambiguity is \(K/(K-1)(1-\sum_i p_i^2)\), with \(K\) configured substantive outcomes excluding can't solve and \(p_i\) conditional weighted shares. Its default threshold `0.64` preserves the binary raw threshold `0.32` / range `0.6`.

The [cost estimate](cost_estimates.md) is the expected cost, not the final bill.

### "Unsure" votes

[`AllowNeitherBothSetting`](job_definition_parameters.md#allowneitherbothsetting) enables additional compare choices. New categorical evidence retains BothGood and BothBad separately rather than splitting their scores into A/B. Explicit can't solve has its own evidence and is never inferred from either choice. Backend can't-solve configuration does not mean an annotator button is deployed.

## Analyzing Adaptive Stopping Results

New compare and single-select classification exports use the same `adaptiveStopping` evidence block. The SDK preserves the entire dictionary, including future metadata and verdicts, and exposes `verdict`, `responses`, and `leadingOutcomeIds` on each adaptive datapoint. Non-adaptive snapshots may be absent or `null`.

```python
results = job.get_results()
for datapoint in results["results"]:
    state = datapoint.get("adaptiveStopping")
    if state is not None:
        print(state["verdict"], state["leadingOutcomeIds"], state["responseCount"])
```

`leadingOutcomeIds` are stable identities that require the backend outcome definitions; their spelling or position does not supply an asset name or category value. `outcomes` keeps raw counts separate from weighted scores and shares. See [Adaptive evidence](understanding_the_results.md#adaptive-evidence) for every field and verdict.

Older `stoppingState` exports still decode to the legacy `A`, `B`, `ambiguous`, `undecided`, or `open` aliases. In a mixed export, `adaptiveStopping` takes precedence; both raw blocks remain available. `to_pandas()` keeps the new snapshot as one dictionary column, including when splitting detailed responses.

---

## Quorum Stopping

### How it Works

Quorum Stopping uses a simple vote-counting approach. A task is completed when:

1. `threshold` responses agree on the same answer, **OR**
2. Quorum becomes mathematically impossible to reach, **OR**
3. `max_responses` votes are reached.

For example, with `QuorumStopping(threshold=7, max_responses=10)`:

- The task completes when 7 responses agree (quorum reached).
- The task completes when both options have 4+ responses (quorum is impossible since neither can reach 7 out of 10).
- The task completes after 10 total votes if neither condition is met.

!!! note
    Quorum Stopping is supported for the Classification and Comparison workflows.

### Using Quorum Stopping in Your Job

#### Example: Classification Job with Quorum Stopping

```python
from rapidata import RapidataClient, QuorumStopping

client = RapidataClient()

audience = client.audience.create_audience(name="Animal Classification Audience")
audience.add_classification_example(
    instruction="What do you see in the image?",
    answer_options=["Cat", "Dog"],
    datapoint="https://assets.rapidata.ai/cat.jpeg",
    truth=["Cat"]
)

audience.start_recruiting() # (1)!

job_definition = client.job.create_classification_job_definition(
    name="Test Classification with Quorum Stopping",
    instruction="What do you see in the image?",
    answer_options=["Cat", "Dog"],
    datapoints=["https://assets.rapidata.ai/dog.jpeg"],
    responses_per_datapoint=QuorumStopping(threshold=7, max_responses=10), # (2)!
)

job = audience.assign_job(job_definition)
job.view()
job.display_progress_bar()
results = job.get_results()
print(results)
```

1. Starts recruiting once all qualification examples are added and reviewed. Adding examples does not start recruiting on its own.
2. Stops collecting once 7 responses agree on the same answer, and after 10 responses at most.

### When to Use Quorum Stopping

Quorum Stopping is a good choice when:

- **Classification**: Adaptive stopping is compare-only.
- **Simplicity**: You want a straightforward stopping rule based on raw vote counts rather than statistical confidence.

---

## Confidence Stopping

Confidence stopping is the early-stopping option for **classification** jobs.

### How it Works

The Early Stopping feature leverages the trustworthiness, quantified through their `userScores`, to calculate the confidence level of each category for any given datapoint.

### Confidence Calculation
- **UserScores**: Each labeler has a `userScore` between 0 and 1, representing their reliability. [More information](understanding_the_results.md#understanding-the-user-scores)
- **Aggregated Confidence**: By combining the userScores of labelers who selected a particular category, the system computes the probability that this category is the correct one.
- **Threshold Comparison**: If the calculated confidence exceeds your specified threshold, the system stops collecting further responses for that datapoint.

## Understanding the Confidence Threshold

We've created a plot based on empirical data aided by simulations to give you an estimate of the number of responses required to reach a certain confidence level.

There are a few things to keep in mind when interpreting the results:

- **Unambiguous Scenario**: The graph represents an ideal situation such as in the [example below](#using-confidence-stopping-in-your-job) with no ambiguity which category is the correct one. A counter-example would be subjective tasks like "Which image do you prefer?", where there's no clear correct answer.
- **Real-World Variability**: Actual required responses may vary based on task complexity.
- **Guidance Tool**: Use the graph as a reference to set realistic expectations for your jobs.
- **Response Overflow**: The number of responses per datapoint may exceed the specified amount due to multiple users answering simultaneously.


<div style="width: 780px; height: 650px; overflow: hidden;">
    <iframe src="/plots/confidence_threshold_plot_with_slider_darkmode.html"
            width="100%"
            height="100%"
            frameborder="0"
            scrolling="no"
            style="overflow: hidden;">
    </iframe>
</div>

!!! note
    The Early Stopping feature is supported for the Classification and Comparison workflows. The number of categories is the number of options in the Classification task. For the Comparison task, the number of categories is always 2.

### Using Confidence Stopping in Your Job

You simply add the `confidence_threshold` parameter when creating the job definition.

#### Example: Classification Job with Confidence Stopping

```python
from rapidata import RapidataClient

client = RapidataClient()

audience = client.audience.create_audience(name="Animal Classification Audience")
audience.add_classification_example(
    instruction="What do you see in the image?",
    answer_options=["Cat", "Dog"],
    datapoint="https://assets.rapidata.ai/cat.jpeg",
    truth=["Cat"]
)

audience.start_recruiting() # (1)!

job_definition = client.job.create_classification_job_definition(
    name="Test Classification with Early Stopping",
    instruction="What do you see in the image?",
    answer_options=["Cat", "Dog"],
    datapoints=["https://assets.rapidata.ai/dog.jpeg"],
    responses_per_datapoint=50, # (2)!
    confidence_threshold=0.99, # (3)!
)

job = audience.assign_job(job_definition)
job.view()
job.display_progress_bar()
results = job.get_results()
print(results)
```

1. Starts recruiting once all qualification examples are added and reviewed. Adding examples does not start recruiting on its own.
2. Sets the **maximum** number of responses per datapoint.
3. Stops collecting once 99% confidence is reached — for clear-cut tasks like this, expect roughly 4 responses.

### When to Use Confidence Stopping

We recommend using Confidence Stopping when:

- **Cost Efficiency**: You want to optimize costs by reducing the number of responses per datapoint.
- **Clear Correct Answer**: The task has a clear correct answer, and you're not interested in a distribution.

### Analyzing Confidence Stopping Results

When using Confidence Stopping, the [results](understanding_the_results.md) will additionally include a `confidencePerCategory` field for each datapoint. This field shows the confidence level for each of the categories in the task.

Example:
```json
{
    "info": {
        "createdAt": "2099-12-30T00:00:00.000000+00:00",
        "version": "3.0.0",
        "type": "Classify"
    },
    "results": [
        {
            "identifier": "dog.jpeg",
            "originalFileName": "dog.jpeg",
            "assetUrl": "https://assets.rapidata.ai/<random-uuid>.jpeg",
            "aggregatedResults": {
                "Dog": 4,
                "Cat": 0
            },
            "aggregatedResultsRatios": {
                "Dog": 1.0,
                "Cat": 0.0
            },
            "summedUserScores": {
                "Dog": 2.0865,
                "Cat": 0.0
            },
            "summedUserScoresRatios": {
                "Dog": 1.0,
                "Cat": 0.0
            },
            # this only appears when using early stopping
            "confidencePerCategory": {
                "Dog": 0.9943,
                "Cat": 0.0057
            },
            "detailedResults": [
                {
                    "selectedCategory": "Dog",
                    "userDetails": {
                        "country": "PT",
                        "language": "pt",
                        "userScores": { "global": 0.3 }
                    }
                },
                {
                    "selectedCategory": "Dog",
                    "userDetails": {
                        "country": "RS",
                        "language": "sr",
                        "userScores": { "global": 0.8486 }
                    }
                },
                {
                    "selectedCategory": "Dog",
                    "userDetails": {
                        "country": "SG",
                        "language": "en",
                        "userScores": { "global": 0.4469 }
                    }
                },
                {
                    "selectedCategory": "Dog",
                    "userDetails": {
                        "country": "IN",
                        "language": "en",
                        "userScores": { "global": 0.4911 }
                    }
                }
            ]
        }
    ],
    "summary": {
        "Dog": 4,
        "Cat": 0
    }
}
```
