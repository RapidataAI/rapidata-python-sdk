# Classification Job Example

To learn about the basics of creating a job, please refer to the [quickstart guide](../quickstart.md).

In this example, we want to rate different images based on a Likert scale to assess how well generated images match their descriptions. The `NoShuffleSetting` setting ensures answer options remain in order since they represent a scale.

```python
from rapidata import RapidataClient, NoShuffleSetting

IMAGE_URLS = [
    "https://assets.rapidata.ai/tshirt-4o.png",
    "https://assets.rapidata.ai/tshirt-aurora.jpg",
    "https://assets.rapidata.ai/teamleader-aurora.jpg",
]

CONTEXTS = ["A t-shirt with the text 'Running on caffeine & dreams'"] * len(IMAGE_URLS)

client = RapidataClient()

audience = client.audience.create_audience(name="Likert Scale Audience")
audience.add_classification_example(
    instruction="How well does the image match the description?",
    answer_options=["1: Not at all", "2: A little", "3: Moderately", "4: Very well", "5: Perfectly"],
    datapoint="https://assets.rapidata.ai/tshirt-4o.png",
    truth=["5: Perfectly"],
    context="A t-shirt with the text 'Running on caffeine & dreams'"
)

job_definition = client.job.create_classification_job_definition(
    name="Likert Scale Example",
    instruction="How well does the image match the description?",
    answer_options=["1: Not at all", "2: A little", "3: Moderately", "4: Very well", "5: Perfectly"],
    contexts=CONTEXTS,
    datapoints=IMAGE_URLS,
    responses_per_datapoint=25,
    settings=[NoShuffleSetting()] # (1)!
)

job_definition.preview()

job = audience.assign_job(job_definition)
job.display_progress_bar()
results = job.get_results()
print(results)
```

1. Keeps the answer options in their specified order. Without this, options are randomized to reduce bias — but for Likert scales you want them ordered.
