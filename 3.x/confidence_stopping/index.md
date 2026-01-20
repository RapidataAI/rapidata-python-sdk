# Early Stopping Based on Confidence

To improve the efficiency and cost-effectiveness of your data labeling tasks, Rapidata offers an Early Stopping feature based on confidence thresholds. This feature allows you to automatically stop collecting responses for a datapoint once a specified confidence level is reached, saving time and resources without compromising quality.


## Why Use Early Stopping?

In traditional data labeling workflows, you might request a fixed number of responses per datapoint to ensure accuracy. However, once a consensus is reached with high confidence, continuing to collect more responses becomes redundant and incurs unnecessary costs.

Early Stopping addresses this by:

- **Reducing Costs**: Stop collecting responses when sufficient confidence is achieved.
- **Improving Efficiency**: Accelerate the labeling process by focusing resources where they are most needed.
- **Maintaining Quality**: Ensure that each datapoint meets your specified confidence level before stopping.

## How it Works

The Early Stopping feature leverages the trustworthiness, quantified through their `userScores`, to calculate the confidence level of each category for any given datapoint.

### Confidence Calculation
- **UserScores**: Each labeler has a `userScore` between 0 and 1, representing their reliability. [More information](understanding_the_results.md#understanding-the-user-scores)
- **Aggregated Confidence**: By combining the userScores of labelers who selected a particular category, the system computes the probability that this category is the correct one.
- **Threshold Comparison**: If the calculated confidence exceeds your specified threshold, the system stops collecting further responses for that datapoint.

## Understanding the Confidence Threshold

We've created a plot based on empirical data aided by simulations to give you an estimate of the number of responses required to reach a certain confidence level.

There are a few things to keep in mind when interpreting the results:

- **Unambiguous Scenario**: The graph represents an ideal situation such as in the [example below](#using-early-stopping-in-your-job) with no ambiguity which category is the correct one. A counter-example would be subjective tasks like "Which image do you prefer?", where there's no clear correct answer.
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

>**Note:** The Early Stopping feature is supported for the Classification and Comparison workflows. The number of categories is the number of options in the Classification task. For the Comparison task, the number of categories is always 2.

## Using Early Stopping in Your Job

Implementing Early Stopping is straightforward. You simply add the confidence threshold as a parameter when creating the job definition.

### Example: Classification Job with Early Stopping

```python
from rapidata import RapidataClient

client = RapidataClient()

# Create audience with qualification example
audience = client.audience.create_audience(name="Animal Classification Audience")
audience.add_classification_example(
    instruction="What do you see in the image?",
    answer_options=["Cat", "Dog"],
    datapoint="https://assets.rapidata.ai/cat.jpeg",
    truth=["Cat"]
)

# Create job definition with early stopping
job_definition = client.job.create_classification_job_definition(
    name="Test Classification with Early Stopping",
    instruction="What do you see in the image?",
    answer_options=["Cat", "Dog"],
    datapoints=["https://assets.rapidata.ai/dog.jpeg"],
    responses_per_datapoint=50,
    confidence_threshold=0.99,
)

# Preview and run
job_definition.preview()
job = audience.assign_job(job_definition)
job.display_progress_bar()
results = job.get_results()
print(results)
```

In this example:

- `responses_per_datapoint=50`: Sets the maximum number of responses per datapoint.
- `confidence_threshold=0.99`: Specifies that data collection for a datapoint should stop once a 99% confidence level is reached.

We'd expect this to take roughly 4 responses to reach the 99% confidence level.

## When to Use Early Stopping

We recommend using Early Stopping when:

- **Cost Efficiency**: You want to optimize costs by reducing the number of responses per datapoint.
- **Clear Correct Answer**: The task has a clear correct answer, and you're not interested in a distribution.

## Analyzing Early Stopping Results

When using Early Stopping, the [results](understanding_the_results.md) will additionally include a `confidencePerCategory` field for each datapoint. This field shows the confidence level for each of the categories in the task.

Example:
```json
{
    "info": {
        "createdAt": "2099-12-30T00:00:00.000000+00:00",
        "version": "3.0.0"
    },
    "results": {
        "globalAggregatedData": {
            "Dog": 4,
            "Cat": 0
        },
        "data": [
            {
                "originalFileName": "dog.jpeg",
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
                            "userScore": 0.3
                        }
                    },
                    {
                        "selectedCategory": "Dog",
                        "userDetails": {
                            "country": "RS",
                            "language": "sr",
                            "userScore": 0.8486
                        }
                    },
                    {
                        "selectedCategory": "Dog",
                        "userDetails": {
                            "country": "SG",
                            "language": "en",
                            "userScore": 0.4469
                        }
                    },
                    {
                        "selectedCategory": "Dog",
                        "userDetails": {
                            "country": "IN",
                            "language": "en",
                            "userScore": 0.4911
                        }
                    }
                ]
            }
        ]
    }
}
```
