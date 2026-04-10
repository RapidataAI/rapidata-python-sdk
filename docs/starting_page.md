# Rapidata Python SDK

Get humans to label your data in minutes.

```
pip install -U rapidata
```

The SDK has three building blocks: **audiences** (who labels), **job definitions** (what to label), and **jobs** (running it). Below are the common patterns.

---

## Compare two outputs

```python
from rapidata import RapidataClient

client = RapidataClient()
audience = client.audience.find_audiences("alignment")[0]

job_definition = client.job.create_compare_job_definition(
    name="Image Comparison",
    instruction="Which image matches the description better?",
    contexts=["A small blue book sitting on a large red book."],
    datapoints=[["https://assets.rapidata.ai/midjourney-5.2_37_3.jpg",
                "https://assets.rapidata.ai/flux-1-pro_37_0.jpg"]],
)

job = audience.assign_job(job_definition)
job.display_progress_bar()
results = job.get_results()
```

Works with images, video, audio, and text. Pass `data_type="text"` for plain text comparisons. See the full [comparison example](examples/compare_job.md).

---

## Classify data

```python
from rapidata import RapidataClient, NoShuffleSetting

client = RapidataClient()
audience = client.audience.find_audiences("alignment")[0]

job_definition = client.job.create_classification_job_definition(
    name="Image Rating",
    instruction="How well does the image match the description?",
    answer_options=["1: Not at all", "2: A little", "3: Moderately", "4: Very well", "5: Perfectly"],
    datapoints=["https://assets.rapidata.ai/tshirt-4o.png"],
    contexts=["A t-shirt with the text 'Running on caffeine & dreams'"],
    settings=[NoShuffleSetting()],
)

job = audience.assign_job(job_definition)
job.display_progress_bar()
results = job.get_results()
```

Use `NoShuffleSetting` for ordered scales (Likert). See the full [classification example](examples/classify_job.md).

---

## Benchmark models

```python
from rapidata import RapidataClient

client = RapidataClient()

benchmark = client.mri.create_new_benchmark(
    name="Image Quality",
    prompts=["A serene mountain landscape at sunset",
             "A futuristic city with flying cars"],
)

leaderboard = benchmark.create_leaderboard(
    name="Realism",
    instruction="Which image is more realistic?",
)

benchmark.evaluate_model(
    name="ModelA",
    media=["https://assets.rapidata.ai/mountain_sunset1.png",
           "https://assets.rapidata.ai/futuristic_city.png"],
    prompts=["A serene mountain landscape at sunset",
             "A futuristic city with flying cars"],
)

standings = leaderboard.get_standings()
```

Creates leaderboards comparing AI models with human evaluation. See the full [MRI guide](mri.md).

---

## Continuous ranking

```python
from rapidata import RapidataClient

client = RapidataClient()

flow = client.flow.create_ranking_flow(
    name="Image Quality Ranking",
    instruction="Which image looks better?",
)

flow_item = flow.create_new_flow_batch(
    datapoints=["https://example.com/a.jpg",
                "https://example.com/b.jpg",
                "https://example.com/c.jpg"],
    time_to_live=300,
)

results = flow_item.get_results()
matrix = flow_item.get_win_loss_matrix()
```

Ranking flows let you keep adding items over time without creating full jobs. See the [Ranking Flows guide](flows.md).

---

## Custom audiences for better quality

The examples above use curated audiences. For production, create your own with qualification examples:

```python
audience = client.audience.create_audience(name="My Audience")
audience.add_compare_example(
    instruction="Which image follows the prompt more accurately?",
    datapoint=["https://assets.rapidata.ai/flux_sign_diffusion.jpg",
               "https://assets.rapidata.ai/mj_sign_diffusion.jpg"],
    truth="https://assets.rapidata.ai/flux_sign_diffusion.jpg",
    context="A sign that says 'Diffusion'.",
)

# Now use this audience for any job
job = audience.assign_job(job_definition)
```

Only labelers who pass your examples get included. See the full [Custom Audiences guide](audiences.md).
