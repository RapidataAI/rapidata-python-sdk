# Ranking Flows

## Overview

Ranking Flows provide a lightweight way to continuously rank items using human comparisons without the overhead of creating full orders. They are ideal for ongoing evaluation where new items are added over time and ranked against existing ones using an ELO-based rating system.

> **Note:** Can be used with Images, Videos, Audio, and Text.

## How to use Ranking Flows

### 1. Create a Flow

Start by creating a ranking flow with an instruction that will be shown to evaluators for each comparison:

```python
from rapidata import RapidataClient

client = RapidataClient()

flow = client.flow.create_ranking_flow(
    name="Image Quality Ranking",
    instruction="Which image looks better?",
    responses_per_comparison=1,
)
```

### 2. Add a Flow Batch

Submit datapoints to the flow by creating a batch. Each batch uploads a set of items that will be compared and ranked:

```python
flow_item = flow.create_new_flow_batch(
    datapoints=[
        "https://example.com/image_a.jpg",
        "https://example.com/image_b.jpg",
        "https://example.com/image_c.jpg",
    ],
)
```

You can also provide text datapoints or add context:

```python
flow_item = flow.create_new_flow_batch(
    datapoints=["Response from Model A", "Response from Model B"],
    contexts=["Prompt: Explain quantum computing", "Prompt: Explain quantum computing"],
    data_type="text",
)
```

### 3. Check Flow Item Status

Each batch is processed as a flow item. You can check its status:

```python
status = flow_item.get_status()  # Pending, Running, Completed, or Failed
```

You can also query all flow items for a flow, optionally filtering by state:

```python
from rapidata.api_client.models.flow_item_state import FlowItemState

# Get all completed items
completed_items = flow.get_flow_items(state=FlowItemState.COMPLETED)

# Get all items
all_items = flow.get_flow_items()
```

### 4. Update Flow Configuration

You can update the flow configuration at any time:

```python
flow.update_config(
    instruction="Which image has higher visual quality?",
    responses_per_comparison=3,
)
```

### Retrieving Existing Flows

You can retrieve flows by ID or list your recent flows:

```python
# Get a specific flow by ID
flow = client.flow.get_flow_by_id("flow_id_here")

# List recent flows
recent_flows = client.flow.find_flows(amount=10)
```

### Deleting a Flow

```python
flow.delete()
```
