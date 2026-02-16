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

> **Note**: You can see the curated audiences along with your own in the [Rapidata Dashboard](https://app.rapidata.ai/audiences).

## Creating a Custom Audience

### Step 1: Create the Audience

```py
from rapidata import RapidataClient

client = RapidataClient()
audience = client.audience.create_audience(name="Image Comparison Audience")
```

### Step 2: Add Qualification Examples

Qualification examples are questions with known correct answers. Labelers must answer these correctly to join your audience:

```py
for _ in range(3):
    audience.add_compare_example(
        instruction="Which image follows the prompt more accurately?",
        datapoint=[
            "https://assets.rapidata.ai/flux_sign_diffusion.jpg",
            "https://assets.rapidata.ai/mj_sign_diffusion.jpg"
        ],
        truth="https://assets.rapidata.ai/flux_sign_diffusion.jpg",
        context="A sign that says 'Diffusion'."
    )
```
> **Note**: You need at least 3 examples to create an audience. In this example, we're adding the same qualification example 5 times for demonstration purposes only. Adding duplicates doesn't improve quality beyond adding it once. For best results, provide diverse, unique examples that cover different aspects of your task.

**Parameters:**

- `instruction`: The question shown to labelers
- `datapoint`: The items to compare (list of URLs, local paths or text)
- `truth`: The correct answer (must match one of the datapoint items exactly)
- `context`: Additional context shown alongside the comparison (optional)

## Complete Example

Here's the full workflow for creating a custom audience and running a labeling job:

```py
from rapidata import RapidataClient

client = RapidataClient()

# Create and configure audience with qualification examples
audience = client.audience.create_audience(name="Prompt Alignment Audience")

for _ in range(3):
    audience.add_compare_example(
        instruction="Which image follows the prompt more accurately?",
        datapoint=[
            "https://assets.rapidata.ai/flux_sign_diffusion.jpg",
            "https://assets.rapidata.ai/mj_sign_diffusion.jpg"
        ],
        truth="https://assets.rapidata.ai/flux_sign_diffusion.jpg",
        context="A sign that says 'Diffusion'."
    )

# Create job definition
job_definition = client.job.create_compare_job_definition(
    name="Prompt Alignment Job",
    instruction="Which image follows the prompt more accurately?",
    datapoints=[
        ["https://assets.rapidata.ai/flux_flower.jpg",
         "https://assets.rapidata.ai/mj_flower.jpg"]
    ],
    contexts=["A yellow flower sticking out of a green pot."]
)

# Preview before running
job_definition.preview()

# Assign to audience and get results
job = audience.assign_job(job_definition)
job.display_progress_bar()
results = job.get_results()
print(results)
```

## Reusing Audiences

Once created, you can reuse your audience for multiple jobs:

```py
# Find existing audiences by name
audiences = client.audience.find_audiences("Prompt Alignment")

# Or get by ID
audience = client.audience.get_audience_by_id("audience_id")

# Assign new jobs to the same audience
job = audience.assign_job(new_job_definition)
```

## Next Steps

- Learn about [Classification Jobs](examples/classify_job.md) for categorizing data
- Understand the [Results Format](understanding_the_results.md)
- Configure [Early Stopping](confidence_stopping.md) based on confidence thresholds
