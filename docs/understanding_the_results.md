# Interpreting the Results

After running your order and collecting responses, you'll receive a structured result containing valuable insights from the annotators. Understanding each component of this result is crucial for analyzing and utilizing the data effectively.

Here's an example of the results you might receive when running the [Quickstart order](/rapidata-python-sdk/quickstart/) (for simplicity, this example uses only 3 responses):

```json
{
  "info": {
    "createdAt": "2099-12-30T00:00:00.000000+00:00",
    "version": "3.0.0"
  },
  "results": {
    "globalAggregatedData": {
      "Fish": 0,
      "Cat": 0,
      "Wallaby": 3,
      "Airplane": 0
    },
    "data": [
      {
        "originalFileName": "wallaby.jpg",
        "aggregatedResults": {
          "Fish": 0,
          "Cat": 0,
          "Wallaby": 3,
          "Airplane": 0
        },
        "aggregatedResultsRatios": {
          "Fish": 0.0,
          "Cat": 0.0,
          "Wallaby": 1.0,
          "Airplane": 0.0
        },
        "summedUserScores": {
          "Fish": 0.0,
          "Cat": 0.0,
          "Wallaby": 1.77,
          "Airplane": 0.0
        },
        "summedUserScoresRatios": {
          "Fish": 0.0,
          "Cat": 0.0,
          "Wallaby": 1.0,
          "Airplane": 0.0
        },
        "detailedResults": [
          {
            "selectedCategory": "Wallaby",
            "userDetails": {
              "country": "DZ",
              "language": "ar",
              "userScore": 0.6409
            }
          },
          {
            "selectedCategory": "Wallaby",
            "userDetails": {
              "country": "EG",
              "language": "ar",
              "userScore": 0.7608
            }
          },
          {
            "selectedCategory": "Wallaby",
            "userDetails": {
              "country": "DZ",
              "language": "ar",
              "userScore": 0.3683
            }
          }
        ]
      }
    ]
  }
}
```

## Breakdown of the Results

1. `info`
    - `createdAt`: The timestamp indicating when the results overview was generated, in UTC time.
    - `version`: The version of the aggregator system that produced the results.
2. `results`:
This section contains the actual data collected from the annotators. The structure may vary slightly depending on the type of order, but the general idea stays the same. For classification orders, it includes:
    - `globalAggregatedData`: Aggregated counts of all votes across all datapoints for each category
    ```json
    "globalAggregatedData": {
        "Fish": 0,
        "Cat": 0,
        "Wallaby": 3,
        "Airplane": 0
    }
    ```
    - `data`: A list of results for each individual datapoint (e.g., each image/media or text you had labeled). Note that the order of datapoints may not match the order you submitted them in.

Each item in the data list contains:

- `originalFileName`: The name or identifier of the original file or datapoint.

    ```json
    "originalFileName": "wallaby.jpg"
    ```

- `aggregatedResults`: The total number of votes each category received for this specific datapoint.

    ```json
    "aggregatedResults": {
        "Fish": 0,
        "Cat": 0,
        "Wallaby": 3,
        "Airplane": 0
    }
    ```

- `aggregatedResultsRatios`: The proportion of votes each category received, calculated as the number of votes for the category divided by the total number of votes for the datapoint.

    ```json
    "aggregatedResultsRatios": {
        "Fish": 0.0,
        "Cat": 0.0,
        "Wallaby": 1.0,
        "Airplane": 0.0
    }
    ```
    
    In this example, all annotators selected "Wallaby," resulting in a ratio of 1.0 (or 100%) for that category.

- `summedUserScores`: The sum of the annotators' userScore values for each category. This metric accounts for the reliability of each annotator's response.

    ```json
    "summedUserScores": {
        "Fish": 0.0,
        "Cat": 0.0,
        "Wallaby": 1.77,
        "Airplane": 0.0
    }    
    ```

- `summedUserScoresRatios`: The proportion of the summed user scores for each category, providing a weighted ratio based on annotator reliability.

    ```json
    "summedUserScoresRatios": {
        "Fish": 0.0,
        "Cat": 0.0,
        "Wallaby": 1.0,
        "Airplane": 0.0
    }
    ```

- `detailedResults`: A list of individual responses from each annotator, including:
    - `selectedCategory`: The category chosen by the annotator.
    - `userDetails`: Information about the annotator.
        - `country`: Country code of the annotator.
        - `language`: Language in which the annotator viewed the task.
        - `userScore`: A score representing the annotator's reliability.

    Example:

    ```json
    {
    "selectedCategory": "Wallaby",
    "userDetails": {
        "country": "DZ",
        "language": "ar",
        "userScore": 0.6409
        }
    }
    ```

## Understanding the User Scores

The `userScore` is a value between 0 and 1 (1 can never be reached, but can appear because of rounding) that indicates the reliability or trustworthiness of an annotator's responses. A higher score suggests that the annotator consistently provides accurate and reliable answers.

### How is it Calculated?

The `userScore` is derived from the annotator's performance on **Validation Tasks**—tasks with known correct answers. By evaluating how accurately an annotator completes these tasks, we assign a score that reflects their understanding and adherence to the task requirements. It is not simply the accuracy, as it also takes into account the difficulties of the tasks, but strongly related to it.

To know more about the Validation Tasks have a look at the [Improve Order Quality](improve_order_quality.md) guide.

### Why is it Important?

- **Weighted Analysis**: Responses from annotators with higher `userScores` can be given more weight, improving the overall quality of the aggregated results.
- **Quality Control**: It helps in identifying and filtering for the most reliable responses.
- **Insight into Annotator Performance**: Provides transparency into who is contributing to your data and how reliably.

## Notes on Data Ordering

The datapoints in the `data` list may not be in the same order as you submitted them. You can use the `originalFileName` to match the results to your original data.

## Utilizing the Results
- **Aggregated Insights**: Use `aggregatedResults` and `aggregatedResultsRatios` to understand the general consensus among annotators for each datapoint.
- **Weighted Decisions**: Consider `summedUserScores` and `summedUserScoresRatios` to make decisions based on annotator reliability.
- **Detailed Analysis**: Explore `detailedResults` to see individual responses and gather insights about annotator demographics and performance.

## Conclusion

By thoroughly understanding each component of the results, you can effectively interpret the data and make informed decisions. Leveraging the userScore and [validation sets](improve_order_quality.md) ensures high-quality, reliable data for your projects.
