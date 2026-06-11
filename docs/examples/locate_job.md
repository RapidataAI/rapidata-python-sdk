# Locate Job Example

To learn about the basics of creating a job, please refer to the [quickstart guide](../quickstart.md).

In a locate job, labelers tap the points in a datapoint that match your instruction. In this example, we ask people to point out visual artifacts in AI-generated images — a common way to find where a generator went wrong.

Locate jobs run on the **global** audience — the broadest pool of labelers, ready to work immediately. Unlike classification and comparison, locate tasks don't support custom qualification examples yet, so there's no custom-audience variant for this job type.

```python
from rapidata import RapidataClient

IMAGE_URLS = [
    "https://assets.rapidata.ai/eac11c3e-ad57-402b-90ed-23378d2ff869.jpg",
    "https://assets.rapidata.ai/04e7e3c6-5554-47ca-bdb2-950e48ac3e6c.jpg",
    "https://assets.rapidata.ai/91d9913c-b399-47f8-ad19-767798cc951c.jpg",
]

client = RapidataClient()

audience = next( # (1)!
    a for a in client.audience.find_audiences("Global Audience") if a.name == "Global Audience"
)

job_definition = client.job.create_locate_job_definition(
    name="Artifact Detection Example",
    instruction="Tap on any visual glitches or errors in the image.", # (2)!
    datapoints=IMAGE_URLS,
    responses_per_datapoint=35,
)

job_definition.preview()

job = audience.assign_job(job_definition)
job.display_progress_bar()
results = job.get_results()
print(results)
```

1. The global audience already has labelers ready to work. A freshly created audience has no qualified labelers yet, so a job assigned to it would never collect responses.
2. The instruction tells labelers what to locate. Each response is the set of points they tapped on that datapoint.
