# Example Free Text Order

This example builds on what was introduced in the [Quickstart](/quickstart/).

## Order description

Let's assume you want to build a new LLM chatbot and you want to know what people might want to ask the bot. You can create a free-text order to gather the questions people might have.

The free-text order will take longer to complete than the others, as the response process is slightly more involved from the perspective of the annotator.

```python
--8<-- "examples/free_text_order.py"
```

The resulting rapids for the users look like this:

<figure markdown="span">
![Freetext Example](../media/order-types/freetext_question_to_ai.png){ width="50%" }
</figure>
