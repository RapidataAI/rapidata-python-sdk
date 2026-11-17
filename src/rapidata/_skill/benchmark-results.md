# Benchmark results and voter demographics

> Part of the Rapidata agent skill: `python -m rapidata skill benchmark-results`. The **Task design rules** and **Key Gotchas** in the main guide (`python -m rapidata skill`) apply to everything here.

## Reading results

```python
# Get results
standings = leaderboard.get_standings()                    # Pandas DataFrame for one leaderboard
overall = benchmark.get_overall_standings(tags=None, leaderboard_ids=None)  # Aggregated ELO across all leaderboards
matrix_lb = leaderboard.get_win_loss_matrix()              # Pairwise wins/losses for one leaderboard
matrix_bm = benchmark.get_win_loss_matrix(                 # Pairwise wins/losses across leaderboards
    tags=None, participant_ids=None, leaderboard_ids=None, use_weighted_scoring=None,
)
# These four leave deprecated models and their votes out by default;
# include_deprecated=True brings them back and refits every score.
overall_all = benchmark.get_overall_standings(include_deprecated=True)

# All of the read methods above (plus the two below) accept voter-demographic filters
# and run_id — see **Voter demographic filtering** below.
demographics = benchmark.get_demographics()                # Demographic composition of the voters
breakdown = benchmark.get_standings_breakdown(             # Standings split by a voter dimension
    dimension=BenchmarkDemographicDimension.COUNTRY,
)

# Access the jobs that ran for a leaderboard (one RapidataJob per run, most recent first)
for job in leaderboard.jobs:
    job_results = job.get_results()
```

## Vote aggregation (`VoteAggregation`)

`VoteAggregation` controls how the individual annotator responses on a single matchup (one comparison of two models on one prompt) are aggregated into that matchup's result. Importable from the top-level `rapidata` package (and from `rapidata.types`).

```python
from rapidata import VoteAggregation
```

| Member | Meaning |
|--------|---------|
| `VoteAggregation.MAJORITY_VOTE` | Collapses each matchup to a single win for the side the majority of responses picked, splitting ties 0.5/0.5. Every matchup weighs the same regardless of how many responses it collected. **Default.** |
| `VoteAggregation.ALL_VOTES` | Counts every individual response as its own matchup, so heavily-answered matchups dominate the standings |

- Set at creation via `benchmark.create_leaderboard(..., vote_aggregation=...)` (defaults to `VoteAggregation.MAJORITY_VOTE`).
- Read back via the read-only `leaderboard.vote_aggregation` property (returns a `VoteAggregation`). For a leaderboard read from the benchmark's listing the value is lazily fetched on first access and cached.
- Change afterwards via `leaderboard.update(vote_aggregation=...)`.

```python
from rapidata import VoteAggregation

leaderboard = benchmark.create_leaderboard(
    name="Realism",
    instruction="Which image is more realistic?",
    min_responses_per_matchup=5,
    vote_aggregation=VoteAggregation.ALL_VOTES,
)
print(leaderboard.vote_aggregation)   # VoteAggregation.ALL_VOTES
```

## Win/loss matrix

`leaderboard.get_win_loss_matrix(tags=None, use_weighted_scoring=None)` and `benchmark.get_win_loss_matrix(tags=None, participant_ids=None, leaderboard_ids=None, use_weighted_scoring=None)` return a square pandas DataFrame indexed by participant name on both axes. Cell `[i, j]` is how often row model `i` beat column model `j`; the diagonal is always 0.

- `tags=None` includes every matchup; `tags=[]` includes none.
- `use_weighted_scoring=True` weights each matchup by annotator reliability (`userScore`), so cells hold weighted float sums; `False` gives raw win counts; `None` uses the server-configured default.
- Both also accept the voter-demographic filters and `run_id` described below.

## Voter demographic filtering

Every benchmark and leaderboard read method that returns standings or a matrix accepts the same six optional voter-demographic filters plus `run_id`, restricting the result to votes cast by matching voters:

- **Benchmark:** `get_overall_standings`, `get_win_loss_matrix`, `get_demographics`, `get_standings_breakdown`.
- **Leaderboard:** `get_standings`, `get_win_loss_matrix`.

