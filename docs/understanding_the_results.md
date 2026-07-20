# Interpreting the Results

After running your job and collecting responses, you'll receive a structured result containing valuable insights from the labelers. Understanding each component of this result is crucial for analyzing and utilizing the data effectively.

Here's an example of the results you might receive when running a COMPARE task (for simplicity, this example uses 3 responses):

```json
{
  "info": {
    "createdAt": "2026-07-13T11:07:53.577348+00:00",
    "version": "4.1.0",
    "type": "Compare",
    "name": "Example Image Prompt Alignment",
    "instruction": "Which image matches the description better?"
  },
  "results": [
    {
      "context": "A small blue book sitting on a large red book.",
      "winner_index": 1,
      "winner": "flux-1-pro_37_0.jpg",
      "rawWinnerIndex": 1,
      "rawWinner": "flux-1-pro_37_0.jpg",
      "weightedWinnerIndex": 1,
      "weightedWinner": "flux-1-pro_37_0.jpg",
      "assetUrls": {
        "midjourney-5.2_37_3.jpg": "https://assets.rapidata.ai/f8bb5e14-fbba-4f8a-a3dd-88530b5eae48.jpg",
        "flux-1-pro_37_0.jpg": "https://assets.rapidata.ai/e8563fc4-a452-4557-9ab2-d0f06d09ccd7.jpg"
      },
      "aggregatedResults": {
        "midjourney-5.2_37_3.jpg": 0,
        "flux-1-pro_37_0.jpg": 3
      },
      "aggregatedResultsRatios": {
        "midjourney-5.2_37_3.jpg": 0.0,
        "flux-1-pro_37_0.jpg": 1.0
      },
      "summedUserScores": {
        "midjourney-5.2_37_3.jpg": 0.0,
        "flux-1-pro_37_0.jpg": 2.552
      },
      "summedUserScoresRatios": {
        "midjourney-5.2_37_3.jpg": 0.0,
        "flux-1-pro_37_0.jpg": 1.0
      },
      "detailedResults": [
          {
              "votedFor": "flux-1-pro_37_0.jpg",
              "userDetails": {
                  "country": "EG",
                  "language": "ar",
                  "userScores": {
                      "global": 0.845
                  },
                  "demographics": {
                      "age": "18-29",
                      "gender": "Other",
                      "occupation": "Not currently working"
                  }
              }
          },
          {
              "votedFor": "flux-1-pro_37_0.jpg",
              "userDetails": {
                  "country": "BD",
                  "language": "en",
                  "userScores": {
                      "global": 0.8349
                  },
                  "demographics": {
                      "age": "65+",
                      "gender": "Other",
                      "occupation": "Retired"
                  }
              }
          },
          {
              "votedFor": "flux-1-pro_37_0.jpg",
              "userDetails": {
                  "country": "ES",
                  "language": "es",
                  "userScores": {
                      "global": 0.8721
                  },
                  "demographics": {
                      "age": "0-17",
                      "gender": "Female",
                      "occupation": "Not currently working"
                  }
              }
          }
      ]
    }
  ],
  "summary": {
    "A_wins_total": 0,
    "B_wins_total": 1
  }
}
```

## Breakdown of the Results

1. `info`
    - `createdAt`: The timestamp indicating when the results overview was generated, in UTC time.
    - `version`: The version of the aggregator system that produced the results.
    - `type`: The type of task that was run (e.g. `Compare`, `Classify`).
    - `name`: The name given to the job or order.
    - `instruction`: The instruction that was shown to the labelers.

