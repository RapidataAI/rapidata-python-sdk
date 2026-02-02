# Quickstart Guide

Get real humans to label your data. This guide shows you how to create a labeling job using the Rapidata API.

The workflow consists of three main concepts:

1. **Audience**: A group of labelers who will work on your tasks
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

### Step 1: Get an Audience

The simplest way to get started is with the global audience - a pre-existing pool of labelers ready to work on your tasks:

```py
audience = client.audience.get_audience_by_id("global")
```

> **Note**: The global audience gets you started quickly, but results may be less accurate than a custom audience trained with examples specific to your task. For higher quality, see [Custom Audiences](audiences.md).

### Step 2: Create a Job Definition

A job definition configures what you want labeled. Here we create a compare job to assess image-prompt alignment:

```py
job_definition = client.job.create_compare_job_definition(
    name="Example Image Comparison",
    instruction="Which image matches the description better?",
    datapoints=[
        ["https://assets.rapidata.ai/midjourney-5.2_37_3.jpg",
         "https://assets.rapidata.ai/flux-1-pro_37_0.jpg"]
    ],
    contexts=["A small blue book sitting on a large red book."]
)
```

> **Tip**: If some datapoints fail to upload, a `FailedUploadException` will be raised. Learn how to handle this in the [Error Handling Guide](error_handling.md).

For a detailed explanation of all available parameters (including name, instruction, datapoints, contexts, quality control options, and more), see the [Job Definition Parameters Reference](job_definition_parameters.md).

### Step 3: Preview the Job Definition

Before running your job, preview it to see exactly what labelers will see:

```py
job_definition.preview()
```

This opens your browser where you can review and adjust the job configuration.

### Step 4: Run and Get Results

Assign your job definition to the audience and monitor progress:

```py
job = audience.assign_job(job_definition)
job.display_progress_bar()
```

Once complete, retrieve your results:

```py
results = job.get_results()
```

You can also monitor progress on the [Rapidata Dashboard](https://app.rapidata.ai/dashboard).

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

Here's the full workflow using the global audience:

```py
from rapidata import RapidataClient

client = RapidataClient()

# Get the global audience
audience = client.audience.get_audience_by_id("global")

# Create job definition
job_definition = client.job.create_compare_job_definition(
    name="Example Image Comparison",
    instruction="Which image matches the description better?",
    datapoints=[
        ["https://assets.rapidata.ai/midjourney-5.2_37_3.jpg",
         "https://assets.rapidata.ai/flux-1-pro_37_0.jpg"]
    ],
    contexts=["A small blue book sitting on a large red book."]
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

- Create [Custom Audiences](audiences.md) for higher quality results
- Learn about [Classification Jobs](examples/classify_job.md) for categorizing data
- Understand the [Results Format](understanding_the_results.md)
- Configure [Early Stopping](confidence_stopping.md) based on confidence thresholds
- Migrating from Orders? See the [Migration Guide](migration_guide.md)
