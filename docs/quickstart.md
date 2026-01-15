# Quickstart Guide

Get real humans to label your data. This guide shows you how to create a labeling job using the Rapidata API.

The workflow consists of three main concepts:

1. **Audience**: A group of qualified labelers who have passed your qualification examples
2. **Job Definition**: The configuration for your labeling task (instruction, datapoints, settings)
3. **Job**: A running labeling task assigned to an audience

## Installation

Install Rapidata using pip:

```
pip install -U rapidata
```

## Usage

All operations are managed through the [`RapidataClient`](reference/rapidata/rapidata_client/rapidata_client.md#rapidata.rapidata_client.rapidata_client.RapidataClient).

Create a client as follows. This will save your credentials in your `~/.config/rapidata/credentials.json` file so you don't have to log in again on that machine:

```py
from rapidata import RapidataClient

# The first time executing it on a machine will require you to log in
client = RapidataClient()
```

Alternatively you can generate a Client ID and Secret in the [Rapidata Settings](https://app.rapidata.ai/settings/tokens) and pass them to the client constructor:

```py
from rapidata import RapidataClient
client = RapidataClient(client_id="Your client ID", client_secret="Your client secret")
```

### Step 1: Create an Audience

An audience is a pool of labelers who are qualified to work on your tasks. You create an audience and add qualification examples that labelers must answer correctly to join.

```py
audience = client.audience.create_audience(name="Image Comparison Audience")
```

### Step 2: Add Qualification Examples

Add examples that labelers must answer correctly to join your audience. This ensures only qualified labelers work on your data.

```py
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

The parameters are:

- `instruction`: The question shown to labelers
- `datapoint`: The two items to compare
- `truth`: The correct answer (must be one of the datapoint items)
- `context`: Additional context shown alongside the comparison (optional)

### Step 3: Create a Job Definition

A job definition configures what you want labeled. Here we create a compare job to assess image-prompt alignment:

```py
job_definition = client.job.create_compare_job_definition(
    name="Prompt Alignment Comparison",
    instruction="Which image follows the prompt more accurately?",
    datapoints=[
        ["https://assets.rapidata.ai/flux_sign_diffusion.jpg",
         "https://assets.rapidata.ai/mj_sign_diffusion.jpg"],
        ["https://assets.rapidata.ai/flux_flower.jpg",
         "https://assets.rapidata.ai/mj_flower.jpg"]
    ],
    contexts=[
        "A sign that says 'Diffusion'.",
        "A yellow flower sticking out of a green pot."
    ]
)
```

For a detailed explanation of all available parameters (including name, instruction, datapoints, contexts, quality control options, and more), see the [Job Definition Parameters Reference](job_definition_parameters.md).

### Step 4: Preview the Job Definition

Before running your job, preview it to see exactly what labelers will see:

```py
job_definition.preview()
```

This opens your browser where you can review and adjust the job configuration.

### Step 5: Assign Job to Audience

Once you're satisfied with your job definition, assign it to your audience to start collecting responses:

```py
job = audience.assign_job(job_definition)
```

Labelers who have passed your qualification examples will now start working on your data.

### Step 6: Monitor Progress and Get Results

Monitor progress on the [Rapidata Dashboard](https://app.rapidata.ai/dashboard) or programmatically:

```py
job.display_progress_bar()
```

Once complete, retrieve your results:

```py
results = job.get_results()
```

To understand the results format, see the [Understanding the Results](understanding_the_results.md) guide.

## Retrieve Existing Resources

### Find Audiences

```py
# Find audiences by name
audiences = client.audience.find_audiences("Image Comparison")

# Get a specific audience by ID
audience = client.audience.get_audience_by_id("audience_id")
```

### Find Job Definitions

```py
# Find job definitions by name
job_definitions = client.job.find_job_definitions("Prompt Alignment")

# Get a specific job definition by ID
job_definition = client.job.get_job_defintion_by_id("job_definition_id")
```

### Find Jobs

```py
# Find jobs by name
jobs = client.job.find_jobs("Prompt Alignment")

# Get a specific job by ID
job = client.job.get_job_by_id("job_id")

# Find jobs for a specific audience
audience = client.audience.get_audience_by_id("audience_id")
jobs = audience.find_jobs("Prompt Alignment")
```

> **Note**: The `find_*` can be executed without the `name` parameter to return the most recent resources.

## Complete Example

Here's the full workflow in one script:

```py
from rapidata import RapidataClient

client = RapidataClient()

# Create and configure audience
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

## Next Steps

- Learn about [Classification Jobs](examples/classify_job.md) for categorizing data
- Understand the [Results Format](understanding_the_results.md)
- Configure [Early Stopping](confidence_stopping.md) based on confidence thresholds
- Migrating from Orders? See the [Migration Guide](migration_guide.md)
