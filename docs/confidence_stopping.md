# Adaptive Stopping

Adaptive stopping ends response collection for a datapoint once a stopping condition is met, so you pay for the responses that change the outcome and not for the ones after it.

You choose the stopping rule with `responses_per_datapoint`:

| Value | Rule | Job types |
|-------|------|-----------|
| `AdaptiveStopping()` | Stops each pair once its verdict is statistically settled. **Default for compare jobs.** | Compare |
| `QuorumStopping(threshold, max_responses)` | Stops once `threshold` responses agree. | Classification, Compare |
| an `int` | Collects exactly that many responses. Default (`10`) for every other job type. | All |

## How it Works

Each vote on a compare pair is weighted by the voter's [user score](understanding_the_results.md#understanding-the-user-scores) at the time the vote was cast. After every vote, the pair is checked against three outcomes:

- **`"A"` or `"B"`**: one side is preferred, with at least `min_confidence` certainty.
- **`"ambiguous"`**: the pair is too close to call — the true preference lies inside the ambiguous band, 20/80 to 80/20 by default — so further votes would not produce a winner.
- **`"undecided"`**: neither happened before `max_responses` votes.
- **`"open"`**: no verdict yet — the pair is still collecting, or the job was paused or stopped before it finished. `max_responses` is a safety cap: with the defaults, no pair comes close to it.

The pair stops at the first verdict. A clear pair stops after as few as 7 votes and a 50/50 pair after about 16. On past compare jobs a pair needed about 25 votes on average, which is what the [cost estimate](cost_estimates.md) is priced with; the hardest pairs, split around 35/65, need about 31.

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

`ambiguity_range` is the width of the ambiguous band, centred on an even split: the default 0.6 gives 20/80–80/20.

**Lower `ambiguity_range` to push closer pairs to a winner, at the cost of more votes.** For example, `AdaptiveStopping(ambiguity_range=0.5)` narrows the band to 25/75–75/25, which takes about a third more votes per pair on average, and about 49 for the hardest pairs; `0.3` narrows it to 35/65–65/35.

The range only decides which pairs may stop as ambiguous. A winner always takes priority, so a 70/30 pair can still return `"A"` or `"B"` even though it lies inside the band.

Because each pair stops at a different point, the [cost estimate](cost_estimates.md) `estimated_cost` is the expected cost of the job.

## Analyzing Adaptive Stopping Results

Each compare datapoint in the [results](understanding_the_results.md) gains:

- `verdict`: `"A"`, `"B"`, `"ambiguous"`, `"undecided"`, or `"open"`.
- `responses`: the number of votes the rule counted — where the pair stopped, or the count so far for an open pair.
- `stoppingState`: the raw state behind the verdict — the weighted votes for each side (`weightA`, `weightB`), the confidence bounds on the share of B (`csLower`, `csUpper`), and the `minConfidence` and `ambiguityRange` used.

```python
results = job.get_results()
for datapoint in results["results"]:
    print(datapoint["verdict"], datapoint["responses"])
```

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

## Confidence Stopping (deprecated)

!!! warning
    The `confidence_threshold` parameter is deprecated and emits a `DeprecationWarning`. For compare jobs use `AdaptiveStopping`; for classification use `QuorumStopping`. It still works with an `int` `responses_per_datapoint` as the cap, and cannot be combined with `AdaptiveStopping` or `QuorumStopping`.

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
