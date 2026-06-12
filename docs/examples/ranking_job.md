# Ranking Job Example

To learn about the basics of creating a job, please refer to the [quickstart guide](../quickstart.md).

In a ranking job, a set of datapoints is ordered through pairwise matchups: labelers are repeatedly shown two datapoints from the set and pick one based on the instruction. The ranking is based on an Elo rating system that updates after each matchup. In this example, we rank images of rabbits by how cool they look.

Phrase the instruction for the individual matchup rather than the overall ranking — "Which rabbit looks cooler?" instead of "Which rabbit looks the coolest?" — since labelers only ever see two images at a time.

```python
from rapidata import RapidataClient

DATAPOINTS = [
    "https://assets.rapidata.ai/f9d92460-a362-493c-af91-bf50046453ae.webp",
    "https://assets.rapidata.ai/9bcd8b18-e9ad-4449-84d4-b3d72e200e9c.webp",
    "https://assets.rapidata.ai/266f6446-3ca8-4c2d-b070-13558b35a4e0.webp",
    "https://assets.rapidata.ai/f787f02c-e5d0-43ca-aa6e-aea747845cf3.webp",
    "https://assets.rapidata.ai/7e518a1b-4d1c-4a86-9109-26646684cc02.webp",
    "https://assets.rapidata.ai/10af47bd-3502-4534-b917-73dba5feaf76.webp",
    "https://assets.rapidata.ai/59725ca0-1fd5-4850-a15c-4221e191e293.webp",
    "https://assets.rapidata.ai/65d3939d-c1b8-433c-b180-13dae80f0519.webp",
    "https://assets.rapidata.ai/c13b8feb-fb97-4646-8dfc-97f05d37a637.webp",
    "https://assets.rapidata.ai/586dc517-c987-4d06-8a6f-553508b86356.webp",
    "https://assets.rapidata.ai/f4884ecd-cacb-4387-ab18-3b6e7dcdf10c.webp",
    "https://assets.rapidata.ai/79076f76-a432-4ef9-9007-6d09a218417a.webp",
]

client = RapidataClient()

audience = client.audience.get_audience_by_id("global") # (1)!

job_definition = client.job.create_ranking_job_definition(
    name="Example Ranking Job",
    instruction="Which rabbit looks cooler?",
    datapoints=[DATAPOINTS], # (2)!
    comparison_budget_per_ranking=50, # (3)!
    random_comparisons_ratio=0.5, # (4)!
)

job_definition.preview()

job = audience.assign_job(job_definition)
job.display_progress_bar()
results = job.get_results()
print(results)
```

1. The global audience (id `global`) already has labelers ready to work, so the job starts collecting responses immediately. You can assign a ranking job to any audience — browse them in the [Rapidata Dashboard](https://app.rapidata.ai/audiences).
2. The outer list defines independent rankings; each inner list is the set of datapoints ranked against each other. Here a single ranking over all rabbits.
3. The number of matchups collected per ranking. More comparisons make the resulting order more reliable.
4. The first half of the comparisons are random; the second half are close matchups between similarly-rated datapoints.

!!! note
    For benchmarking AI models on an ongoing leaderboard, see [Model Ranking](../mri.md); for lightweight continuous ranking without full job setup, see [Ranking Flows](../flows.md).
