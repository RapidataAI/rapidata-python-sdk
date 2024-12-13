# Improve Response Quality

This guide builds on the [Quickstart](/quickstart/) and focuses on improving the quality of responses received for your orders. By creating a **Validation Set**, you can provide clear guidance to labelers, helping them better understand your expectations. While using a validation set is optional, it significantly enhances response accuracy and consistency, especially for more complex or unintuitive tasks.

### Why Use a Validation Set?

A validation set is a collection of tasks with known answers. It provides labelers with examples of how you want your data annotated, offering immediate feedback to align their work with your requirements.

### How Does it Work?

The validation task has a known truth and will be shown in front of the actual labeling task. Think of it as an interview question before the work starts. The labelers are only allowed to proceed to the actual task if they correctly solve one validation task.

## Example Validation Set

Let’s walk through how to create and use a validation set using the **Compare Order** as an example. The principles apply to any order type and the created validation set can be reused indefinitely.

Here’s what labelers will see during validation for this example:

![Compare Example](./media/order-types/good_bad_ai_image.png){ width="40%" }

### Creating a Validation Set
As always, we start by creating a [`RapidataClient`](reference/rapidata/rapidata_client/rapidata_client.md#rapidata.rapidata_client.rapidata_client.RapidataClient):

```py
from rapidata import RapidataClient

rapi = RapidataClient()
```

All the validation-related operations are performed using `rapi.validation`. Here we create a compare validation set to be used in any future orders:

The creation is structured in the same way as the order creation, except here we have to supply the correct answers as "truth" for each task.

```py
validation_set = rapi.validation.create_compare_set(
     name="Example Compare Validation Set",
     instruction="Which of the AI generated images looks more realistic?",
     datapoints=[["https://assets.rapidata.ai/bad_ai_generated_image.png", 
         "https://assets.rapidata.ai/good_ai_generated_image.png"]], 
     truths=["https://assets.rapidata.ai/good_ai_generated_image.png"] 
)
```

The parameters are as follows:

- `name`: The name of the validation set. This is used to identify the validation set and to find it again later.
- `criteria`: The criteria for the comparison. This is the question that the labeler will answer.
- `datapoints`: The datapoints, each containing 2 images to compare.
- `truths`: The truth, which image is the correct answer.

The truths must be the same length as the datapoints and contain the correct answer for each datapoint.

### Usage

1. We can now use the validation set in any order we create. We first need to find the validation set we created:

```py
# find the validation set by name
validation_set = rapi.validation.find_validation_sets("Example Compare Validation Set")[0] 

# or by id
validation_set = rapi.validation.get_validation_set_by_id("validation_set_id")
```

2. Now we can create a new order and add the validation set to it. It will automatically be shown in front of the datapoints we want to label. Ideally the criteria is the same or very closely related to the one in the validation set:

```py
order = rapi.order.create_compare_order(
     name="Example Compare Validation Set",
     instruction="Which of the AI generated images looks more realistic?", 
     datapoints=[["https://assets.rapidata.ai/dalle-3_human.jpg", 
        "https://assets.rapidata.ai/flux_human.jpg"]],
     validation_set_id=validation_set.id
).run()
```

If the labeler answers the validation task incorrectly, they will get warned and have to answer it correctly before they can proceed to the actual task.

3. Finally we wait for the order to complete and look at the results:

```py
order.display_progress_bar()
results = order.get_results()
```

The validation results will not be included in the final results, you'll only see the results of the actual tasks you wanted to have labeled. Likewise you'll only be charged credits for the actual tasks and not the validation tasks.
