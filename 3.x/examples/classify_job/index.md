# Classification Job Example

To learn about the basics of creating a job, please refer to the [quickstart guide](../quickstart.md).

In this example, we rate images on a Likert scale to assess how well generated images match their descriptions. The `NoShuffleSetting` keeps the answer options in order, since they represent a scale.

=== "Simple"

    The simple version runs straight away on a **curated** audience — a pre-existing pool of trained labelers — so the job starts collecting responses immediately.

    ```python
    from rapidata import RapidataClient, NoShuffleSetting

    IMAGE_URLS = [
        "https://assets.rapidata.ai/tshirt-4o.png",
        "https://assets.rapidata.ai/tshirt-aurora.jpg",
        "https://assets.rapidata.ai/teamleader-aurora.jpg",
    ]

    CONTEXTS = ["A t-shirt with the text 'Running on caffeine & dreams'"] * len(IMAGE_URLS)

    client = RapidataClient()

    audience = client.audience.get_audience_by_id("aud_mr3NbeWa4Uo") # (1)!

    job_definition = client.job.create_classification_job_definition(
        name="Likert Scale Example",
        instruction="How well does the image match the description?",
        answer_options=["1: Not at all", "2: A little", "3: Moderately", "4: Very well", "5: Perfectly"],
        contexts=CONTEXTS,
        datapoints=IMAGE_URLS,
        responses_per_datapoint=25,
        settings=[NoShuffleSetting()] # (2)!
    )

    job_definition.preview()

    job = audience.assign_job(job_definition)
    job.display_progress_bar()
    results = job.get_results()
    print(results)
    ```

    1. Looks up the curated **Coherence** audience by id, which already has trained labelers. A freshly created audience has no qualified labelers yet, so a job assigned to it would never collect responses — see the Advanced tab for how to build and train your own. You can browse the curated audiences and copy their ids from the [Rapidata Dashboard](https://app.rapidata.ai/audiences).
    2. Keeps the answer options in their specified order. Without this, options are randomized to reduce bias — but for Likert scales you want them ordered.

=== "Advanced"

    The advanced version builds a **custom** audience and trains labelers with qualification examples before running the job. Only labelers who answer the examples correctly join the audience, which raises label quality on nuanced tasks.

    !!! warning "This takes significantly longer"
        Unlike the Simple path, this first builds and trains an entirely new audience before the job can start collecting responses — expect it to take considerably longer to return results.

    ```python
    from rapidata import RapidataClient, NoShuffleSetting

    IMAGE_URLS = [
        "https://assets.rapidata.ai/tshirt-4o.png",
        "https://assets.rapidata.ai/tshirt-aurora.jpg",
        "https://assets.rapidata.ai/teamleader-aurora.jpg",
    ]

    CONTEXTS = ["A t-shirt with the text 'Running on caffeine & dreams'"] * len(IMAGE_URLS)

    ANSWER_OPTIONS = ["1: Not at all", "2: A little", "3: Moderately", "4: Very well", "5: Perfectly"]

    # Qualification examples — each pairs an image with a description and the
    # correct rating. Use only examples whose truth is clear and unambiguous.
    EXAMPLES = [
        ("https://assets.rapidata.ai/tshirt-4o.png", "A t-shirt with the text 'Running on caffeine & dreams'", "5: Perfectly"),
        ("https://assets.rapidata.ai/flux_duck.jpg", "A psychedelic duck with glasses", "5: Perfectly"),
        ("https://assets.rapidata.ai/flux_flower.jpg", "A yellow flower sticking out of a green pot", "5: Perfectly"),
        ("https://assets.rapidata.ai/teamleader-aurora.jpg", "A t-shirt with the text 'Running on caffeine & dreams'", "1: Not at all"),
        ("https://assets.rapidata.ai/flux_book.jpg", "A psychedelic duck with glasses", "1: Not at all"),
        ("https://assets.rapidata.ai/flux_duck.jpg", "A small blue book sitting on a large red book", "1: Not at all"),
    ]

    client = RapidataClient()

    audience = client.audience.create_audience(name="Likert Scale Audience") # (1)!
    for datapoint, context, truth in EXAMPLES:
        audience.add_classification_example(
            instruction="How well does the image match the description?",
            answer_options=ANSWER_OPTIONS,
            datapoint=datapoint,
            truth=[truth],
            context=context,
            settings=[NoShuffleSetting()] # (2)!
        )

    job_definition = client.job.create_classification_job_definition(
        name="Likert Scale Example",
        instruction="How well does the image match the description?",
        answer_options=ANSWER_OPTIONS,
        contexts=CONTEXTS,
        datapoints=IMAGE_URLS,
        responses_per_datapoint=25,
        settings=[NoShuffleSetting()]
    )

    job_definition.preview()

    job = audience.assign_job(job_definition)
    job.display_progress_bar()
    results = job.get_results()
    print(results)
    ```

    1. Creates a new, empty audience. The `add_classification_example` calls below define who qualifies to join it.
    2. Qualify labelers on the same UI they'll see in the job. Since the job uses `NoShuffleSetting`, the examples use it too — see [Custom Audiences](../audiences.md#matching-the-job-ui-with-settings).

    !!! note
        Review every qualification example and its truth carefully, and add more than the few shown here for production workloads — see [Custom Audiences](../audiences.md) for the full guide.
