# Example Classify Order

To learn about the basics of creating an order, please refer to the [quickstart guide](../quickstart.md).

## Order description

With this order we want to find out what kind of emotions people feel when they are given a certain AI generated image. We have asked Dalle-3 to generate 4 different images that would convey happyness, anger, disgust and sadness. Now we want to find out if the images are actually conveying the emotions we asked for.

```python
--8<-- "examples/classify_order.py"
```

The resulting rapids for the users look like this:

<figure markdown="span">
![Classify Example](../media/order-types/classify_emotions_example.png){ width="50%" }
</figure>
