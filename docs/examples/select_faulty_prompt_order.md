# Example Missing Element Select Words Order

This example builds on what was introduced in the [Quickstart](/quickstart/) as well as the [Improve Quality](/improve_order_quality/) guide.

## Order description

A big part of image generation is following the prompt accurately. Rapidata makes it easy to get feedback on what parts of the prompt the model is struggling with. In this example, we will create an order where annotators are asked to select the words that are not correctly depicted in the image.

```python
--8<-- "examples/select_faulty_prompt_order.py"
```

The resulting rapids for the users look like this:

<figure markdown="span">
![SelectWords Example](../media/order-types/select_words_prompt.png){ width="50%" }
</figure>
