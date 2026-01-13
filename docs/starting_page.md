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

    Create qualified audiences and have them label your data.

    ```python
    pip install -U rapidata
    ```

    === "Image"
        ```python
        from rapidata import RapidataClient

        client = RapidataClient()

        # Create audience with qualification example
        audience = client.audience.create_audience(name="Image Comparison Audience")
        audience.add_compare_example(
            instruction="Which image matches the description better?",
            datapoint=[
                "https://assets.rapidata.ai/flux_sign_diffusion.jpg",
                "https://assets.rapidata.ai/mj_sign_diffusion.jpg"
            ],
            truth="https://assets.rapidata.ai/flux_sign_diffusion.jpg",
            context="A sign that says 'Diffusion'."
        )

        # Create job definition
        job_definition = client.job.create_compare_job_definition(
            name="Example Image Comparison",
            instruction="Which image matches the description better?",
            contexts=["A small blue book sitting on a large red book."],
            datapoints=[["https://assets.rapidata.ai/midjourney-5.2_37_3.jpg",
                        "https://assets.rapidata.ai/flux-1-pro_37_0.jpg"]],
        )

        # Preview, then assign to audience
        job_definition.preview()
        job = audience.assign_job_to_audience(job_definition)
        job.display_progress_bar()
        results = job.get_results()
        print(results)
        ```

    === "Video"
        ```python
        from rapidata import RapidataClient

        client = RapidataClient()

        # Create audience with qualification example
        audience = client.audience.create_audience(name="Video Comparison Audience")
        audience.add_compare_example(
            instruction="Which video fits the description better?",
            datapoint=[
                "https://assets.rapidata.ai/0074_sora_1.mp4",
                "https://assets.rapidata.ai/0074_hunyuan_1724.mp4"
            ],
            truth="https://assets.rapidata.ai/0074_sora_1.mp4",
            context="A group of elephants painting murals."
        )

        # Create job definition
        job_definition = client.job.create_compare_job_definition(
            name="Example Video Comparison",
            instruction="Which video fits the description better?",
            contexts=["A group of elephants painting vibrant murals on a city wall."],
            datapoints=[["https://assets.rapidata.ai/0074_sora_1.mp4",
                        "https://assets.rapidata.ai/0074_hunyuan_1724.mp4"]],
        )

        # Preview, then assign to audience
        job_definition.preview()
        job = audience.assign_job_to_audience(job_definition)
        job.display_progress_bar()
        results = job.get_results()
        print(results)
        ```

    === "Audio"
        ```python
        from rapidata import RapidataClient, LanguageFilter

        client = RapidataClient()

        # Create audience with qualification example
        audience = client.audience.create_audience(
            name="Audio Comparison Audience",
            filters=[LanguageFilter(["en"])]
        )
        audience.add_compare_example(
            instruction="Which audio clip sounds more natural?",
            datapoint=[
                "https://assets.rapidata.ai/Chat_gpt.mp3",
                "https://assets.rapidata.ai/ElevenLabs.mp3"
            ],
            truth="https://assets.rapidata.ai/ElevenLabs.mp3"
        )

        # Create job definition
        job_definition = client.job.create_compare_job_definition(
            name="Example Audio Comparison",
            instruction="Which audio clip sounds more natural?",
            datapoints=[["https://assets.rapidata.ai/Chat_gpt.mp3",
                        "https://assets.rapidata.ai/ElevenLabs.mp3"]],
        )

        # Preview, then assign to audience
        job_definition.preview()
        job = audience.assign_job_to_audience(job_definition)
        job.display_progress_bar()
        results = job.get_results()
        print(results)
        ```

    === "Text"
        ```python
        from rapidata import RapidataClient, LanguageFilter

        client = RapidataClient()

        # Create audience with qualification example
        audience = client.audience.create_audience(
            name="Text Comparison Audience",
            filters=[LanguageFilter(["en"])]
        )
        audience.add_compare_example(
            instruction="Which sentence is grammatically more correct?",
            datapoint=[
                "The children were amazed by the magician's tricks",
                "The children were amusing by the magician's tricks."
            ],
            truth="The children were amazed by the magician's tricks",
            data_type="text"
        )

        # Create job definition
        job_definition = client.job.create_compare_job_definition(
            name="Example Text Comparison",
            instruction="Which sentence is grammatically more correct?",
            datapoints=[["The children were amazed by the magician's tricks",
                        "The children were amusing by the magician's tricks."]],
            data_type="text",
        )

        # Preview, then assign to audience
        job_definition.preview()
        job = audience.assign_job_to_audience(job_definition)
        job.display_progress_bar()
        results = job.get_results()
        print(results)
        ```
    [:octicons-arrow-right-24: Let's go](quickstart.md)

</div>
