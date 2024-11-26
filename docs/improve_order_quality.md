# Improve Response Quality

This guide builds on the [Quickstart](quickstart.md) and focuses on improving the quality of responses received for your orders. By creating a **Validation Set**, you can provide clear guidance to labelers, helping them better understand your expectations. While using a validation set is optional, it significantly enhances response accuracy and consistency, especially for more complex or unintuitve tasks.

### Why Use a Validation Set?

A validation set is a collection of tasks with known answers. It provides labelers with examples of how you want your data annotated, offering immediate feedback to align their work with your requirements.

### How does it work?

The validation task has a known truth and will be shown infront of the actual labeling task. Think of it as an interview question before the work starts. The labelers are only allowed to proceed to the actual task if they correctly solve one validation task.

## Example Validation Set

Let’s walk through how to create and use a validation set using the **Compare Order** as an example. The principles apply to any order type.

Here’s what labelers will see during validation for this example:

![Compare Example](./media/order-types/good_bad_ai_image.png){ width="40%" }

### Creating a Validation Set
As always, we start by creating a [`RapidataClient`](reference/rapidata/rapidata_client/rapidata_client.md#rapidata.rapidata_client.rapidata_client.RapidataClient):

```py
from rapidata import RapidataClient

rapi = RapidataClient()
```

1. Create an empty validation set builder with a name to later find it again:

```py
validation_set_builder = rapi.new_validation_set(
        "Example Compare Validataion Set")
```

2. Now that we have the validation set builder, we can start adding tasks to it, where we know the ground truth. In our case, each task is called a 'Rapid'. Let's first create the Rapid, and then add it to the validation set builder:

```py
rapid = (rapi.rapid_builder
         .compare_rapid() # We specify the type of Rapid we want to create
         .criteria("Which of the AI generated images looks more realistic?") # We specifiy the criteria for the labeler how to decide which image to select
         .media(["https://assets.rapidata.ai/bad_ai_generated_image.png", 
         "https://assets.rapidata.ai/good_ai_generated_image.png"]) # We specify the two images that will be compared
         .truth("https://assets.rapidata.ai/good_ai_generated_image.png") # We specify the image that is the correct choice
         .build()) # We build the Rapid to get the instance

validation_set_builder.add_rapid(rapid) # We can add as many rapids to the validation set as we want. Each time, a random one will be chosen to be shown to the labeler.
```

3. After we have added all the tasks to the validation set, we can create the validation set to use it in our orders:

```py
validataion_set = validation_set_builder.create()
```

### Usage

1. Let's find the validation set that we can add it to the order. It can be reused for multiple orders:

```py
validation_set = rapi.find_validation_sets("Example Compare Validataion Set")[0] 
```

2. Now we can create a new order and add the validation set to it. It will automatically be shown infront of the datapoints we want to label. Ideally the criteria is the same or very closely related to the one in the validation set:

```py
order = (rapi.create_compare_order("Example Compare Order") # We create a new order
        .criteria("Which of the AI generated images looks more realistic?") # We specify the criteria for the labeler how to decide which image to select
        .media([["https://assets.rapidata.ai/dalle-3_human.jpg", 
        "https://assets.rapidata.ai/flux_human.jpg"]]) # We specify the images that will be labeled. (list of lists - inner list will be the matched pairs)
        .validation_set(validation_set.id) # We specify the validation set that will be used to validate the order
        .run()) # We run the order
```

3. Now we wait for the order to complete and look at the results:

```py
order.display_progress_bar()
results = order.get_results()
```
