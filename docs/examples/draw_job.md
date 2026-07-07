# Draw Job Example

To learn about the basics of creating a job, please refer to the [quickstart guide](../quickstart.md).

In a draw job, labelers draw lines on a datapoint to color in the regions that match your instruction. This is a powerful way to collect localization data — for example, training data that teaches image editing models where to apply their edits.

Like any other job, a draw job can be assigned to any audience — a ready-to-go curated one, or a custom audience you train with qualification examples.

=== "Simple"

    The simple version runs straight away on a **curated** audience — a pre-existing pool of labelers, ready to work immediately — so the job starts collecting responses right away. Here we ask people to color in specific objects in AI-generated images.

    ```python
    from rapidata import RapidataClient

    IMAGE_URLS = [
        "https://assets.rapidata.ai/midjourney-5.2_37_3.jpg",
        "https://assets.rapidata.ai/flux-1-pro_37_0.jpg",
        "https://assets.rapidata.ai/frames-23-1-25_37_4.png",
        "https://assets.rapidata.ai/aurora-20-1-25_37_3.png",
    ]

    client = RapidataClient()

    audience = client.audience.get_audience_by_id("global") # (1)!

    job_definition = client.job.create_draw_job_definition(
        name="Blue Books Example",
        instruction="Color in all the blue books", # (2)!
        datapoints=IMAGE_URLS,
        responses_per_datapoint=35,
    )

    job = audience.assign_job(job_definition)
    job.view()
    job.display_progress_bar()
    results = job.get_results()
    print(results)
    ```

    1. The global audience (id `global`) already has labelers ready to work, so the job starts collecting responses immediately. You can assign a draw job to any audience — browse them in the [Rapidata Dashboard](https://app.rapidata.ai/audiences).
    2. The instruction tells labelers what to color in. Each response is the set of lines they drew on that datapoint.

=== "Advanced"

    The advanced version builds a **custom** audience and trains labelers with qualification examples before running the job. Each example carries the bounding box(es) covering the region a correct labeler should color in — their drawn lines must fall within them to qualify — which raises label quality. In this version, we train an audience to color in visual artifacts in AI-generated images.

    !!! warning "This takes significantly longer"
        Unlike the Simple path, this first builds and trains an entirely new audience before the job can start collecting responses — expect it to take considerably longer to return results.

    ```python
    from rapidata import RapidataClient, Box

    IMAGE_URLS = [
        "https://assets.rapidata.ai/eac11c3e-ad57-402b-90ed-23378d2ff869.jpg",
        "https://assets.rapidata.ai/04e7e3c6-5554-47ca-bdb2-950e48ac3e6c.jpg",
        "https://assets.rapidata.ai/91d9913c-b399-47f8-ad19-767798cc951c.jpg",
    ]

    # Qualification examples — each pairs an image with the bounding box(es)
    # covering the region a correct labeler should color in. Coordinates are
    # image ratios (0.0–1.0).
    EXAMPLES = [
        ("https://assets.rapidata.ai/544b1210-1e91-4351-a97c-fe8263b319b4.webp",
         [Box(x_min=0.44, y_min=0.42, x_max=0.58, y_max=0.63)]),
        ("https://assets.rapidata.ai/f1e11611-7c5b-4186-8ddf-51e06c0859ff.webp",
         [Box(x_min=0.07, y_min=0.37, x_max=0.39, y_max=0.71)]),
        ("https://assets.rapidata.ai/ad816f8f-f7a9-4c90-90dd-9c10bc556856.webp",
         [Box(x_min=0.04, y_min=0.10, x_max=0.31, y_max=0.28)]),
        ("https://assets.rapidata.ai/a076ae24-4d5c-415d-9d41-6afbe2fbfcde.webp",
         [Box(x_min=0.25, y_min=0.40, x_max=0.70, y_max=0.96)]),
        ("https://assets.rapidata.ai/38753cb4-4b77-4fb7-b601-8a5bc3d166d7.webp",
         [Box(x_min=0.41, y_min=0.09, x_max=0.87, y_max=0.45)]),
        ("https://assets.rapidata.ai/50109592-b521-4dcb-a00f-453f6c026a52.webp",
         [Box(x_min=0.25, y_min=0.03, x_max=0.71, y_max=0.48)]),
        ("https://assets.rapidata.ai/a5a954d0-91e8-4b4e-bec6-2bb739444be8.webp",
         [Box(x_min=0.57, y_min=0.40, x_max=0.96, y_max=0.89)]),
    ]

    client = RapidataClient()

    audience = client.audience.create_audience(name="Artifact Drawing Audience") # (1)!
    for datapoint, truths in EXAMPLES:
        audience.add_draw_example(
            instruction="Color in the visual glitches or errors in the image.",
            datapoint=datapoint,
            truths=truths,
        )

    job_definition = client.job.create_draw_job_definition(
        name="Artifact Drawing Example",
        instruction="Color in the visual glitches or errors in the image.",
        datapoints=IMAGE_URLS,
        responses_per_datapoint=35,
    )

    job = audience.assign_job(job_definition)
    job.view()
    job.display_progress_bar()
    results = job.get_results()
    print(results)
    ```

    1. Creates a new, empty audience. The `add_draw_example` calls train and filter the labelers who join it.

    !!! note
        Review every qualification example and its truth regions carefully, and add more than the few shown here for production workloads — see [Custom Audiences](../audiences.md) for the full guide.