| Parameter | Type | Notes |
|-----------|------|-------|
| `country` | `list[str] \| None` | ISO-2 country codes; **observed** |
| `language` | `list[str] \| None` | Language codes; **observed** |
| `gender` | `list[Gender] \| None` | SDK `Gender` enum; **estimated** (inferred) |
| `age_bucket` | `list[AgeGroup] \| None` | SDK `AgeGroup` enum; **estimated** (inferred) |
| `occupation` | `list[str] \| None` | Occupation strings; **estimated** (inferred) |
| `run_id` | `str \| None` | Restrict to a single evaluation run |

```python
from rapidata import Gender, AgeGroup, BenchmarkDemographicDimension

# Standings from US/GB voters aged 18–29
overall = benchmark.get_overall_standings(
    country=["US", "GB"],
    age_bucket=[AgeGroup.BETWEEN_18_29],
)
```

`gender`/`age_bucket` enum values are converted to backend values internally.

## `benchmark.get_demographics(...)`

Returns the demographic composition of the benchmark's voters. Accepts `tags`, `leaderboard_ids`, and the six demographic filters plus `run_id` above. The DataFrame has one row per `(dimension, bucket)`:

| Column | Meaning |
|--------|---------|
| `dimension` | Which attribute the row describes (a `BenchmarkDemographicDimension` value) |
| `value` | The bucket within that dimension |
| `votes` | Raw vote count in the bucket |
| `share` | Fraction of the dimension's votes; shares within a dimension sum to 1 |

Every dimension includes an `"unknown"` bucket for votes whose attribute could not be determined.

## `benchmark.get_standings_breakdown(dimension, ...)`

Returns standings split by a demographic dimension of the voters. `dimension` (required, first positional arg) is a `BenchmarkDemographicDimension`; the method also accepts `tags`, `leaderboard_ids`, and the six demographic filters plus `run_id`. The DataFrame has one row per `(segment, model)`:

| Column | Meaning |
|--------|---------|
| `segment` | The voter segment within the chosen dimension (includes an `"unknown"` bucket) |
| `segment_votes` | Raw vote count for the segment |
| `name` | Model / participant name |
| `wins` | Wins for that model within the segment |
| `total_matches` | Matches the model took part in within the segment |
| `score` | Score rounded to 2 decimals, or `None` |

## `BenchmarkDemographicDimension`

Importable from the top-level `rapidata` package. Selects which voter attribute `get_standings_breakdown` splits on and identifies the `dimension` column of `get_demographics`. Members: `AGEBUCKET`, `GENDER`, `OCCUPATION`, `COUNTRY`, `LANGUAGE` (rendered as `AgeBucket`, `Gender`, `Occupation`, `Country`, `Language`).

```python
from rapidata import BenchmarkDemographicDimension
```

## Example

### Model Benchmark — Voter Demographics

Standings, win/loss matrices, and both demographic read methods accept the same
optional voter-demographic filters. `country` (ISO-2 codes), `language`, and
`occupation` take plain strings; `gender` takes the `Gender` enum and `age_bucket`
the `AgeGroup` enum. `run_id` restricts to a single evaluation run. `gender` /
`age_bucket` / `occupation` are estimated (inferred); `country` / `language` are
observed.

```python
from rapidata import RapidataClient, Gender, AgeGroup, BenchmarkDemographicDimension

client = RapidataClient()
benchmark = client.mri.get_benchmark_by_id("benchmark_id")

# Restrict any read to a demographic slice of the voters.
standings = benchmark.get_overall_standings(
    country=["US", "CA"],
    language=["en"],
    gender=[Gender.FEMALE],
    age_bucket=[AgeGroup.BETWEEN_18_29],
)
matrix = benchmark.get_win_loss_matrix(country=["US"])

# The same filters work on a single leaderboard's reads.
# lb.get_standings(country=["US"], occupation=["student"])
# lb.get_win_loss_matrix(gender=[Gender.MALE])

# Who voted: one row per (dimension, value) with vote counts and shares that sum
# to 1 within each dimension. Every dimension has an "unknown" bucket for votes
# whose attribute could not be determined.
demographics = benchmark.get_demographics()
print(demographics)  # columns: dimension, value, votes, share

# Standings split by one demographic dimension of the voters.
breakdown = benchmark.get_standings_breakdown(
    dimension=BenchmarkDemographicDimension.COUNTRY,
)
print(breakdown)  # columns: segment, segment_votes, name, wins, total_matches, score
```
