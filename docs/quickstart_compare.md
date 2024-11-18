# Quickstart Compare Guide
Directly ask real humans to compare your data. This guide will show you how to create a compare order using the Rapidata API.

We will create an order, specify the compare criteria we want to have, as well as upload the data we want to compare.

Our annotators will then label the data according to the criteria we provided.

They see the following screen:

![Compare Example](./media/order-types/compare-screen.png){ width="40%" }

## Installation

Install Rapidata using pip:

```
pip install -U rapidata
```

## Usage

Orders are managed through the [`RapidataClient`](reference/rapidata/rapidata_client/rapidata_client.md#rapidata.rapidata_client.rapidata_client.RapidataClient).

Create a client as follows:

```py
from rapidata import RapidataClient

#first time executing it on a machine will require you to log in
rapi = RapidataClient()
```

### Creating an Order

1. Create a new `Compare Order` and specify the name:

```py
order_builder = rapi.create_compare_order("Example Compare Order")
```

2. Add the criteria for the comparison.

```py
order_builder = order_builder.criteria("Which logo looks better?")
```

3. Add the paths to the images you want to compare. Note that this is a list of lists, where the inner list represents the images that will be compared. The order of those 2 images will be randomized:

```py
# URL
order_builder = order_builder.media([
        ["https://assets.rapidata.ai/rapidata_logo.png",
        "https://assets.rapidata.ai/rapidata_concept_logo.jpg"]])
```
```py
# Local file
order_builder = order_builder.media([
        ["examples/data/rapidata_logo.png","examples/data/rapidata_concept_logo.jpg"]])
```

4. Optionally add additional specifications. Here we're adding a specific amount of responses<sup>1</sup> we want per datapoint, there are other functionalities you can explore by looking at the order_builder methods:

```py
order_builder = order_builder.responses(20)
```

5. Finally create the order. This sends the order off for verification and will start collecting responses.

```py
order = order_builder.create()
```

6. You can see your orders on the [Rapidata Dashboard](https://app.rapidata.ai/dashboard/orders).

### Short Form

The `RapidataSDK` supports a fluent interface, allowing method call chaining. This enables a more concise order creation:

```py
order = (rapi.create_compare_order("Example Compare Order")
        .criteria("Which logo looks better?")
        .media([
        ["https://assets.rapidata.ai/rapidata_logo.png",
        "https://assets.rapidata.ai/rapidata_concept_logo.jpg"]])
        .responses(20)
        .create())
```

### Retrieve Orders

To Retrieve old orders, you can use the `find_orders` method. This method allows you to filder by name and amount of orders to retrieve:

```py
example_orders = rapi.find_orders("Example Compare Order")

# if no name is provided it will just return the most recent one
most_recent_order = rapi.find_orders()[0]
```

### Monitoring Order Progress

You can monitor the progress of the order on the [Rapidata Dashboard](https://app.rapidata.ai/dashboard/orders) or by checking how many datapoints are already done labeling (keep in mind that this will be an exponential function since the datapoints get picket at random to be labeled):

```py
order.display_progress_bar()
```

### Downloading Results

To download the results simply call the `get_results` method on the order:

```py
results = order.get_results()
```

---

<sup>1</sup> Due to the possibility of multiple people answering at the same time, this number is treated as a minimum. The actual number of responses may be higher. The overshoot per datapoint will be lower the more datapoints are added.
