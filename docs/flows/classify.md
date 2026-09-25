# Classify Flows

Use a classify flow to assign each datapoint to one of your categories. Each datapoint is evaluated independently. `create_classify_flow()` returns a `RapidataClassifyFlow`.

For the shared lifecycle and flow management methods, see the [flow overview](../flows.md).

## 1. Create a Flow

Create a classify flow with the question shown for every item and the categories annotators choose from:

```python
from rapidata import RapidataClient

client = RapidataClient()

flow = client.flow.create_classify_flow(
    name="Text Detection",
    instruction="Does this image contain text?",
    categories=["Yes", "No"],
)
```

A flow has between 2 and 8 categories, shared by every batch of the flow.

You can optionally configure a **response threshold range** per datapoint:

- `max_responses_per_datapoint` (default `15`): the number of accepted responses that closes an image. Collection for that image stops once it's reached.
- `min_responses_per_datapoint` (default `10`): the minimum average responses per image you're willing to accept. If the batch's `time_to_live` expires and the item's total responses are below `min_responses_per_datapoint × number of images`, the item is marked as **Incomplete**. Otherwise it's **Completed**.

```python
flow = client.flow.create_classify_flow(
    name="Text Detection",
    instruction="Does this image contain text?",
    categories=["Yes", "No"],
    max_responses_per_datapoint=15, # (1)!
    min_responses_per_datapoint=10, # (2)!
)
```

1. The number of accepted responses that closes an image. Collection for that image stops once it's reached.
2. The minimum average responses per image. If the batch's `time_to_live` expires with the item's total responses below this times the number of images, it's marked **Incomplete**; otherwise **Completed**.

Each response is billed. A batch collects up to `max_responses_per_datapoint` responses for each of its items, so a six-item batch with the default maximum collects up to 15 × 6 = 90 responses.

The instruction, categories, and response thresholds are fixed once the flow exists: `update_config()` is only available on `RapidataRankingFlow`, so create a new flow to change them.

## 2. Add a Flow Batch

Submit the items to classify. Every item is classified independently with the flow's instruction and categories:

```python
flow_item = flow.create_new_flow_batch(
    datapoints=[
        "https://example.com/image_a.jpg",
        "https://example.com/image_b.jpg",
        "https://example.com/image_c.jpg",
    ],
)
```

Context is attached per item. `contexts: list[str]` and `context_assets: list[list[str]]` take exactly one entry per datapoint and show it alongside that datapoint:

```python
flow_item = flow.create_new_flow_batch(
    datapoints=[
        "https://example.com/image_a.jpg",
        "https://example.com/image_b.jpg",
        "https://example.com/image_c.jpg",
    ],
    contexts=[ # (1)!
        "Screenshot of a landing page",
        "Product photo",
        "Concert poster",
    ],
    context_assets=[
        ["https://example.com/reference_a.jpg", "https://example.com/reference_a2.jpg"],
        ["https://example.com/reference_b.jpg"],
        ["https://example.com/reference_c.jpg"],
    ],
    time_to_live=120, # (2)!
)
```

1. One text context per datapoint, shown together with that datapoint. `context_assets` takes one list of image, video, or audio paths/URLs per datapoint.
2. Stops the flow item after this many seconds and returns the responses collected so far. Between 70 seconds and 1 hour; defaults to 4 minutes when omitted.

Each `context_assets` entry is a list, even when it contains only one asset. Omit `contexts` or `context_assets` when it is not needed.

## 3. Get Results

Call `get_results()` on the flow item. This waits until the batch completes or its time to live expires:

```python
results = flow_item.get_results()
```

This returns a `ClassifyFlowItemResult`. For the batch above it looks like this:

```python
ClassifyFlowItemResult(
    datapoints={
        "https://example.com/image_a.jpg": ClassifyDatapointResult(
            majority_value="Yes", distribution={"Yes": 4, "No": 1}, response_count=5
        ),
        "https://example.com/image_b.jpg": ClassifyDatapointResult(
            majority_value="No", distribution={"Yes": 0, "No": 5}, response_count=5
        ),
        "https://example.com/image_c.jpg": ClassifyDatapointResult(
            majority_value=None, distribution={"Yes": 2, "No": 2}, response_count=4
        ),
    },
    total_responses=14,
)
```

It has two fields:

- `datapoints`: a mapping of each item to its `ClassifyDatapointResult`. Items are keyed by their source URL when provided, otherwise by their original filename. `majority_value` is the category value chosen most often, or `None` when the top categories are tied. `distribution` counts the responses for every category of the flow, in the flow's category order (categories nobody chose show `0`), and `response_count` is the number of responses collected for that item.
- `total_responses`: the total number of responses collected across all items.

```python
for item, result in results.datapoints.items():
    print(item, result.majority_value, result.distribution)
```

`flow_item.get_status()` checks the batch status without blocking, and `flow_item.get_response_count()` returns `total_responses`. The win/loss matrix is a ranking concept: `get_win_loss_matrix()` raises a `ValueError` on a classify flow item.

!!! note
    A classify flow item enters the `Incomplete` state when its `time_to_live` expires with total responses below `min_responses_per_datapoint × number of images` (an average per image). Otherwise it's `Completed` — including when every image already reached `max_responses_per_datapoint`. Compare each image's `response_count` with `max_responses_per_datapoint` to see which images, if any, got fewer responses than others.
