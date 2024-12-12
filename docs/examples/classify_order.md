# Example Classify Order

To learn about the basics of creating an order, please refer to the [quickstart guide](../quickstart.md).

## Order description

With this order we want to find out what kind of emotions certain AI generated image convey. We have asked Dalle-3 to generate 4 different images that would convey happiness, anger, disgust and sadness and saved those images to publically accessible URLs. 

Now we want to find out if the images actually match the emotions we asked for. When you run this with your own examples, you may use simple, local paths to your images instead of the URLs.

```python
--8<-- "examples/classify_order.py"
```

The resulting rapids for the users look like this:

<figure markdown="span">
![Classify Example](../media/order-types/classify_emotions_example.png){ width="50%" }
</figure>
