# Custom orders

## Installation

Install Rapidata using pip:

```
pip install rapidata
```

To update an existing installation:

```
pip install rapidata -U
```

## Usage

Orders are managed through the [`RapidataClient`](reference/rapidata/rapidata_client/rapidata_client.md#rapidata.rapidata_client.rapidata_client.RapidataClient).

Create a client as follows:

```py
from rapidata import RapidataClient

rapi = RapidataClient(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
```

Contact a Rapidata representative at [info@rapidata.ai](mailto:info@rapidata.ai) to obtain your `CLIENT_ID` and `CLIENT_SECRET`.

### Creating an Order

Each request to humans begins with creating an order. Use the `rapi` client to configure the order according to your needs.

1. Create a new [`RapidataOrderBuilder`](reference/rapidata/rapidata_client/order/rapidata_order_builder.md/#rapidata.rapidata_client.order.rapidata_order_builder.RapidataOrderBuilder) and specify the name:

```py
order_builder = rapi.new_order("Quickstart Order")
```

2. Configure the order using a workflow, which defines the type of questions asked to people. For example, the [`ClassifyWorkflow`](reference/rapidata/rapidata_client/workflow/classify_workflow.md) asks a question with multiple answer choices:

```py
from rapidata import ClassifyWorkflow

workflow = ClassifyWorkflow(
    question="What is shown in the image?",
    options=["Fish", "Cat", "Wallaby", "Airplane"],
)
```

Set the `workflow` on the `order_builder`:

```py
order_builder.workflow(workflow)
```

3. (Optional) Further configure the order by specifying the number of answers desired for each datapoint (default is 10). Choose either a [`NaiveReferee`](reference/rapidata/rapidata_client/referee/naive_referee.md/#rapidata.rapidata_client.referee.naive_referee.NaiveReferee) or a [`ClassifyEarlyStoppingReferee`](reference/rapidata/rapidata_client/referee/classify_early_stopping_referee.md/#rapidata.rapidata_client.referee.classify_early_stopping_referee.ClassifyEarlyStoppingReferee):

```py
from rapidata import NaiveReferee

order_builder.referee(NaiveReferee(required_guesses=15))
```

4. Upload datapoints for which you want this question to be asked. In this example, we upload one image:

```py
order_builder.media(["examples/data/wallaby.jpg"])
```

5. Define the number of tasks you'd like to show in a row. Consider that a person only has 30 seconds to answer all of them. Aim for an expected completion time for ALL tasks of 20-25 seconds. A good default for classification is 3:

```py
from rapidata import LabelingSelection

order_builder.selections([
    LabelingSelection(amount=3)
])
```

6. Create the order. This executes all the HTTP requests to the Rapidata API:

```py
order = order_builder.create()
```

7. Save the order ID for future reference, especially if you need to download results later after restarting the kernel:

```py
print("order id: ", order.order_id)
# Optionally save the order ID to a file
with open("order_ids.txt", "a") as file:
    file.write(f"{order.order_id}\n")
```

### Short Form

The [`RapidataOrderBuilder`](reference/rapidata/rapidata_client/order/rapidata_order_builder.md/#rapidata.rapidata_client.order.rapidata_order_builder.RapidataOrderBuilder) supports a fluent interface, allowing method call chaining. This enables a more concise order creation:

```py
order = (
    rapi.new_order(name="Example Classify Order")
    .workflow(
        ClassifyWorkflow(
            question="What is shown in the image?",
            options=["Fish", "Cat", "Wallaby", "Airplane"],
        )
    )
    .referee(NaiveReferee(required_guesses=15))
    .media(["examples/data/wallaby.jpg"])
    .selections([LabelingSelection(amount=1)])
    .create()
)

print("order id: ", order.order_id)
# Optionally save the order ID to a file
with open("order_ids.txt", "a") as file:
    file.write(f"{order.order_id}\n")
```

### Downloading Results

To download the results, you'll need the order object (this will throw an error if the order is not complete yet):

```py
results = order.get_results()
```

If you've restarted the kernel, you can retrieve the order using the order ID and the `rapi` client:

```py
from rapidata import RapidataClient

rapi = RapidataClient(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
order_id = "your_order_id"  # as a string
order = rapi.get_order(order_id)
results = order.get_results()
```
