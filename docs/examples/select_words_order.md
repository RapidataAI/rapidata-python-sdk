# Example Select Words Order

To learn about the basics of creating an order, please refer to the [quickstart guide](../quickstart.md).

A big part of image generation is following the prompt accurately. Rapidata makes it easy to get feedback on what parts of the prompt the model is struggling with. In this example, we will create an order where annotators are asked to select the words that are not correctly depicted in the image.

```python
--8<-- "examples/basic_select_words_order.py"
```

To preview the order and see what the annotators see, you can run the following code:

```python
order.preview()
```

To open the order in the browser, you can run the following code:

```python
order.view()
```
