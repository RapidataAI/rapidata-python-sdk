# Custom Audiences

Custom audiences let you train labelers with qualification examples specific to your task, resulting in higher quality labels.

## Audience Types

| Audience Type | Speed | Quality | Best For |
|---------------|-------|---------|----------|
| **Global** | Fastest | Baseline | Quick prototyping, simple tasks |
| **Curated** | Fast | Good | Tasks with a known domain (e.g. prompt alignment) |
| **Custom** | Slower initial setup | Highest | Production workloads, nuanced tasks |

The **global audience** is the broadest pool of labelers, ready to work on any task immediately.

A **curated audience** is a pre-existing pool of labelers trained on a specific type of task. It offers better quality than the global audience without requiring any setup.

A **custom audience** filters labelers through qualification examples before they can work on your data. Only labelers who demonstrate they understand your tasks will be included, leading to the most accurate results.

!!! note
    You can see the curated audiences along with your own in the [Rapidata Dashboard](https://app.rapidata.ai/audiences).

## Creating a Custom Audience

### Step 1: Create the Audience

```py
from rapidata import RapidataClient

client = RapidataClient()
audience = client.audience.create_audience(name="Custom Prompt Alignment Audience") # (1)!
```

1. Creates a new, empty audience. Labelers join by passing the qualification examples you add next.

### Step 2: Add Qualification Examples

Qualification examples are questions with known correct answers. Labelers must answer these correctly to join your audience.

!!! warning "Review your qualification examples carefully"
    Every qualification example with its associated truth must be manually and thoroughly reviewed before use. If an example has a wrong or ambiguous truth value, the qualification process will filter out good labelers who answer correctly while letting through bad labelers who happen to match the incorrect answer — completely inverting your quality control. Always verify that each example has a clear, unambiguous correct answer.

```py
DATAPOINTS = [
    ["https://assets.rapidata.ai/flux_sign_diffusion.jpg", "https://assets.rapidata.ai/mj_sign_diffusion.jpg"],
    ["https://assets.rapidata.ai/flux_duck.jpg", "https://assets.rapidata.ai/mj_duck.jpg"],
    ["https://assets.rapidata.ai/flux_book.jpg", "https://assets.rapidata.ai/mj_book.jpg"],
    ["https://assets.rapidata.ai/flux_flower.jpg", "https://assets.rapidata.ai/mj_flower.jpg"],
    ["https://assets.rapidata.ai/flux_store_front.jpg", "https://assets.rapidata.ai/mj_store_front.jpg"],
    ["https://assets.rapidata.ai/flux_hand.jpg", "https://assets.rapidata.ai/mj_hand.jpg"],
    ["https://assets.rapidata.ai/flux_traffic_lights.jpg", "https://assets.rapidata.ai/mj_traffic_lights.jpg"],
    ["https://assets.rapidata.ai/flux_plane.jpg", "https://assets.rapidata.ai/mj_plane.jpg"],
]
PROMPTS = [
    "A sign that says 'Diffusion'.",
    "A psychedelic duck with glasses",
    "A small blue book sitting on a large red book.",
    "A yellow flower sticking out of a bright green pot.",
    "A store front with 'hello world' written on it.",
    "A yellow hand on a black stone.",
    "A green, yellow and red traffic light.",
    "A plane flying over a person.",
]

for prompt, datapoint in zip(PROMPTS, DATAPOINTS):
    audience.add_compare_example(
        instruction="Which image follows the prompt more accurately?",
        datapoint=datapoint, # (1)!
        truth=datapoint[0], # (2)!
        context=prompt # (3)!
    )
```

1. The items to compare — a list of URLs, local paths, or text strings.
2. The correct answer — must match one of the datapoint items exactly.
3. Additional context shown alongside the comparison (optional).

!!! note
    In practice you'd want to add more examples to the audience to improve the quality of the results.

### Step 3: Create and Assign a Job

Once your audience is set up, create a job definition and assign it to the audience:

```py
job_definition = client.job.create_compare_job_definition(
    name="Prompt Alignment Job",
    instruction="Which image follows the prompt more accurately?",
    datapoints=[
        ["https://assets.rapidata.ai/flux_book.jpg",
         "https://assets.rapidata.ai/mj_book.jpg"]
    ],
    contexts=["A small blue book sitting on a large red book."]
)

job_definition.preview()

job = audience.assign_job(job_definition)
job.display_progress_bar()
results = job.get_results()
print(results)
```

## Complete Example

Here's the full workflow — creating a custom audience, adding qualification examples, and running a labeling job:

```py
from rapidata import RapidataClient

client = RapidataClient()

audience = client.audience.create_audience(name="Custom Prompt Alignment Audience")

DATAPOINTS = [
    ["https://assets.rapidata.ai/flux_sign_diffusion.jpg", "https://assets.rapidata.ai/mj_sign_diffusion.jpg"],
    ["https://assets.rapidata.ai/flux_duck.jpg", "https://assets.rapidata.ai/mj_duck.jpg"],
    ["https://assets.rapidata.ai/flux_book.jpg", "https://assets.rapidata.ai/mj_book.jpg"],
    ["https://assets.rapidata.ai/flux_flower.jpg", "https://assets.rapidata.ai/mj_flower.jpg"],
    ["https://assets.rapidata.ai/flux_store_front.jpg", "https://assets.rapidata.ai/mj_store_front.jpg"],
    ["https://assets.rapidata.ai/flux_hand.jpg", "https://assets.rapidata.ai/mj_hand.jpg"],
    ["https://assets.rapidata.ai/flux_traffic_lights.jpg", "https://assets.rapidata.ai/mj_traffic_lights.jpg"],
    ["https://assets.rapidata.ai/flux_plane.jpg", "https://assets.rapidata.ai/mj_plane.jpg"],
]
PROMPTS = [
    "A sign that says 'Diffusion'.",
    "A psychedelic duck with glasses",
    "A small blue book sitting on a large red book.",
    "A yellow flower sticking out of a bright green pot.",
    "A store front with 'hello world' written on it.",
    "A yellow hand on a black stone.",
    "A green, yellow and red traffic light.",
    "A plane flying over a person.",
]

for prompt, datapoint in zip(PROMPTS, DATAPOINTS):
    audience.add_compare_example(
        instruction="Which image follows the prompt more accurately?",
        datapoint=datapoint,
        truth=datapoint[0],
        context=prompt
    )

job_definition = client.job.create_compare_job_definition(
    name="Prompt Alignment Job",
    instruction="Which image follows the prompt more accurately?",
    datapoints=[
        ["https://assets.rapidata.ai/flux_book.jpg",
         "https://assets.rapidata.ai/mj_book.jpg"]
    ],
    contexts=["A small blue book sitting on a large red book."]
)

job_definition.preview()

job = audience.assign_job(job_definition)
job.display_progress_bar()
results = job.get_results()
print(results)
```

## Matching the Job UI with Settings

Qualification examples default to the standard UI for their task type. If
your job uses `settings` to change how the task is rendered (e.g.
`NoShuffleSetting` to keep answer options in order, `AllowNeitherBothSetting`
to add an "Unsure" button), pass the same settings to the example so the
labeler qualifies on the exact UI they will later see.

```py
from rapidata import NoShuffleSetting

audience.add_classification_example(
    instruction="How well does the image match the description?",
    answer_options=[
        "1: Not at all",
        "2: A little",
        "3: Moderately",
        "4: Very well",
        "5: Perfectly",
    ],
    datapoint="https://assets.rapidata.ai/email-4o.png",
    truth=["5: Perfectly", "4: Very well"],
    context="A laptop screen with clearly readable text, addressed to the marketing team.",
    settings=[NoShuffleSetting()], # (1)!
)
```

1. Applies the setting as a feature flag on this single example. Use the same
   `RapidataSetting` subclasses you would pass to `settings=` on a job or
   order (e.g. `NoShuffleSetting`, `MarkdownSetting`,
   `AllowNeitherBothSetting`, `ComparePanoramaSetting`). Both
   `add_classification_example` and `add_compare_example` accept `settings`.

## Reusing Audiences

Once created, you can reuse your audience for multiple jobs:

```py
audiences = client.audience.find_audiences("Custom Prompt Alignment Audience")
audience = client.audience.get_audience_by_id("audience_id")

job = audience.assign_job(new_job_definition)
```

## Next Steps

- Learn about [Classification Jobs](examples/classify_job.md) for categorizing data
- Understand the [Results Format](understanding_the_results.md)
- Configure [Early Stopping](confidence_stopping.md) based on confidence thresholds
