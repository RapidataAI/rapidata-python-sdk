# Quickstart

## Installation

```
pip install rapidata
```

or to update:

```
pip install rapidata -U
```

## Usage

Rapidata provides an API to millions of users across the globe. The

Orders are managed throught the {py:class}`~rapidata.rapidata_client.RapidataClient`.

One can create client like this:

```
from rapidata.rapidata_client import RapidataClient


rapi = RapidataClient(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
```

Ask a Rapidata representative for your `CLIENT_ID` and `CLIENT_SECRET` (info@rapidata.ai).

### Creating an Order

Each request to humans starts with creating order. Creating an order is done using the created `rapi` client and going through the configuration options to taylor the order to your needs.

1. Create a new {py:class}`~rapidata.rapidata_client.order.rapidata_order_builder.RapidataOrderBuilder` and specify the name:

```
order_builder = rapi.new_order("Quickstart Order")
```

2. Configure the order using a workflow, which defines the type of questions asked to the people. For example, the {py:class}`~rapidata.rapidata_client.workflow.classify_workflow.ClassifyWorkflow` asks a question with multiple answer choices:

```
workflow = ClassifyWorkflow(
            question="What is shown in the image?",
            options=["Fish", "Cat", "Wallaby", "Airplane"],
        )
```

Now, set the `workflow` on the `order_builder`:

```
order_builder.workflow(workflow)
```

Optionally, you can further configure the order by specifying the number of answers desired for each datapoint with this question. This is done by choosing a {py:class}`~rapidata.rapidata_client.referee`:

```
order_builder = order_builder.referee(NaiveReferee(required_guesses=15))
```

Now, set the `workflow` on the `order_builder`:

```
order_builder.workflow(workflow)

3. Upload datapoints for which you want this question to be asked. For this case, we only upload one image:
```

order.dataset.add_images_from_paths(["examples/data/wallaby.jpg"])

```

4. Finally, create the order. This executes all the actual HTTP requests to the Rapidata API. Per default, a created order is directly submitted. If this is not intended, specify `submit=
```

order = order_builder.create()

```
### Short Form

The `order_builder` supports a fluent interface, which makes chaining of method calls possible. This allows to achieve everything in a short snippet:

```
order = (
        rapi.new_order(
            name="Example Classify Order",
        )
        .workflow(
            ClassifyWorkflow(
                question="What is shown in the image?",
                options=["Fish", "Cat", "Wallaby", "Airplane"],
            )
        )
        .referee(NaiveReferee(required_guesses=15))
        .media(["examples/data/wallaby.jpg"])
        .create()
    )
```
