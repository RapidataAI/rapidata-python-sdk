# Quickstart Classification Guide

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

1. Create a new `Compare Order` and specify the name:

```py
order_builder = rapi.create_compare_order("Simple Compare")
```

2. Add the criteria for the comparison.

```py
order_builder = order_builder.criteria("Which logo looks better?")
```

3. Add the paths to the images you want to classify:

```py
order_builder = order_builder.media([["examples/data/rapidata_logo.png", "examples/data/rapidata_concept_logo.jpg"]])
```

4. Optionally add additional specifications, here we're adding a specific amount of votes we want per datapoint, there are other functionalities you can explore:

```py
order_builder = order_builder.votes(20)
```

5. Finally create the order. This sends the order off for verification and will start collecting responses.

```py
order = order_builder.create()
```

6. Save the order ID for future reference, especially if you need to download results later after restarting the kernel:

```py
print("order id: ", order.order_id)
# Optionally save the order ID to a file
with open("order_ids.txt", "a") as file:
    file.write(f"{order.order_id}\n")
```

### Short Form

The `RapidataSDK` supports a fluent interface, allowing method call chaining. This enables a more concise order creation:

```py
order = (rapi.create_compare_order("Simple Compare")
        .criteria("Which logo looks better?")
        .media([["examples/data/rapidata_logo.png", 
                 "examples/data/rapidata_concept_logo.jpg"]])
        .votes(20)
        .create())
print("order id: ", order.order_id)
# Optionally save the order ID to a file
with open("order_ids.txt", "a") as file:
    file.write(f"{order.order_id}\n")
```

### Recover Order

If you've restarted the kernel, you can retrieve the order using the order ID and the `rapi` client:

```py
from rapidata import RapidataClient

rapi = RapidataClient(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
order_id = "your_order_id"  # as a string
order = rapi.get_order(order_id)
results = order.get_results()
```

### Monitoring Order Progress

You can monitor the progress of the order by checking how many datapoints are already done labeling (keep in mind that this will be an exponential function since the datapoints get picket at random to be labeled):

```py
order.display_progress_bar()
```

### Downloading Results

To download the results after the order is done, you'll need the order object (this will throw an error if the order is not complete yet, or the aggregation hasn't finished):

```py
results = order.get_results()
```
