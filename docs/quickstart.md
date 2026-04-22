# Quickstart Guide

Get real humans to label your data. This guide shows you how to create a labeling job using the Rapidata API.

The workflow consists of three main concepts:

1. **Audience**: A group of labelers who will work on your tasks
2. **Job Definition**: The configuration for your labeling task (instruction, datapoints, settings)
3. **Job**: A running labeling task assigned to an audience

<div data-preview-embed data-preview-campaign="cmp_1HSFCph25U1J22">
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

## Installation

Install Rapidata using pip:

```
pip install -U rapidata
```

## Usage

All operations are managed through the [`RapidataClient`](reference/rapidata/rapidata_client/rapidata_client.md#rapidata.rapidata_client.rapidata_client.RapidataClient).

Create a client as follows:

```py
from rapidata import RapidataClient

client = RapidataClient() # (1)!
```

1. The first time you run this on a machine, it will open a browser window to log in. Your credentials are saved to `~/.config/rapidata/credentials.json` so you don't have to log in again.

Alternatively, authenticate with a client ID and secret from [Rapidata Settings](https://app.rapidata.ai/settings/tokens):

```py
from rapidata import RapidataClient
client = RapidataClient(client_id="Your client ID", client_secret="Your client secret")
```

### Step 1: Get an Audience

The simplest way to get started is with a curated audience:

```py
audience = client.audience.find_audiences("alignment")[0] # (1)!
```

1. Curated audiences are pre-existing pools of labelers trained on a specific type of task.

!!! note
    The curated audience gets you started quickly, but results may be less accurate than a custom audience trained with examples specific to your task. For higher quality, see [Custom Audiences](audiences.md).

### Step 2: Create a Job Definition

A job definition configures what you want labeled:

```py
job_definition = client.job.create_compare_job_definition(
    name="Example Image Prompt Alignment",
    instruction="Which image matches the description better?", # (1)!
    datapoints=[ # (2)!
        ["https://assets.rapidata.ai/midjourney-5.2_37_3.jpg",
         "https://assets.rapidata.ai/flux-1-pro_37_0.jpg"]
    ],
    contexts=["A small blue book sitting on a large red book."] # (3)!
)
```

1. The instruction shown to labelers. Should be clear and unambiguous.
2. For compare jobs, each datapoint is a pair of items. Supports URLs, local paths, or text.
3. Optional text context shown alongside each datapoint (must match the length of `datapoints`).

!!! tip
    If some datapoints fail to upload, a `FailedUploadException` will be raised. Learn how to handle this in the [Error Handling Guide](error_handling.md).

For a detailed explanation of all available parameters (including name, instruction, datapoints, contexts, quality control options, and more), see the [Job Definition Parameters Reference](job_definition_parameters.md).

### Step 3: Preview the Job Definition

Before running your job, preview it to see exactly what labelers will see:

```py
job_definition.preview() # (1)!
```

1. Opens your browser where you can review and adjust the job configuration.

### Step 4: Run and Get Results

```py
job = audience.assign_job(job_definition) # (1)!
job.display_progress_bar()
results = job.get_results() # (2)!
```

1. Assigns the job definition to the audience and starts collecting responses.
2. Blocks until the job is complete and returns the results. You can also monitor progress on the [Rapidata Dashboard](https://app.rapidata.ai/dashboard).

To understand the results format, see the [Understanding the Results](understanding_the_results.md) guide.

## Retrieve Existing Resources

### Find Audiences

```py
# Find audiences by name
audiences = client.audience.find_audiences("alignment")

# Get a specific audience by ID
audience = client.audience.get_audience_by_id("audience_id")
```

### Find Job Definitions

```py
# Find job definitions by name
job_definitions = client.job.find_job_definitions("Example Image Prompt Alignment")

# Get a specific job definition by ID
job_definition = client.job.get_job_defintion_by_id("job_definition_id")
```

### Find Jobs

```py
# Find jobs by name
jobs = client.job.find_jobs("Example Image Prompt Alignment")

# Get a specific job by ID
job = client.job.get_job_by_id("job_id")

# Find jobs for a specific audience
audience = client.audience.get_audience_by_id("audience_id")
jobs = audience.find_jobs("Prompt Alignment")
```

!!! note
    The `find_*` can be executed without the `name` parameter to return the most recent resources.

## Complete Example

Here's the full workflow using the curated alignment audience:

```py
from rapidata import RapidataClient

client = RapidataClient()

audience = client.audience.find_audiences("alignment")[0]

job_definition = client.job.create_compare_job_definition(
    name="Example Image Prompt Alignment",
    instruction="Which image matches the description better?",
    datapoints=[
        ["https://assets.rapidata.ai/midjourney-5.2_37_3.jpg",
         "https://assets.rapidata.ai/flux-1-pro_37_0.jpg"]
    ],
    contexts=["A small blue book sitting on a large red book."]
)

job_definition.preview() # (1)!

job = audience.assign_job(job_definition)
job.display_progress_bar()
results = job.get_results()
print(results)
```

1. Optional — opens a browser preview of what labelers will see.

## Next Steps

- Create [Custom Audiences](audiences.md) for higher quality results
- Learn about [Classification Jobs](examples/classify_job.md) for categorizing data
- Understand the [Results Format](understanding_the_results.md)
- Configure [Early Stopping](confidence_stopping.md) based on confidence thresholds
- Let your [AI agent](ai_agents.md) write the integration code for you — one-line install for Claude Code, Cursor, Copilot, and many more
