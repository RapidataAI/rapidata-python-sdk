# Adaptive Stopping

Adaptive stopping ends response collection for a datapoint once a stopping condition is met, so you pay for the responses that change the outcome and not for the ones after it.

You choose the stopping rule with `responses_per_datapoint`:

| Value | Rule | Job types |
|-------|------|-----------|
| `AdaptiveStoppingReferee()` | Stops each pair once its verdict is statistically settled. **Default for compare jobs.** | Compare |
| an `int` | Collects exactly that many responses. Default (`10`) for every other job type. | All |

[Quorum Stopping](#quorum-stopping) is still available through `quorum_threshold`.

## How it Works

Each vote on a compare pair is weighted by the voter's [user score](understanding_the_results.md#understanding-the-user-scores). After every vote, the pair is checked for a verdict:

- **`Decided`**: one option is preferred, with at least `min_confidence` certainty.
- **`Ambiguous`**: the pair is a toss-up. Voters are split too evenly for either option to win clearly. By default, that means neither option would get more than about 80% of the votes, so more votes would not produce a winner.
- **`Undecided`**: neither happened before `max_votes` votes. `max_votes` is a hard cap that the defaults never reach: every pair reaches a verdict in under 80 votes.
- **`Open`**: no verdict yet. The pair is still collecting, or the job was paused or stopped before it finished.

The pair stops at the first verdict. A clear pair stops after as few as 7 votes and a 50/50 pair after about 16. A pair needs about 21 votes on average; the hardest pairs, split around 35/65, need about 31.

## Using Adaptive Stopping in Your Job

Compare jobs use adaptive stopping unless you pass something else:

```python
from rapidata import RapidataClient, AdaptiveStoppingReferee

client = RapidataClient()

job_definition = client.job.create_compare_job_definition(
    name="Prompt alignment",
    instruction="Which image matches the description better?",
    datapoints=[["https://assets.rapidata.ai/a.jpg", "https://assets.rapidata.ai/b.jpg"]],
    contexts=["A small blue book sitting on a large red book."],
    responses_per_datapoint=AdaptiveStoppingReferee(), # (1)!
)
```

1. The same as leaving the argument out. Pass `responses_per_datapoint=15` to collect exactly 15 responses per pair instead.

`ambiguity_threshold` sets how even the split must be before a pair is called a toss-up. With the default 0.64, a pair is a toss-up when neither option would get more than about 80% of the votes.

**Raise `ambiguity_threshold` to resolve less decisive pairs, at the cost of more votes.** For example, `AdaptiveStoppingReferee(ambiguity_threshold=0.75)` resolves pairs down to a 75%/25% split: a pair is a toss-up only when neither option would get more than about 75% of the votes. That takes about a third more votes per pair on average, and about 49 for the hardest pairs. With `0.91`, the limit is about 65%.

The threshold only decides which pairs may stop as a toss-up. A clear winner always takes priority, so a pair where one option gets 70% of the votes can still end `Decided`.

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `min_confidence` | 0.9 | How certain the result must be before a winner is called, between 0 and 1. |
| `ambiguity_threshold` | 0.64 | How even the split must be before a pair is called a toss-up, between 0 and 1. Higher calls fewer pairs a toss-up and costs more votes. |
| `max_votes` | 100 | The hard cap on votes per pair. With the default `min_confidence` and `ambiguity_threshold`, no pair can reach it: every pair reaches a verdict in under 80 votes. |

A parameter left as `None` uses the default above, and a saved job definition shows the resolved values. Adaptive stopping is compare-only: passing it to any other job type raises a `ValueError` before anything is sent.

For now, there is no forecast for the expected response count, so the [cost estimate](cost_estimates.md) and [job progress](job_progress.md) use the `max_votes` setting per pair, which is well above the expected cost.

## Analyzing Adaptive Stopping Results

Each compare datapoint in the [results](understanding_the_results.md) gains an `adaptiveStoppingState`:

```json
"adaptiveStoppingState": {
    "verdict": "Decided",
    "winners": ["1"],
    "outcomes": {
        "0": {"weight": 1.485, "lower": 0.004, "upper": 0.496},
        "1": {"weight": 10.515, "lower": 0.504, "upper": 0.996}
    },
    "responseCount": 12,
    "minConfidence": 0.9,
    "ambiguityThreshold": 0.64
}
```

- `outcomes` is keyed by option: `"0"` is the first asset of the pair, `"1"` the second. `winners` names the winning key and is only filled for `Decided`.
- `verdict` is final once it is not `Open`, together with the `outcomes` and `responseCount` at that moment.
- `weight` is the option's user-score-weighted votes, scaled so all weights add up to `responseCount`.
- `lower` and `upper` bound the option's share of the vote at the chosen confidence.
- With `Undecided`, `outcomes` can be empty when every response was a skip.

```python
results = job.get_results()
for datapoint in results["results"]:
    state = datapoint["adaptiveStoppingState"]
    print(state["verdict"], state["winners"], state["responseCount"])
```

`results.to_pandas()` flattens the state into columns such as `adaptiveStoppingState_verdict`. The SDK passes the values through unchanged.

---

## Quorum Stopping

### How it Works

Quorum Stopping uses a simple vote-counting approach. A task is completed when:

1. A minimum number of responses (`quorum_threshold`) agree on the same answer, **OR**
2. Quorum becomes mathematically impossible to reach, **OR**
3. The maximum number of votes (`responses_per_datapoint`) is reached.

For example, with `quorum_threshold=7` and `responses_per_datapoint=10`:

- The task completes when 7 responses agree (quorum reached).
- The task completes when both options have 4+ responses (quorum is impossible since neither can reach 7 out of 10).
- The task completes after 10 total votes if neither condition is met.

!!! note
    Quorum Stopping is supported for the Classification and Comparison workflows. On a compare job, pass an `int` `responses_per_datapoint` as the cap; it is 10 when omitted.

### Using Quorum Stopping in Your Job

You add the `quorum_threshold` parameter when creating the job definition.

#### Example: Classification Job with Quorum Stopping

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
    name="Test Classification with Quorum Stopping",
    instruction="What do you see in the image?",
    answer_options=["Cat", "Dog"],
    datapoints=["https://assets.rapidata.ai/dog.jpeg"],
    responses_per_datapoint=10, # (2)!
    quorum_threshold=7, # (3)!
)

job = audience.assign_job(job_definition)
job.view()
job.display_progress_bar()
results = job.get_results()
print(results)
```

1. Starts recruiting once all qualification examples are added and reviewed. Adding examples does not start recruiting on its own.
2. Sets the **maximum** number of responses per datapoint.
3. Stops collecting once 7 responses agree on the same answer.

### When to Use Quorum Stopping

Quorum Stopping is a good choice when:

- **Simplicity**: You want a straightforward stopping rule based on raw vote counts rather than statistical confidence.
- **Predictable Costs**: You want to set an upper bound on responses while still allowing early termination.
- **Clear Correct Answer**: The task has a clear correct answer, and you expect most labelers to agree.

---

## Confidence Stopping

!!! warning "Deprecated"
    `confidence_threshold` is deprecated and emits a `DeprecationWarning`. For compare jobs use adaptive stopping, the default. For classification use `quorum_threshold` or a fixed `responses_per_datapoint`.

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
    Confidence Stopping is supported for the Classification and Comparison workflows. The number of categories is the number of options in the Classification task. For the Comparison task, the number of categories is always 2.

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
