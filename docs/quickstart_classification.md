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

1. Create a new `Classification Order` and specify the name:

```py
order_builder = rapi.create_classify_order("Simple Classification")
```

2. Add the question you want to ask.

```py
order_builder = order_builder.question("What is shown in the image?")
```

3. add the different answer options:

```py
order_builder = order_builder.options(["Fish", "Cat", "Wallaby", "Airplane"])
```

4. Add the paths to the images you want to classify:

```py
order_builder = order_builder.media(["examples/data/wallaby.jpg"])
```

5. Optionally add additional specifications, here we're adding a specific amount of votes we want per datapoint, there are other functionalities you can explore:

```py
order_builder = order_builder.votes(20)
```

6. Finally create the order. This sends the order off for verification and will start collecting responses.

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

The `RapidataSDK` supports a fluent interface, allowing method call chaining. This enables a more concise order creation:

```py
order = (rapi.create_classify_order("classifcaiton order")
         .question("what is this?")
         .options(["a", "b", "c"])
         .media(["C:\\Users\\linog\\Pictures\\example_jpg.jpg"])
         .votes(20)
         .create())
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
