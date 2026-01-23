<div style="display: flex; justify-content: space-between; align-items: center;">
  <h1 style="margin: 0;">Rapidata developer documentation</h1>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.10+-blue.svg?style=flat-square&padding=0" alt="Python 3.10+">
  </a>
</div>

Set up your environment and make your first API request in minutes.

<div class="grid cards" markdown>

-   __Quick Start__

    ---

    Get real humans to label your data in minutes.

    ```python
    pip install -U rapidata
    ```

    === "Image"
        ```python
        from rapidata import RapidataClient

        client = RapidataClient()

        # Get the global audience
        audience = client.audience.get_audience_by_id("global")

        # Create job definition
        job_definition = client.job.create_compare_job_definition(
            name="Example Image Comparison",
            instruction="Which image matches the description better?",
            contexts=["A small blue book sitting on a large red book."],
            datapoints=[["https://assets.rapidata.ai/midjourney-5.2_37_3.jpg",
                        "https://assets.rapidata.ai/flux-1-pro_37_0.jpg"]],
        )

        # Assign to audience
        job = audience.assign_job(job_definition)
        
        # View the job in the browser
        job.view()
        job.display_progress_bar()
        results = job.get_results()
        print(results)
        ```

    === "Video"
        ```python
        from rapidata import RapidataClient

        client = RapidataClient()

        # Get the global audience
        audience = client.audience.get_audience_by_id("global")

        # Create job definition
        job_definition = client.job.create_compare_job_definition(
            name="Example Video Comparison",
            instruction="Which video fits the description better?",
            contexts=["A group of elephants painting vibrant murals on a city wall."],
            datapoints=[["https://assets.rapidata.ai/0074_sora_1.mp4",
                        "https://assets.rapidata.ai/0074_hunyuan_1724.mp4"]],
        )

        # Assign to audience
        job = audience.assign_job(job_definition)
        
        # View the job in the browser
        job.view()
        job.display_progress_bar()
        results = job.get_results()
        print(results)
        ```

    === "Audio"
        ```python
        from rapidata import RapidataClient, LanguageFilter

        client = RapidataClient()

        # Get the global audience
        audience = client.audience.get_audience_by_id("global")

        # Create job definition
        job_definition = client.job.create_compare_job_definition(
            name="Example Audio Comparison",
            instruction="Which audio clip sounds more natural?",
            datapoints=[["https://assets.rapidata.ai/Chat_gpt.mp3",
                        "https://assets.rapidata.ai/ElevenLabs.mp3"]],
        )

        # Assign to audience
        job = audience.assign_job(job_definition)
        
        # View the job in the browser
        job.view()
        job.display_progress_bar()
        results = job.get_results()
        print(results)
        ```

    === "Text"
        ```python
        from rapidata import RapidataClient, LanguageFilter

        client = RapidataClient()

        # Get the global audience
        audience = client.audience.get_audience_by_id("global")

        # Create job definition
        job_definition = client.job.create_compare_job_definition(
            name="Example Text Comparison",
            instruction="Which sentence is grammatically more correct?",
            datapoints=[["The children were amazed by the magician's tricks",
                        "The children were amusing by the magician's tricks."]],
            data_type="text",
        )

        # Assign to audience
        job = audience.assign_job(job_definition)
        
        # View the job in the browser
        job.view()
        job.display_progress_bar()
        results = job.get_results()
        print(results)
        ```

    > **Note**: The global audience gets you started quickly. For higher quality results, use a [custom audience](audiences.md) with qualification examples.

    [:octicons-arrow-right-24: Quickstart Guide](quickstart.md)

</div>
