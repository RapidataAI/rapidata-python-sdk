# Example Ranking Order

To learn about the basics of creating an order, please refer to the [quickstart guide](../quickstart.md).

In this example, we will create an order to rank various images of rabbits. The matchups will be generated automatically, comparing two images at a time. The ranking system is based on an Elo rating system, which updates rankings based on the results of these matchups.

The instruction is designed to focus on the comparison between the two images rather than the overall ranking. For example, instead of asking "Which rabbit looks the coolest?", we ask "Which rabbit looks cooler?" to emphasize the specific matchup.

```python
--8<-- "examples/basic_ranking_order.py"
```

To preview the order and see what the annotators see, you can run the following code:

```python
order.preview()
```

To open the order in the browser, you can run the following code:

```python
order.view()
```
