# Rapidata Python SDK

Get humans to label your data in minutes. Create labeling jobs, compare model outputs, and collect human feedback at scale.

```
pip install -U rapidata
```

The SDK has three building blocks: **audiences** (who labels), **job definitions** (what to label), and **jobs** (running it). Below are the common patterns.

---

## Quick example

=== "Image"
    ```python
    from rapidata import RapidataClient

    client = RapidataClient()

    audience = client.audience.find_audiences("alignment")[0]

    job_definition = client.job.create_compare_job_definition(
        name="Example Image Comparison",
        instruction="Which image matches the description better?",
        contexts=["A small blue book sitting on a large red book."],
        datapoints=[["https://assets.rapidata.ai/midjourney-5.2_37_3.jpg",
                    "https://assets.rapidata.ai/flux-1-pro_37_0.jpg"]],
    )

    job = audience.assign_job(job_definition)
    job.view()
    job.display_progress_bar()
    results = job.get_results()
    print(results)
    ```

=== "Video"
    ```python
    from rapidata import RapidataClient

    client = RapidataClient()

    audience = client.audience.find_audiences("alignment")[0]

    job_definition = client.job.create_compare_job_definition(
        name="Example Video Comparison",
        instruction="Which video fits the description better?",
        contexts=["A group of elephants painting vibrant murals on a city wall."],
        datapoints=[["https://assets.rapidata.ai/0074_sora_1.mp4",
                    "https://assets.rapidata.ai/0074_hunyuan_1724.mp4"]],
    )

    job = audience.assign_job(job_definition)
    job.view()
    job.display_progress_bar()
    results = job.get_results()
    print(results)
    ```

=== "Audio"
    ```python
    from rapidata import RapidataClient, LanguageFilter

    client = RapidataClient()

    audience = client.audience.get_audience_by_id("global")

    job_definition = client.job.create_compare_job_definition(
        name="Example Audio Comparison",
        instruction="Which audio clip sounds more natural?",
        datapoints=[["https://assets.rapidata.ai/Chat_gpt.mp3",
                    "https://assets.rapidata.ai/ElevenLabs.mp3"]],
    )

    job = audience.assign_job(job_definition)
    job.view()
    job.display_progress_bar()
    results = job.get_results()
    print(results)
    ```

=== "Text"
    ```python
    from rapidata import RapidataClient, LanguageFilter

    client = RapidataClient()

    audience = client.audience.get_audience_by_id("global")

    job_definition = client.job.create_compare_job_definition(
        name="Example Text Comparison",
        instruction="Which sentence is grammatically more correct?",
        datapoints=[["The children were amazed by the magician's tricks",
                    "The children were amusing by the magician's tricks."]],
        data_type="text",
    )

    job = audience.assign_job(job_definition)
    job.view()
    job.display_progress_bar()
    results = job.get_results()
    print(results)
    ```

!!! note
    The curated/global audiences get you started quickly. For higher quality results, use a [custom audience](audiences.md) with qualification examples.

<div data-preview-embed
     data-preview-map='{"Image":"cmp_1HSFCph25U1J22","Video":"cmp_1HSMbDk5EaUExL","Audio":"cmp_1HSMsM9Ph3Sn5o","Text":"cmp_1HSN6NhgMo4C9R"}'>
  <div class="phone-preview">
    <div class="phone-preview__notch"></div>
    <div class="phone-preview__btn phone-preview__btn--left-top"></div>
    <div class="phone-preview__btn phone-preview__btn--left-bot"></div>
    <div class="phone-preview__btn phone-preview__btn--right"></div>
    <iframe class="phone-preview__iframe"
            src="https://rapids.rapidata.ai/preview/campaign?id=cmp_1HSFCph25U1J22&language=en&userSegment=0&refreshCount=0"
            allow="clipboard-write"
            title="Live Rapidata campaign preview"></iframe>
  </div>
  <div class="preview-controls">
    <button type="button" data-preview-refresh aria-label="Refresh preview">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
      <span>Refresh</span>
    </button>
  </div>
</div>

---

## Core workflow

The SDK is built around three concepts:

**Audience** --- A group of labelers filtered through qualification examples. Use curated audiences for quick starts or create custom ones for higher quality.
[:octicons-arrow-right-24: Custom Audiences](audiences.md)

**Job Definition** --- Configures what you want labeled: the data, instruction, response format, and quality settings.
[:octicons-arrow-right-24: Parameter Reference](job_definition_parameters.md)

**Job** --- A running labeling task. Assign a job definition to an audience, monitor progress, and retrieve results.
[:octicons-arrow-right-24: Quick Start](quickstart.md)

---

## What you can do

| Use case | Description | Guide |
|---|---|---|
| **Compare** | Side-by-side comparison of images, video, audio, or text | [Comparison example](examples/compare_job.md) |
| **Classify** | Categorize data with custom labels or Likert scales | [Classification example](examples/classify_job.md) |
| **Rank models** | Benchmark AI models on leaderboards with human evaluation | [Model Ranking](mri.md) |
| **Continuous ranking** | Lightweight ongoing ranking without full job setup | [Ranking Flows](flows.md) |
