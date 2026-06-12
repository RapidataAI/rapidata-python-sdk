# Locate Job Example

To learn about the basics of creating a job, please refer to the [quickstart guide](../quickstart.md).

In a locate job, labelers tap the points in a datapoint that match your instruction. In this example, we ask people to point out visual artifacts in AI-generated images — a common way to find where a generator went wrong.

Like any other job, a locate job can be assigned to any audience — a ready-to-go curated one, or a custom audience you train with qualification examples.

=== "Simple"

    The simple version runs straight away on a **curated** audience — a pre-existing pool of labelers, ready to work immediately — so the job starts collecting responses right away.

    ```python
    from rapidata import RapidataClient

    IMAGE_URLS = [
        "https://assets.rapidata.ai/eac11c3e-ad57-402b-90ed-23378d2ff869.jpg",
        "https://assets.rapidata.ai/04e7e3c6-5554-47ca-bdb2-950e48ac3e6c.jpg",
        "https://assets.rapidata.ai/91d9913c-b399-47f8-ad19-767798cc951c.jpg",
    ]

    client = RapidataClient()

    audience = client.audience.get_audience_by_id("global") # (1)!

    job_definition = client.job.create_locate_job_definition(
        name="Artifact Detection Example",
        instruction="Tap on any visual glitches or errors in the image.", # (2)!
        datapoints=IMAGE_URLS,
        responses_per_datapoint=35,
    )

    job_definition.preview()

    job = audience.assign_job(job_definition)
    job.display_progress_bar()
    results = job.get_results()
    print(results)
    ```

    1. The global audience (id `global`) already has labelers ready to work, so the job starts collecting responses immediately. You can assign a locate job to any audience — browse them in the [Rapidata Dashboard](https://app.rapidata.ai/audiences).
    2. The instruction tells labelers what to locate. Each response is the set of points they tapped on that datapoint.

=== "Advanced"

    The advanced version builds a **custom** audience and trains labelers with qualification examples before running the job. Each example carries the bounding box(es) covering the region a correct labeler should tap; only labelers who tap inside them join the audience, which raises label quality.

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
    # covering the region a correct labeler should tap. Coordinates are image
    # ratios (0.0–1.0);
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

    audience = client.audience.create_audience(name="Artifact Detection Audience") # (1)!
    for datapoint, truths in EXAMPLES:
        audience.add_locate_example(
            instruction="Tap on any visual glitches or errors in the image.",
            datapoint=datapoint,
            truths=truths,
        )

    job_definition = client.job.create_locate_job_definition(
        name="Artifact Detection Example",
        instruction="Tap on any visual glitches or errors in the image.",
        datapoints=IMAGE_URLS,
        responses_per_datapoint=35,
    )

    job_definition.preview()

    job = audience.assign_job(job_definition)
    job.display_progress_bar()
    results = job.get_results()
    print(results)
    ```

    1. Creates a new, empty audience. The `add_locate_example` calls train and filter the labelers who join it.

    !!! note
        Review every qualification example and its truth regions carefully, and add more than the few shown here for production workloads — see [Custom Audiences](../audiences.md) for the full guide.
