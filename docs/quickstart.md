# Quickstart Guide

Directly ask real humans to compare your data. This guide will show you how to create a compare order using the Rapidata API.

There are many other types of orders you can create which you can find in the examples on the [Overview](index.md).

We will create an order assessing image-prompt-alignment, using 2 AI generated images and compare them against each other based on which image followed the prompt more accurately.

Our annotators will then label the data according to the instruction we provided.

They see the following screen:

![Compare Example](./media/compare_quickstart.png){ width="40%" }

## Installation

Install Rapidata using pip:

```
pip install "rapidata<3.0.0"
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

Here we create a compare order with a name and the instruction / question we want to ask. Additionally, we provide the prompt as context:

```py
order = rapi.order.create_compare_order(
    name="Example Alignment Order",
    instruction="Which image matches the description better?",
    contexts=["A small blue book sitting on a large red book."],
    datapoints=[["https://assets.rapidata.ai/midjourney-5.2_37_3.jpg", 
                "https://assets.rapidata.ai/flux-1-pro_37_0.jpg"]],
)
```
> **Note:** When calling this function the data gets uploaded and prepared, but no annotators will start working on it yet.

For a detailed explanation of all available parameters (including `name`, `instruction`, `datapoints`, `contexts`, quality control options, and more), see the [Order Parameters Reference](order_parameters.md).

### Preview the Order

You can see how the users will be presented with the task by calling the `.preview()` method on the order object to make sure everything looks as expected:

```py
order.preview()
```

### Start Collecting Responses
To start the order and collect responses, call the `run` method:

```py
order.run()
```

Once you call this method, annotators will start working on your order immediately.


### Retrieve Orders

To retrieve old orders, you can use the `find_orders` method. This method allows you to filter by name and amount of orders to retrieve:

```py
example_orders = rapi.order.find_orders("Example Alignment Order")

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

To better understand the results you can check out the [Understanding the Results](/understanding_the_results/) guide.

## Next Steps

This is just the beginning. You can create many different types of orders and customize them to your needs. Check out the [Overview](index.md) for more examples and information or check out how to improve the quality of your responses in the [Improve Quality](/improve_order_quality/).
