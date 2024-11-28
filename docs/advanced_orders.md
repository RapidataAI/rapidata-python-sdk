# Advanced orders examples
Directly ask real humans to classify your data. This guide will show you how to create the same classification order shown in the [Quickstart](quickstart.md) using the advanced order builder which allows for more options and customization.

We will create an order, specify what question and answer options we want to have, as well as upload the data we want to classify.

Our annotators will then label the data according to the question and answer options we provided.

They see the following screen:

![Classify Example](./media/order-types/classify-screen.png){ width="40%" }

## Usage

Orders are managed through the [`RapidataClient`](reference/rapidata/rapidata_client/rapidata_client.md#rapidata.rapidata_client.rapidata_client.RapidataClient).

Create a client as follows:

```py
from rapidata import RapidataClient

#first time executing it on a machine will require you to log in
rapi = RapidataClient()
```
### Creating an Order

Each request to humans begins with creating an order. Use the `rapi` client to configure the order according to your needs.

1. Create a new [`RapidataOrderBuilder`](reference/rapidata/rapidata_client/order/rapidata_order_builder.md/#rapidata.rapidata_client.order.rapidata_order_builder.RapidataOrderBuilder) and specify the name:

```py
order_builder = rapi.new_complex_order("Example Custom Order")
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

3. (Optional) Further configure the order by specifying the number of responses<sup>1</sup> desired for each datapoint (default is 10). Choose either a [`NaiveReferee`](reference/rapidata/rapidata_client/referee/naive_referee.md/#rapidata.rapidata_client.referee.naive_referee.NaiveReferee) or a [`EarlyStoppingReferee`](reference/rapidata/rapidata_client/referee/early_stopping_referee.md/#rapidata.rapidata_client.referee.early_stopping_referee.ClassifyEarlyStoppingReferee)<sup>2</sup>:

```py
from rapidata import NaiveReferee

order_builder.referee(NaiveReferee(responses=15))
```

4. Upload datapoints for which you want this question to be asked. In this example, we upload one image:

```py
# URL
from rapidata import MediaAsset
order_builder.media([MediaAsset("https://assets.rapidata.ai/wallaby.jpg")])
```

```py
# Local file
from rapidata import MediaAsset
order_builder.media([MediaAsset("examples/data/wallaby.jpg")])
```

5. Define the number of tasks you'd like to show in a row. Consider that a person only has 30 seconds to answer all of them. Aim for an expected completion time for ALL tasks of 20-25 seconds. A good default for classification is 3:

```py
from rapidata import LabelingSelection

order_builder.selections([
    LabelingSelection(amount=3)
])
```

6. Create the order. This sends off all the datapoints to be verified and starts collecting responses:

```py
order = order_builder.create()
```

7. You can see your orders on the [Rapidata Dashboard](https://app.rapidata.ai/dashboard/orders).

### Short Form

The [`RapidataOrderBuilder`](reference/rapidata/rapidata_client/order/rapidata_order_builder.md/#rapidata.rapidata_client.order.rapidata_order_builder.RapidataOrderBuilder) supports a fluent interface, allowing method call chaining. This enables a more concise order creation:

```py
order = (
    rapi.new_complex_order(name="Example Custom Order")
    .workflow(
        ClassifyWorkflow(
            question="What is shown in the image?",
            options=["Fish", "Cat", "Wallaby", "Airplane"],
        )
    )
    .referee(NaiveReferee(responses=15))
    .media([MediaAsset("https://assets.rapidata.ai/wallaby.jpg")])
    .selections([LabelingSelection(amount=1)])
    .create()
)
```

### Retrieve Orders

To Retrieve old orders, you can use the `find_orders` method. This method allows you to filter by name and amount of orders to retrieve:

```py
example_orders = rapi.find_orders("Example Custom Order")

# if no name is provided it will just return the most recent one
most_recent_order = rapi.find_orders()[0]
```

### Monitoring Order Progress

You can monitor the progress of the order on the [Rapidata Dashboard](https://app.rapidata.ai/dashboard/orders) or by checking how many datapoints are already done labeling:

```py
order.display_progress_bar()
```

### Downloading Results

To download the results simply call the `get_results` method on the order:

```py
results = order.get_results()
```

-------

<sup>1</sup> Due to the possibility of multiple people answering at the same time, this number is treated as a minimum. The actual number of responses may be higher. The overshoot per datapoint will be lower the more datapoints are added.

<sup>2</sup> The Referee is responsible for deciding when to stop collecting responses. The `NaiveReferee` will stop collecting responses after the specified number of responses is reached. The `EarlyStoppingReferee` will stop collecting responses if either the confidence threshold is reached or the max votes have been collected - This is valuable if there is a clear correct answer but less so if it's an opinion  based question.
