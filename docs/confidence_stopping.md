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
- **UserScores**: Each annotator has a `userScore` between 0 and 1, representing their reliability. [More information](/rapidata-python-sdk/understanding_the_results/#understanding-the-user-scores)
- **Aggregated Confidence**: By combining the userScores of annotators who selected a particular category, the system computes the probability that this category is the correct one.
- **Threshold Comparison**: If the calculated confidence exceeds your specified threshold, the system stops collecting further responses for that datapoint.

## Understanding the Confidence Threshold Plot

To help you estimate the number of responses needed to reach different confidence levels, we've conducted a thousand simulations based on actual userScore distributions.

There are a few things to keep in mind when interpreting the results:

- **Ideal Scenario**: The graph represents an ideal situation with no ambiguity which category is the correct one.
- **Real-World Variability**: Actual required responses may vary based on task complexity.
- **Guidance Tool**: Use the graph as a guideline to set realistic expectations for your orders.
- **Response Overflow**: The number of responses per datapoint may exceed the specified amount due to multiple users answering simultaneously.


<div style="width: 780px; height: 650px; overflow: hidden;">
    <iframe src="/rapidata-python-sdk/plots/confidence_threshold_plot_with_slider_darkmode.html"
            width="100%" 
            height="100%" 
            frameborder="0" 
            scrolling="no"
            style="overflow: hidden;">
    </iframe>
</div>

The Early Stopping feature is supported for the Classification and Comparison workflows. The number of categories is the number of options in the Classification task. For the Comparison task, the number of categories is always 2.

## Using Early Stopping in Your Order

Implementing Early Stopping is straightforward. You simply add the .confidence_threshold() method when building your order.

### Example: Classification Order with Early Stopping

```python
order = (rapi
        .create_classify_order("Test Classification Order")
        .question("What do you see in the image?")
        .options(["Dog", "Cat"])
        .media(["https://assets.rapidata.ai/dog.jpeg"])
        .responses(50)
        .confidence_threshold(0.99)
        .run())

order.display_progress_bar()
result = order.get_results()
print(result)
```

In this example:

- responses(50): Sets the maximum number of responses per datapoint.
- confidence_threshold(0.99): Specifies that data collection for a datapoint should stop once a 99% confidence level is reached.

We'd expect this to take roughtly 4 responses to reach the 99% confidence level.

## When to Use Early Stopping

We recommend using Early Stopping when:

- **Cost Efficiency**: You want to optimize costs by reducing the number of responses per datapoint.
- **Clear Correct Answer**: The task has a clear correct answer, and you're not interested in a distribution.

## Analyzing Early Stopping Results

When using Early Stopping, the [results](/rapidata-python-sdk/understanding_the_results/) will additionally include a `confidencePerCategory` field for each datapoint. This field shows the confidence level for each of the categories in the task.

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
