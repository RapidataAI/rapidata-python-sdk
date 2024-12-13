# Quickstart Guide

Directly ask real humans to classify your data. This guide will show you how to create a classification order using the Rapidata API.

There are many other types of orders you can create which you can find in the examples on the [Overview](index.md).

We will create an order, specify what question and answer options we want to have, as well as upload the data we want to classify.

Our annotators will then label the data according to the question and answer options we provided.

They see the following screen:

![Classify Example](./media/order-types/classify-screen.png){ width="40%" }

## Installation

Install Rapidata using pip:

```
pip install -U rapidata
```


## Usage

Orders are managed through the [`RapidataClient`](reference/rapidata/rapidata_client/rapidata_client.md#rapidata.rapidata_client.rapidata_client.RapidataClient).

Create a client as follows, this will save your credentials in your `~/.config/rapidata/credentials.json` file so you don't have to log in again on that machine:

```py
from rapidata import RapidataClient

#The first time executing it on a machine will require you to log in
rapi = RapidataClient()
```

Alternatively you can generate a Client ID and Secret in the [Rapidata Settings](https://app.rapidata.ai/settings/tokens) and pass them to the [`RapidataClient`](reference/rapidata/rapidata_client/rapidata_client.md#rapidata.rapidata_client.rapidata_client.RapidataClient) constructor:

```py
from rapidata import RapidataClient
rapi = RapidataClient(client_id="Your client ID", client_secret="Your client secret")
```

### Creating an Order

All order-related operations are performed using rapi.order.

1. Here we create a classification order with a name and the instruction / question we want to ask:

```py
order = rapi.order.create_classification_order(
    name="Example Classification Order",
    instruction="What is shown in the image?",
    answer_options=["Fish", "Cat", "Wallaby", "Airplane"],
    datapoints=["https://assets.rapidata.ai/wallaby.jpg"]
)
```
The parameters are as follows:

- `name`: The name of the order. This is used to identify the order in the [Rapidata Dashboard](https://app.rapidata.ai/dashboard/orders). This name is also be used to find the order again later.
- `instruction`: The instruction you want to show the annotators to select the options by.
- `answer_options`: The different answer options the annotators can choose from.
- `datapoints`: The data you want to classify. This can be any public URL (that points to an image, video or audio) or a local file path. This is a list of all datapoints you want to classify. The same instruction and answer options will be asked for each datapoint. There is a limit of 100 datapoints per order. If you need more than that, you can reach out to us at <info@rapidata.ai>.

Optionally you may add additional specifications with the other parameters. As an example, the `responses_per_datapoint` that specifies how many responses you want per datapoint<sup>1</sup>.

When calling this function the data gets uploaded and prepared, but no annotators will start working on it yet.

2. To start the order and collect responses, call the `run` method:

```py
order.run()
```

### Retrieve Orders

To retrieve old orders, you can use the `find_orders` method. This method allows you to filter by name and amount of orders to retrieve:

```py
example_orders = rapi.order.find_orders("Example Classification Order")

# if no name is provided it will just return the most recent one
most_recent_order = rapi.order.find_orders()[0]
```

Optionally you can also retrieve a specific order using the order ID:

```py
order = rapi.order.get_order_by_id("order_id")
```

### Monitoring Order Progress

You can monitor the progress of the order on the [Rapidata Dashboard](https://app.rapidata.ai/dashboard/orders) or by checking how many datapoints are already done with labeling:

```py
order.display_progress_bar()
```

### Downloading Results

To download the results simply call the `get_results` method on the order:

```py
results = order.get_results()
```

## Credits and Billing

When you first create an account on Rapidata, you will receive 100 free credits. Each credit give you 10 responses. After you have used up your free credits, you may purchase more on our [website](https://app.rapidata.ai/pricing).

## Next Steps

This is just the beginning. You can create many different types of orders and customize them to your needs. Check out the [Overview](index.md) for more examples and information or check out how to improve the quality of your responses in the [Improve Quality](/improve_order_quality/) .

------------------

<sup>1</sup> Due to the possibility of multiple people answering at the same time, this number is treated as a minimum. The actual number of responses may be higher. The overshoot per datapoint will be lower the more datapoints are added.
