# Example Free Text Order

To learn about the basics of creating an order, please refer to the [quickstart guide](../quickstart.md).

![Free Text Order Example](../media/order-types/freetext.png){ width="20%" }

=== "Basic"

    Let's assume you want to build a new LLM chatbot and you want to know what people might want to ask the bot. You can create a free-text order to gather the questions people might have.

    The free-text order will take longer to complete than the others, as the response process is slightly more involved from the perspective of the annotator.

    ```python
    --8<-- "examples/basic_free_text_order.py"
    ```

    To preview the order and see what the annotators see, you can run the following code:

    ```python
    order.preview()
    ```

    To open the order in the browser, you can run the following code:

    ```python
    order.view()
    ```

=== "Advanced"

    In the advanced example we will add some filters to the order to make sure only annotators that have their phone set to english are able to answer. Additionally we will set a minimum length of 5 characters for the questions.

    ```python
    --8<-- "examples/advanced_free_text_order.py"
    ```

    To preview the order and see what the annotators see, you can run the following code:

    ```python
    order.preview()
    ```

    To open the order in the browser, you can run the following code:

    ```python
    order.view()
    ```

    
    
