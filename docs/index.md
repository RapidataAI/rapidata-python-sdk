# Rapidata developer documentation

## Developer Quickstart
Set up your environment and make your first API request in minutes.

<div class="grid cards" markdown>

-   __Developer Quickstart__

    ---

    The user is given mutliple answer options for the given question and image.

    *Estimated time: 5 minutes*

    ```python
    pip install -U rapidata
    ```

    ```python
    from rapidata import RapidataClient

    rapi = RapidataClient()

    order = (rapi.create_classify_order("Example Classification Order")
            .question("What is shown in the image?")
            .options(["Fish", "Cat", "Wallaby", "Airplane"])
            .media(["https://assets.rapidata.ai/wallaby.jpg"])
            .create())

    order.display_progress_bar()

    results = order.get_results()
    print(results)
    ```
    
    [:octicons-arrow-right-24: Let's go](quickstart.md)

</div>

<div class="grid cards" markdown>

-   __Classify Order__

    ---

    The user is given mutliple answer options for the given question and image.

    <figure markdown="span">
    ![Classify Example](./media/order-types/classify_emotions_example.png){ width="60%" }
    </figure>

    [:octicons-arrow-right-24: Let's go](./examples/classify_order.md)

-   __Compare Order__

    ---

    The user chooses between two images/videos/texts based on a criteria.

    <figure markdown="span">
    ![Compare Example](./media/order-types/compare_text_image_alignment.png){ width="60%" }
    </figure>

    [:octicons-arrow-right-24: Let's go](./examples/compare_order.md)

-   __Free Text Order__

    ---

    The user has a keyboard pop up to freely answer anything.

    <figure markdown="span">
    ![Freetext Example](./media/order-types/freetext_question_to_ai.png){ width="60%" }
    </figure>

    [:octicons-arrow-right-24: Let's go](./examples/free_text_order.md)

-   __SelectWords Order__

    ---

    Have the users click on words in a text depending on a condition.

    <figure markdown="span">
    ![SelectWords Example](./media/order-types/select_words_tts_example.png){ width="60%" }
    </figure>

    [:octicons-arrow-right-24: Let's go](./examples/select_words_order.md)

</div>

<div class="grid cards" markdown>

-   __Preference Data for RLHF__

    ---

    Longer, more detailed blog post on how to use a compare-style setup to collect human preference data, e.g. for Reinforcement Learning from Human Feedback (RLHF).

    <figure markdown="span">
    ![Preference Example](./media/order-types/glass_on_dog_1.png){ width="80%" }
    </figure>

    [:octicons-arrow-right-24: Let's go](https://rapidata.ai/blog/preference-dataset-demo)

</div>
