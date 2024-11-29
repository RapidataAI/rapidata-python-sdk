# Example Compare Order

This example builds on what was introduced in the [Quickstart](/rapidata-python-sdk/quickstart/) as well as the [Improve Order Quality](/rapidata-python-sdk/improve_order_quality/) guide.

## Order description

We have two state of the art models, Flux and Midjourney that generate images based on a description aka prompt. We want to find out which of the images more closely aligns with the prompt. 

```python
--8<-- "examples/compare_prompt_image_alignment.py"
```

The resulting rapids for the users look like this:

<figure markdown="span">
![Compare Example](../media/order-types/compare_text_image_alignment.png){ width="50%" }
</figure>
