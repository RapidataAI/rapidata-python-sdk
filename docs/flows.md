# Flows

Flows collect human responses on small batches of data. Create a flow once with an instruction and evaluation settings, then reuse it for new batches without creating a full job each time. Flows support images, videos, audio, and text.

## How a Flow Works

1. **Create a flow** to define how annotators evaluate your data.
2. **Submit a batch** with `create_new_flow_batch()`. The SDK uploads the datapoints and returns a flow item representing that batch. Each batch runs independently using the flow's configuration.
3. **Retrieve results** with `flow_item.get_results()`. This waits for the batch to finish; `flow_item.get_status()` checks its status without blocking.

Each batch has a time limit (`time_to_live`), up to 1 hour, with a default of 4 minutes. It must also leave at least 20 seconds before the flow's drain starts, so the minimum is the drain plus 20 seconds: 60 seconds with the default 40-second drain. When time runs out, you can retrieve the responses collected so far. Whether the batch is marked `Completed` or `Incomplete` depends on the response thresholds for its flow type.

The drain is the last part of each batch's `time_to_live`. During it, the batch is no longer shown to new annotators, but annotators who already have a task can still answer. By default the drain equals the flow's serve timeout (40 seconds), the time an annotator has to answer a task. Set it explicitly with `drain_duration` when creating the flow or in `update_config()`.

## Choose a Flow Type

| Flow | Use it to | Context | Results |
| --- | --- | --- | --- |
| [Classify](flows/classify.md) | Assign each datapoint to a category | One text context and one list of context assets per datapoint | Category distribution and majority value per datapoint |
| [Ranking](flows/ranking.md) | Compare the items in a batch against each other | One shared text context and list of context assets | A score per item and total comparison count |

`create_classify_flow()` returns a `RapidataClassifyFlow`; `create_ranking_flow()` returns a `RapidataRankingFlow`. Both inherit shared listing and deletion methods from `RapidataFlow` and can be imported from `rapidata`. Follow the linked guide for creation, batch inputs, response thresholds, and results.

## Managing Flows

Initialize a client to manage your flows:

```python
from rapidata import RapidataClient

client = RapidataClient()
```

### Preheating

If you need low-latency responses for upcoming flow items, you can preheat the system beforehand:

```python
client.flow.preheat()
```

This warms up internal resources so that subsequent flow batches are processed faster. Call it around 5 minutes before submitting time-sensitive batches.

### Retrieving Existing Flows

You can retrieve flows by ID or list your recent flows:

```python
# Get a specific flow by ID
flow = client.flow.get_flow_by_id("flow_id_here")

# List recent flows
recent_flows = client.flow.find_flows(amount=10)
```

`get_flow_by_id()` and `find_flows()` return `RapidataRankingFlow` or `RapidataClassifyFlow` instances according to the stored flow type. Narrow the type before passing kind-specific batch arguments:

```python
from rapidata import RapidataClassifyFlow

flow = client.flow.get_flow_by_id("flow_id_here")
if isinstance(flow, RapidataClassifyFlow):
    flow_item = flow.create_new_flow_batch(
        datapoints=["https://example.com/image_a.jpg"],
        contexts=["Screenshot of a landing page"],
    )
```

### Listing Batches

To list the flow items of a flow, newest first and 10 per page by default:

```python
recent_items = flow.get_flow_items()
```

### Deleting a Flow

```python
flow.delete()
```
