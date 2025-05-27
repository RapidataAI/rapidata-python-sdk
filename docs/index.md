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
