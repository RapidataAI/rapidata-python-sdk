# Understanding the Results

`job.get_results()` returns a `RapidataResults` object, a `dict` holding the JSON below. Every job type shares the same top level:

```json
{
  "info": { ... },
  "results": [ ... ],
  "summary": { ... }
}
```

What one entry in `results` looks like depends on the job type. Jump to yours:

| Job type | `info.type` | One `results` entry is | `summary` |
| --- | --- | --- | --- |
| [Classification](#classification) | `Classification` | one datapoint | votes per category, all datapoints |
| [Compare](#compare) | `Compare` | one pair | wins per side, all pairs |
| [Ranking](#ranking) | `Ranking` | one ranking, with its matchups inside | none (each ranking has its own) |
| [Locate](#locate) | `Locate` | one datapoint | none |
| [Draw](#draw) | `Draw` | one datapoint | none |
| [Select Words](#select-words) | `SelectWords` | one datapoint | none |
| [Free Text](#free-text) | `FreeText` | one datapoint | none |

## Fields every job type shares

### `info`

| Field | Meaning |
| --- | --- |
| `createdAt` | When the results were generated, UTC |
| `version` | Version of the aggregator that produced them. Some fields only exist from a given version on |
| `type` | The job type, as in the table above |
| `name` | The job's name |
| `instruction` | The instruction shown to labelers |

### Which datapoint an entry belongs to

Datapoint-based results (everything except Compare and Ranking) identify the datapoint with:

| Field | Meaning |
| --- | --- |
| `identifier` | The URL you passed, else the original file name, else the text of a text datapoint. Use it to join results back to your input |
| `url` / `originalFileName` / `text` | Whichever of the three `identifier` came from |
| `assetUrl` | The Rapidata-hosted copy of the exact file labelers saw. Random UUID name; not encrypted |
| `context` / `mediaContext` | The context you attached to the datapoint, if any |
| `privateMetadata` | The `private_metadata` you attached to the datapoint, if any |

Keys that don't apply are left out, not set to `null`.

### `detailedResults`

Every entry carries a `detailedResults` list with one item per response. Each item has the labeler's answer (the field name depends on the job type and is listed in its section) and `userDetails`:

| Field | Meaning |
| --- | --- |
| `userId` | Pseudonymous id of the labeler (`rtr_…`): the same in all your jobs, so you can follow one labeler across them. It reveals nothing else about them. Missing from results computed before it was added |
| `country` | Labeler's country code |
| `language` | Language the labeler saw the task in |
| `userScores` | The labeler's reliability per dimension; `global` is the one to use by default. See [below](#understanding-the-user-scores) |
| `demographics` | Demographic attributes by name (e.g. `age`, `gender`, `occupation`). Can be empty |

## Classification

```json
{
  "info": { "type": "Classification", "version": "4.1.0", "name": "Cat or dog", "instruction": "What animal is in the image?", "createdAt": "..." },
  "results": [
    {
      "identifier": "https://example.com/image1.jpg",
      "url": "https://example.com/image1.jpg",
      "assetUrl": "https://assets.rapidata.ai/<uuid>.jpg",
      "aggregatedResults": { "Cat": 15, "Dog": 8 },
      "aggregatedResultsRatios": { "Cat": 0.6522, "Dog": 0.3478 },
      "summedUserScores": { "Cat": 9.5, "Dog": 4.2 },
      "summedUserScoresRatios": { "Cat": 0.6934, "Dog": 0.3066 },
      "detailedResults": [
        { "selectedCategory": "Cat", "userDetails": { "userId": "rtr_3f9c0b2e7a51d4c86e02", "country": "US", "language": "en", "userScores": { "global": 0.75 }, "demographics": {} } }
      ]
    }
  ],
  "summary": { "Cat": 15, "Dog": 8 }
}
```

| Field | Meaning |
| --- | --- |
| `aggregatedResults` | Votes per answer option |
| `aggregatedResultsRatios` | Share of votes per option |
| `summedUserScores` | Per option, the sum of the user scores of the labelers who picked it: votes weighted by reliability |
| `summedUserScoresRatios` | `summedUserScores` normalized to sum to 1 |
| `confidencePerCategory` | Only with `confidence_threshold`: confidence per option. See [Adaptive Stopping](confidence_stopping.md) |
| `detailedResults[].selectedCategory` | The option this labeler picked |
| `summary` | Votes per option, summed over all datapoints |

## Compare

```json
{
  "info": { "type": "Compare", "version": "4.1.0", "name": "Image Prompt Alignment", "instruction": "Which image matches the description better?", "createdAt": "..." },
  "results": [
    {
      "context": "A small blue book sitting on a large red book.",
      "winner": "flux-1-pro_37_0.jpg",
      "winnerIndex": 1,
      "weightedWinner": "flux-1-pro_37_0.jpg",
      "weightedWinnerIndex": 1,
      "winner_index": 1,
      "assetUrls": {
        "midjourney-5.2_37_3.jpg": "https://assets.rapidata.ai/<uuid>.jpg",
        "flux-1-pro_37_0.jpg": "https://assets.rapidata.ai/<uuid>.jpg"
      },
      "aggregatedResults": { "midjourney-5.2_37_3.jpg": 0, "flux-1-pro_37_0.jpg": 3 },
      "aggregatedResultsRatios": { "midjourney-5.2_37_3.jpg": 0.0, "flux-1-pro_37_0.jpg": 1.0 },
      "summedUserScores": { "midjourney-5.2_37_3.jpg": 0.0, "flux-1-pro_37_0.jpg": 2.552 },
      "summedUserScoresRatios": { "midjourney-5.2_37_3.jpg": 0.0, "flux-1-pro_37_0.jpg": 1.0 },
      "adaptiveStoppingState": { "verdict": "Decided", "winners": ["1"], "responseCount": 7, "...": "..." },
      "detailedResults": [
        { "votedFor": "flux-1-pro_37_0.jpg", "userDetails": { "userId": "rtr_a07d5e19c4b3f2806d71", "country": "EG", "language": "ar", "userScores": { "global": 0.845 }, "demographics": { "age": "18-29" } } }
      ]
    }
  ],
  "summary": { "A_wins_total": 0, "B_wins_total": 1 }
}
```

The two options are keyed by their identifier (URL, file name or text). Text comparisons have no `assetUrls`.

| Field | Meaning |
| --- | --- |
| `winner` / `winnerIndex` | Winner by **raw vote count** (`argmax` of `aggregatedResults`) and its position: `0` = first asset, `1` = second; `Both` / `Neither` get trailing indexes when they received votes. Both are `null` when nothing was voted or the top count is tied |
| `weightedWinner` / `weightedWinnerIndex` | Winner by **reliability-weighted** votes (`argmax` of `summedUserScores`). Same index space and `null` rule. Can differ from `winner` on close votes, so say which one you mean |
| `winner_index` | **Deprecated** alias of `winnerIndex`; will be removed |
| `assetUrls` | Each option's Rapidata-hosted file |
| `aggregatedResults` / `aggregatedResultsRatios` | Votes per option, and their share |
| `summedUserScores` / `summedUserScoresRatios` | Reliability-weighted votes per option, and their share (sums to 1) |
| `adaptiveStoppingState` | Only for pairs collected with [adaptive stopping](confidence_stopping.md) (the compare default). `verdict` is `Decided`, `Ambiguous`, `Undecided` or `Open`; `winners` names the winner (`"0"` / `"1"`) once `Decided`. Prefer it over `winner` for these pairs. See [Analyzing Adaptive Stopping Results](confidence_stopping.md#analyzing-adaptive-stopping-results) |
| `detailedResults[].votedFor` | The option this labeler picked (`Both` / `Neither` when allowed) |
| `summary` | Pairs won by each side over all pairs: `A_wins_total`, `B_wins_total`, or `<name>_wins_total` when you set `a_b_names` |

!!! note
    `winnerIndex` and `weightedWinner*` exist from aggregator version `4.1.0` (`info.version`). Older results only have `winner` and `winner_index`.

## Ranking

A ranking job returns one `results` entry **per ranking** (per inner list of `datapoints`). Each entry holds the final order in its `summary` and every matchup labelers judged in its own `results`.

```json
{
  "info": { "type": "Ranking", "version": "4.1.0", "name": "Example Ranking Job", "instruction": "Which rabbit looks cooler?", "createdAt": "..." },
  "results": [
    {
      "group": "0",
      "context": "Optional context",
      "summary": {
        "https://example.com/rabbit_3.webp": 1335,
        "https://example.com/rabbit_1.webp": 1200,
        "https://example.com/rabbit_2.webp": 1064
      },
      "results": [
        {
          "winner": "https://example.com/rabbit_3.webp",
          "winnerIndex": 1,
          "weightedWinner": "https://example.com/rabbit_3.webp",
          "weightedWinnerIndex": 1,
          "assetUrls": {
            "https://example.com/rabbit_2.webp": "https://assets.rapidata.ai/<uuid>.webp",
            "https://example.com/rabbit_3.webp": "https://assets.rapidata.ai/<uuid>.webp"
          },
          "aggregatedResults": { "https://example.com/rabbit_2.webp": 0, "https://example.com/rabbit_3.webp": 1 },
          "aggregatedResultsRatios": { "https://example.com/rabbit_2.webp": 0.0, "https://example.com/rabbit_3.webp": 1.0 },
          "summedUserScores": { "https://example.com/rabbit_2.webp": 0.0, "https://example.com/rabbit_3.webp": 0.7306 },
          "summedUserScoresRatios": { "https://example.com/rabbit_2.webp": 0.0, "https://example.com/rabbit_3.webp": 1.0 },
          "detailedResults": [
            { "votedFor": "https://example.com/rabbit_3.webp", "userDetails": { "userId": "rtr_5c2e8a90d17b4f63e1a8", "country": "DE", "language": "de", "userScores": { "global": 0.7306 }, "demographics": {} } }
          ]
        }
      ]
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `group` | Position of this ranking in your `datapoints` list, as a string (`"0"` is the first inner list) |
| `context` / `mediaContext` | The context you attached to this ranking, if any |
| `summary` | **The ranking.** Each datapoint's identifier mapped to its Elo rating, highest first. Everyone starts at 1200; the gap between two ratings says how strongly one was preferred |
| `results` | One entry per matchup, with the same fields as a [Compare](#compare) pair (no `adaptiveStoppingState`, no `winner_index`) |

There is no top-level `summary` for ranking jobs. If two datapoints in one ranking share a file name, every identifier in that ranking is prefixed with its position (`0/image.jpg`, `1/image.jpg`) to keep them apart.

## Locate

```json
{
  "info": { "type": "Locate", "version": "4.1.0", "name": "Artifact Detection", "instruction": "Tap on any visual glitches or errors in the image.", "createdAt": "..." },
  "results": [
    {
      "identifier": "https://example.com/image1.jpg",
      "url": "https://example.com/image1.jpg",
      "assetUrl": "https://assets.rapidata.ai/<uuid>.jpg",
      "notApplicable": 0,
      "notApplicableRatio": 0.0,
      "aggregatedResults": [ { "x": 68.1007, "y": 32.4029 }, { "x": 23.3924, "y": 31.883 } ],
      "detailedResults": [
        { "locations": [ { "x": 68.1007, "y": 32.4029 }, { "x": 23.3924, "y": 31.883 } ], "userDetails": { "userId": "rtr_e41b7c06a95d2f38c0b4", "country": "ES", "language": "es", "userScores": { "global": 0.6709 }, "demographics": {} } }
      ]
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `aggregatedResults` | Every point tapped by every labeler, flattened into one list. Not clustered |
| `x` / `y` | Position as a **percentage** of the image's width and height (0–100), from the top-left corner |
| `notApplicable` / `notApplicableRatio` | How many labelers, and what share, said there was nothing to tap |
| `detailedResults[].locations` | The points this labeler tapped; empty if they marked the datapoint as not applicable |

## Draw

```json
{
  "info": { "type": "Draw", "version": "4.1.0", "name": "Blue Books", "instruction": "Color in all the blue books", "createdAt": "..." },
  "results": [
    {
      "identifier": "https://example.com/image1.jpg",
      "url": "https://example.com/image1.jpg",
      "assetUrl": "https://assets.rapidata.ai/<uuid>.jpg",
      "notApplicable": 0,
      "notApplicableRatio": 0.0,
      "aggregatedResults": [
        { "size": 12, "points": [ { "x": 83.8539, "y": 79.4461 }, { "x": 64.4864, "y": 81.5653 }, { "x": 64.5551, "y": 80.0596 } ] }
      ],
      "detailedResults": [
        { "lines": [ { "size": 12, "points": [ { "x": 83.8539, "y": 79.4461 }, "..." ] } ], "userDetails": { "userId": "rtr_8d63f1a2b0c97e54d3f6", "country": "US", "language": "en", "userScores": { "global": 0.71 }, "demographics": {} } }
      ]
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `aggregatedResults` | Every line drawn by every labeler, flattened into one list |
| `size` | Brush size of the line |
| `points` | The line's points, in the same percentage coordinates as [Locate](#locate) |
| `notApplicable` / `notApplicableRatio` | How many labelers, and what share, said there was nothing to draw |
| `detailedResults[].lines` | The lines this labeler drew; empty if they marked the datapoint as not applicable |

## Select Words

```json
{
  "info": { "type": "SelectWords", "version": "4.1.0", "name": "Image-Text Alignment", "instruction": "Select the words that are not shown in the image.", "createdAt": "..." },
  "results": [
    {
      "identifier": "https://example.com/image1.jpg",
      "url": "https://example.com/image1.jpg",
      "assetUrl": "https://assets.rapidata.ai/<uuid>.jpg",
      "sentence": "Four cars on the street.",
      "aggregatedResults": [
        { "word": "Four", "wordIndex": 0, "selectedAmount": 0 },
        { "word": "cars", "wordIndex": 1, "selectedAmount": 4 },
        { "word": "on", "wordIndex": 2, "selectedAmount": 0 }
      ],
      "detailedResults": [
        { "selectedWords": [ { "word": "cars", "wordIndex": 1 } ], "userDetails": { "userId": "rtr_1b9e4d7c63a0f8e25b19", "country": "BR", "language": "pt", "userScores": { "global": 0.7115 }, "demographics": {} } }
      ]
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `sentence` | The sentence shown, rebuilt from its words |
| `aggregatedResults` | One entry per word of the sentence, in order, including words nobody selected |
| `wordIndex` | The word's position in the sentence (split by spaces), from 0. Use it rather than `word` when a word repeats |
| `selectedAmount` | How many labelers selected this word |
| `detailedResults[].selectedWords` | The words this labeler selected |

## Free Text

```json
{
  "info": { "type": "FreeText", "version": "4.1.0", "name": "Prompt generation", "instruction": "What would you like to ask an AI?", "createdAt": "..." },
  "results": [
    {
      "identifier": "https://example.com/image1.png",
      "url": "https://example.com/image1.png",
      "assetUrl": "https://assets.rapidata.ai/<uuid>.png",
      "aggregatedResults": [ "How do I bake bread?", "What is the tallest mountain?" ],
      "detailedResults": [
        { "answerText": "How do I bake bread?", "userDetails": { "userId": "rtr_c6f02a8e5d14b97a3e60", "country": "US", "language": "en", "userScores": { "global": 0.81 }, "demographics": {} } }
      ]
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `aggregatedResults` | Every answer, as written |
| `detailedResults[].answerText` | This labeler's answer |

## Understanding the User Scores

The `userScore` is a value between 0 and 1 (1 is never reached, but can appear through rounding) that indicates how reliable a labeler's responses are.

It is derived from the labeler's performance on **qualification tasks**: examples with known correct answers that labelers must pass before working on your data. It is not plain accuracy, since it also accounts for how difficult the tasks were, but it is closely related to it.

For most tasks, the `global` score is the one to use. If you need more specific dimensions, contact us at <info@rapidata.ai>.

Use it to:

- **Weight responses:** the `summedUserScores` fields already do this for you.
- **Filter:** keep only responses from labelers above a score you choose.
- **Inspect:** see who contributed to your data and how reliably.

## Working with the Results

```python
results = job.get_results()                 # RapidataResults, a dict of the JSON above
df = results.to_pandas()                    # one row per datapoint
df = results.to_pandas(split_details=True)  # one row per individual response
results.to_json("results.json")             # save to a file
```

`to_pandas()` gives Compare results `A_` / `B_` columns, Ranking results one row per ranked datapoint (`group`, `datapoint`, `score`, `rank`), and Classification results one row per datapoint and option. For Ranking, `split_details=True` gives one row per matchup response instead.

[Flows](flows.md) return their own result objects, not this format.
