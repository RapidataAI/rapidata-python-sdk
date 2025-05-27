# Example Compare Order

To learn about the basics of creating an order, please refer to the [quickstart guide](../quickstart.md).

=== "Basic"

    In this example we want to compare two image-to-text models, Flux and Midjourney, that have generated images based on a description, aka prompt. Those images have been saved to a public URL in order to be able to run the example anywhere. When you run this with your own examples, you may use local paths to your images instead of the URLs.

    We now want to find out which of the two images more closely aligns with the prompt - for every prompt.

    ```python
    --8<-- "examples/basic_compare_order.py"
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

    In the advanced example we will first create a validation set to give the annotators a reference how they should rate the images.

    To get a better understanding of validation sets, please refer to the [Improve Quality](/improve_order_quality/) guide.

    ```python
    --8<-- "examples/advanced_compare_order.py"
    ```

    To preview the order and see what the annotators see, you can run the following code:

    ```python
    order.preview()
    ```

    To open the order in the browser, you can run the following code:

    ```python
    order.view()
    ```


