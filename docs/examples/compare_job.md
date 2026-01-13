# Compare Job Example

To learn about the basics of creating a job, please refer to the [quickstart guide](../quickstart.md).

In this example, we compare images from two image generation models (Flux and Midjourney) to determine which more accurately follows the given prompts.

```python
from rapidata import RapidataClient

PROMPTS = [
    "A sign that says 'Diffusion'.",
    "A yellow flower sticking out of a green pot.",
    "hyperrealism render of a surreal alien humanoid.",
    "psychedelic duck",
    "A small blue book sitting on a large red book."
]

IMAGE_PAIRS = [
    ["https://assets.rapidata.ai/flux_sign_diffusion.jpg", "https://assets.rapidata.ai/mj_sign_diffusion.jpg"],
    ["https://assets.rapidata.ai/flux_flower.jpg", "https://assets.rapidata.ai/mj_flower.jpg"],
    ["https://assets.rapidata.ai/flux_alien.jpg", "https://assets.rapidata.ai/mj_alien.jpg"],
    ["https://assets.rapidata.ai/flux_duck.jpg", "https://assets.rapidata.ai/mj_duck.jpg"],
    ["https://assets.rapidata.ai/flux_book.jpg", "https://assets.rapidata.ai/mj_book.jpg"]
]

client = RapidataClient()

# Create audience with qualification example
audience = client.audience.create_audience(name="Prompt Alignment Audience")
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
    name="Example Image Prompt Alignment Job",
    instruction="Which image follows the prompt more accurately?",
    datapoints=IMAGE_PAIRS,
    responses_per_datapoint=25,
    contexts=PROMPTS
)

# Preview the job definition
job_definition.preview()

# Assign to audience and get results
job = audience.assign_job_to_audience(job_definition)
job.display_progress_bar()
results = job.get_results()
print(results)
```