2. `results`: This section contains the actual comparison data collected from the labelers. For comparison jobs, each item includes:

    - `context`: The context shown alongside this datapoint (present when `contexts` were provided for the job)
    - `winner` / `winner_index`: **Deprecated aliases** of `weightedWinner` / `weightedWinnerIndex` (see below) — kept for backward compatibility. They always carry the *weighted* winner and, unlike the explicit fields, are never `null` (ties are broken toward the first option). Prefer `rawWinner*` / `weightedWinner*` in new code.
    - `rawWinnerIndex` / `rawWinner`: The **raw-majority** winner — the option with the most responses, i.e. `argmax` of `aggregatedResults`. `rawWinnerIndex` is the option's position in the ordered option list (`0` = first asset, `1` = second; `Both` / `Neither` appear as trailing indexes when they received votes); `rawWinner` is its identifier. Both are `null` when there is **no clear winner** (nothing was voted, or the top count is tied across options).
    - `weightedWinnerIndex` / `weightedWinner`: The **reliability-weighted** winner — `argmax` of `summedUserScores`, so more-reliable labelers count for more. Same index space and same `null`-on-tie behavior as the raw winner. On close votes the raw and weighted winners can differ; this is exactly why both are surfaced explicitly rather than through a single generic `winner`.

    !!! note
        `rawWinner*` / `weightedWinner*` are emitted by aggregator version `4.1.0` and later (see `info.version`). Results generated by an older aggregator won't contain these keys until their pipeline is re-run — `winner` / `winner_index` are always present as a fallback.

    - `assetUrls`: Maps each option to the URL under which the asset is hosted by Rapidata — the exact file that was shown to the labelers. The hosted files are not encrypted, but are assigned a random UUID name so they can't be accessed by guessing URLs.
        ```json
        "assetUrls": {
            "midjourney-5.2_37_3.jpg": "https://assets.rapidata.ai/f8bb5e14-fbba-4f8a-a3dd-88530b5eae48.jpg",
            "flux-1-pro_37_0.jpg": "https://assets.rapidata.ai/e8563fc4-a452-4557-9ab2-d0f06d09ccd7.jpg"
        }
        ```

    - `aggregatedResults`: The total number of responses each option received for this specific comparison.
        ```json
        "aggregatedResults": {
            "midjourney-5.2_37_3.jpg": 0,
            "flux-1-pro_37_0.jpg": 3
        }
        ```

    - `aggregatedResultsRatios`: The proportion of responses each option received, calculated as the number of responses for the option divided by the total number of responses.
        ```json
        "aggregatedResultsRatios": {
            "midjourney-5.2_37_3.jpg": 0.0,
            "flux-1-pro_37_0.jpg": 1.0
        }
        ```

    - `summedUserScores`: For each option, the sum over the labelers who chose it of that labeler's aggregated `userScore` (the mean of their `userScores` dimensions, which is just the `global` score in the common single-dimension case). This is reliability-weighted vote mass, and `weightedWinner` is the `argmax` of this dict.
        ```json
        "summedUserScores": {
            "midjourney-5.2_37_3.jpg": 0.0,
            "flux-1-pro_37_0.jpg": 2.552
        }
        ```

    - `summedUserScoresRatios`: `summedUserScores` normalized to sum to 1 — each option's summed score divided by the total across all options — giving a reliability-weighted proportion directly comparable to `aggregatedResultsRatios` (the unweighted proportion).
        ```json
        "summedUserScoresRatios": {
            "midjourney-5.2_37_3.jpg": 0.0,
            "flux-1-pro_37_0.jpg": 1.0
        }
        ```

    - `detailedResults`: A list of individual responses from each labeler, including:
        - `votedFor`: The option chosen by the labeler
        - `userDetails`: Information about the labeler
            - `country`: Country code of the labeler
            - `language`: Language in which the labeler viewed the task
            - `userScores`: A score representing the labeler's reliability across different dimensions
                - `global`: The global userScore of the labeler, which is a measure of their overall reliability
            - `demographics`: Demographic attributes collected for the labeler, keyed by attribute name (e.g. `age`, `gender`, `occupation`). May be empty if no demographic data was collected for the labeler.

3. `summary`
    - `A_wins_total`: The total number of comparisons won by option A (index 0) across all pairs
    - `B_wins_total`: The total number of comparisons won by option B (index 1) across all pairs

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

- **Clear Winners**: Use `weightedWinner` / `weightedWinnerIndex` (reliability-weighted) or `rawWinner` / `rawWinnerIndex` (raw majority) to identify which option was preferred — and be explicit about which notion of "won" you mean, since the two can differ on close votes. Both are `null` when there is no clear winner. The generic `winner` / `winner_index` are deprecated aliases of the weighted fields; prefer the explicit names.
- **Aggregated Insights**: Use `aggregatedResults` and `aggregatedResultsRatios` to understand the strength of preference between options
- **Weighted Decisions**: Consider `summedUserScores` and `summedUserScoresRatios` to make decisions based on annotator reliability
- **Detailed Analysis**: Explore `detailedResults` to see individual responses and gather insights about labeler demographics and performance

## Conclusion

By thoroughly understanding each component of the results, you can effectively interpret the data and make informed decisions. Leveraging the userScore and qualification examples ensures high-quality, reliable data for your projects.
