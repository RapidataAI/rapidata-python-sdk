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

Create a client as follows, this will save your credentials in a local file so you don't have to log in again on that machine:

```py
from rapidata import RapidataClient

#first time executing it on a machine will require you to log in
rapi = RapidataClient()
```

Alternatively you can generate a Client ID and Secret in the [Rapidata Settings](https://app.rapidata.ai/settings/tokens) and pass them to the [`RapidataClient`](reference/rapidata/rapidata_client/rapidata_client.md#rapidata.rapidata_client.rapidata_client.RapidataClient) constructor:

```py
from rapidata import RapidataClient
rapi = RapidataClient(client_id="Your client ID", client_secret="Your client secret")
```

### Creating an Order

1. Create a new `Classification Order` and specify the name by making use of the `order_builder`:

```py
order_builder = rapi.order_builder.classify_order("Example Classification Order")
```

2. Add the question you want to ask.

```py
order_builder = order_builder.question("What is shown in the image?")
```

3. add the different answer options (the order of the options will be randomized when displayed to the user):

```py
order_builder = order_builder.options(["Fish", "Cat", "Wallaby", "Airplane"])
```

4. Add the paths to the images you want to classify:

```py
# URL
order_builder = order_builder.media(["https://assets.rapidata.ai/wallaby.jpg"])
```

```py
# Local file path
order_builder = order_builder.media(["examples/data/wallaby.jpg"])
```

5. Optionally add additional specifications. here we're adding a specific amount of responses<sup>1</sup> we want per datapoint, there are other functionalities you can explore by looking at the order_builder methods:

```py
order_builder = order_builder.responses(20)
```

6. Finally we want to submit the order. This sends the order off for verification and will start collecting responses.

```py
order = order_builder.submit()
```

7. You can see your orders on the [Rapidata Dashboard](https://app.rapidata.ai/dashboard/orders).


### Short Form

The `RapidataSDK` supports a fluent interface, allowing method call chaining. This enables a more concise order creation:

```py
order = (rapi.order_builder
         .classify_order("Example Classification Order")
         .question("What is shown in the image?")
         .options(["Fish", "Cat", "Wallaby", "Airplane"])
         .media(["https://assets.rapidata.ai/wallaby.jpg"])
         .responses(20)
         .submit())
```

### Retrieve Orders

To Retrieve old orders, you can use the `find_orders` method. This method allows you to filder by name and amount of orders to retrieve:

```py
example_orders = rapi.find_orders("Example Classification Order")

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

------------------

<sup>1</sup> Due to the possibility of multiple people answering at the same time, this number is treated as a minimum. The actual number of responses may be higher. The overshoot per datapoint will be lower the more datapoints are added.
