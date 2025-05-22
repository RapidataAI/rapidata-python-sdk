<div style="display: flex; justify-content: space-between; align-items: center;">
  <h1 style="margin: 0;">Rapidata developer documentation</h1>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.10+-blue.svg?style=flat-square&padding=0" alt="Python 3.10+">
  </a>
</div>

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

    === "Image"
        ```python
        from rapidata import RapidataClient

        rapi = RapidataClient()

        order = rapi.order.create_compare_order(
            name="Example Image Comparison",
            instruction="Which image matches the description better?",
            contexts=["A small blue book sitting on a large red book."],
            datapoints=[["https://assets.rapidata.ai/midjourney-5.2_37_3.jpg", 
                        "https://assets.rapidata.ai/flux-1-pro_37_0.jpg"]],
        ).run()

        order.display_progress_bar()

        results = order.get_results()
        print(results)
        ```

    === "Video"
        ```python
        from rapidata import RapidataClient

        rapi = RapidataClient()

        order = rapi.order.create_compare_order(
            name="Example Video Comparison",
            instruction="Which video fits the description better?",
            contexts=["A group of elephants painting vibrant murals on a city wall during a lively street festival."],
            datapoints=[["https://assets.rapidata.ai/0074_sora_1.mp4", 
                        "https://assets.rapidata.ai/0074_hunyuan_1724.mp4"]],
        ).run()

        order.display_progress_bar()

        results = order.get_results()
        print(results)
        ```

    === "Audio"
        ```python
        from rapidata import RapidataClient, LanguageFilter

        rapi = RapidataClient()

        order = rapi.order.create_compare_order(
            name="Example Audio Comparison",
            instruction="Which audio clip sounds more natural?",
            datapoints=[["https://assets.rapidata.ai/Chat_gpt.mp3", 
                        "https://assets.rapidata.ai/ElevenLabs.mp3"]],
            filters=[LanguageFilter(["en"])]
        ).run()

        order.display_progress_bar()

        results = order.get_results()
        print(results)
        ```
    
    === "Text"
        ```python
        from rapidata import RapidataClient, LanguageFilter

        rapi = RapidataClient()

        order = rapi.order.create_compare_order(
            name="Example Text Comparison",
            instruction="Which sentence is grammatically more correct?",
            datapoints=[["The children were amazed by the magician’s tricks", 
                        "The children were amusing by the magician’s tricks."]],
            data_type="text",
            filters=[LanguageFilter(["en"])]
        ).run()

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
    ![SelectWords Example](./media/order-types/select_words_prompt.png){ width="60%" }
    </figure>

    [:octicons-arrow-right-24: Let's go](./examples/select_faulty_prompt_order.md)

</div>

<div class="grid cards" markdown>

-   __Preference Data for RLHF__

    ---

    Longer, more detailed blog post on how to use a compare-style setup to collect human preference data, e.g. for Reinforcement Learning from Human Feedback (RLHF).

    <figure markdown="span">
    ![Preference Example](./media/order-types/glass_on_dog_1.png){ width="80%" }
    </figure>

    [:octicons-arrow-right-24: Let's go](https://www.rapidata.ai/guides/preference-dataset-demo)

</div>
