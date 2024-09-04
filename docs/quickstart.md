# Quickstart

## Installation

In the future:

```
pip install rapidata
```

## Usage

Orders are managed throught the {py:class}`rapidata.rapidata_client.RapidataClient`.

One can create client like this:

```
from rapidata.rapidata_client import RapidataClient


rapi = RapidataClient(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
```

Ask a Rapidata representative for your `CLIENT_ID` and `CLIENT_SECRET` (info@rapidata.ai).

### Creating an Order

Creating an order is done using the created `rapi` client.

1. Create a new `OrderBuilder` {py:class}`rapidata.rapidata_client.order.rapidata_order_builder` and specify the name:

```
order_builder = rapi.new_order("Example Order")
```

2. Configure the order using a workflow. For example, the {py:class}`rapidata.rapidata_client.workflow.classify_workflow.ClassifyWorkflow` asks a question with multiple answer choices:

```
workflow = ClassifyWorkflow(
            question="Who should be president?",
            categories=["Kamala Harris", "Donald Trump"],
        )
```

Optionally, you can further configure the workflow by specifying the number of answers desired for each datapoint with this question:

```
workflow.referee(NaiveReferee(required_guesses=15))
```

Now, set the `workflow` on the `order_builder`:
```
order_builder.workflow(workflow)
```

3. Create the order
```
order = order_builder.create()
```

4. Upload datapoints for which you want this question to be asked. For this case, we only upload one image:
```
order.dataset.add_images_from_paths(["examples/data/kamala_trump.jpg"])
```
5. Submit the order:
```
order.submit()
```


### Short Form

The `order_builder` and `workflow` support a fluent interface, which makes chaining of method calls possible. This allows to achieve everything in a short snippet:

```
order = (
    rapi.new_order(
        name="Example Classify Order",
    )
    .workflow(
        ClassifyWorkflow(
            question="Who should be president?",
            categories=["Kamala Harris", "Donald Trump"],
        )
        .referee(NaiveReferee(required_guesses=15))
    )
    .create()
)

order.dataset.add_images_from_paths(["examples/data/kamala_trump.jpg"])
order.submit()
```