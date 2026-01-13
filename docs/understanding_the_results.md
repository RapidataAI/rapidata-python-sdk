# Interpreting the Results

After running your job and collecting responses, you'll receive a structured result containing valuable insights from the labelers. Understanding each component of this result is crucial for analyzing and utilizing the data effectively.

Here's an example of the results you might receive when running a COMPARE task (for simplicity, this example uses 3 responses):

```json
{
  "info": {
    "createdAt": "2025-02-11T07:31:59.353232+00:00",
    "version": "3.0.0"
  },
  "summary": {
    "A_wins_total": 0,
    "B_wins_total": 1
  },
  "results": [
    {
      "context": "A small blue book sitting on a large red book.",
      "winner_index": 1,
      "winner": "dalle-3_37_2.jpg",
      "aggregatedResults": {
        "aurora-20-1-25_37_4.png": 0,
        "dalle-3_37_2.jpg": 3
      },
      "aggregatedResultsRatios": {
        "aurora-20-1-25_37_4.png": 0.0,
        "dalle-3_37_2.jpg": 1.0
      },
      "summedUserScores": {
        "aurora-20-1-25_37_4.png": 0.0,
        "dalle-3_37_2.jpg": 1.196
      },
      "summedUserScoresRatios": {
        "aurora-20-1-25_37_4.png": 0.0,
        "dalle-3_37_2.jpg": 1.0
      },
      "detailedResults": [
          {
              "votedFor": "dalle-3_37_2.jpg",
              "userDetails": {
                  "country": "BY",
                  "language": "ru",
                  "userScores": {
                      "global": 0.4469
                  },
                  "age": "Unknown",
                  "gender": "Unknown",
                  "occupation": "Unknown"
              }
          },
          {
              "votedFor": "dalle-3_37_2.jpg",
              "userDetails": {
                  "country": "LY",
                  "language": "ar",
                  "userScores": {
                      "global": 0.3923
                  },
                  "age": "0-17",
                  "gender": "Other",
                  "occupation": "Other Employment"
              }
          },
          {
              "votedFor": "dalle-3_37_2.jpg",
              "userDetails": {
                  "country": "BY",
                  "language": "ru",
                  "userScores": {
                      "global": 0.3568
                  },
                  "age": "0-17",
                  "gender": "Other",
                  "occupation": "Healthcare"
              }
          }
      ]
    }
  ]
}
```

## Breakdown of the Results

1. `info`
    - `createdAt`: The timestamp indicating when the results overview was generated, in UTC time.
    - `version`: The version of the aggregator system that produced the results.

2. `summary`
    - `A_wins_total`: The total number of comparisons won by option A (index 0) across all pairs
    - `B_wins_total`: The total number of comparisons won by option B (index 1) across all pairs

3. `results`: This section contains the actual comparison data collected from the labelers. For comparison jobs, each item includes:

    - `context`: The prompt or description provided for the comparison task
    - `winner_index`: Index of the winning option (0 for first option, 1 for second option)
    - `winner`: Filename or identifier of the winning option
    
    - `aggregatedResults`: The total number of responses each option received for this specific comparison.
        ```json
        "aggregatedResults": {
            "aurora-20-1-25_37_4.png": 0,
            "dalle-3_37_2.jpg": 3
        }
        ```

    - `aggregatedResultsRatios`: The proportion of responses each option received, calculated as the number of responses for the option divided by the total number of responses.
        ```json
        "aggregatedResultsRatios": {
            "aurora-20-1-25_37_4.png": 0.0,
            "dalle-3_37_2.jpg": 1.0
        }
        ```

    - `summedUserScores`: The sum of the labelers' global userScore values for each option. This metric accounts for the reliability of each labeler's response.
        ```json
        "summedUserScores": {
            "aurora-20-1-25_37_4.png": 0.0,
            "dalle-3_37_2.jpg": 1.196
        }
        ```

    - `summedUserScoresRatios`: The proportion of the summed global userScores for each option, providing a weighted ratio based on labeler reliability.
        ```json
        "summedUserScoresRatios": {
            "aurora-20-1-25_37_4.png": 0.0,
            "dalle-3_37_2.jpg": 1.0
        }
        ```

    - `detailedResults`: A list of individual responses from each labeler, including:
        - `votedFor`: The option chosen by the labeler
        - `userDetails`: Information about the labeler
            - `country`: Country code of the labeler
            - `language`: Language in which the labeler viewed the task
            - `userScores`: A score representing the labeler's reliability across different dimensions
                - `global`: The global userScore of the labeler, which is a measure of their overall reliability
            - `age`: Age group of the labeler
            - `gender`: The gender of the labeler
            - `occupation`: The occupation of the labeler

## Understanding the User Scores

The `userScore` is a value between 0 and 1 (1 can never be reached, but can appear because of rounding) that indicates the reliability or trustworthiness of a labeler's responses. A higher score suggests that the labeler consistently provides accurate and reliable answers.

### How is it Calculated?

The `userScore` is derived from the labeler's performance on **Qualification Tasks**—tasks with known correct answers. By evaluating how accurately a labeler completes these tasks, we assign a score that reflects their understanding and adherence to the task requirements. It is not simply the accuracy, as it also takes into account the difficulties of the tasks, but strongly related to it.

For most tasks, the `global` userScore is the most relevant and can be used per default. If you need more specific information, you may contact us directly at <info@rapidata.ai>.

Qualification tasks are examples with known correct answers that labelers must pass before working on your data.

### Why is it Important?

- **Weighted Analysis**: Responses from labelers with higher `userScores` can be given more weight, improving the overall quality of the aggregated results.
- **Quality Control**: It helps in identifying and filtering for the most reliable responses.
- **Insight into Labeler Performance**: Provides transparency into who is contributing to your data and how reliably.

## Utilizing the Results

- **Clear Winners**: Use `winner` and `winner_index` to quickly identify which option was preferred. It is calculated based on the global userScores.
- **Aggregated Insights**: Use `aggregatedResults` and `aggregatedResultsRatios` to understand the strength of preference between options
- **Weighted Decisions**: Consider `summedUserScores` and `summedUserScoresRatios` to make decisions based on annotator reliability
- **Detailed Analysis**: Explore `detailedResults` to see individual responses and gather insights about labeler demographics and performance

## Conclusion

By thoroughly understanding each component of the results, you can effectively interpret the data and make informed decisions. Leveraging the userScore and qualification examples ensures high-quality, reliable data for your projects.
