# Compare Job Example

To learn about the basics of creating a job, please refer to the [quickstart guide](../quickstart.md).

In this example, we compare images from two image generation models (Flux and Midjourney) to determine which more accurately follows the given prompts.

=== "Simple"

    The simple version runs straight away on a **curated** audience — a pre-existing pool of trained labelers — so the job starts collecting responses immediately.

    ```python
    from rapidata import RapidataClient

    PROMPTS = [
        "A sign that says 'Diffusion'.",
        "A yellow flower sticking out of a green pot.",
        "hyperrealism render of a surreal alien humanoid.",
        "psychedelic duck",
        "A small blue book sitting on a large red book."
    ]

    IMAGE_PAIRS = [
        ["https://assets.rapidata.ai/flux_sign_diffusion.jpg", "https://assets.rapidata.ai/mj_sign_diffusion.jpg"],
        ["https://assets.rapidata.ai/flux_flower.jpg", "https://assets.rapidata.ai/mj_flower.jpg"],
        ["https://assets.rapidata.ai/flux_alien.jpg", "https://assets.rapidata.ai/mj_alien.jpg"],
        ["https://assets.rapidata.ai/flux_duck.jpg", "https://assets.rapidata.ai/mj_duck.jpg"],
        ["https://assets.rapidata.ai/flux_book.jpg", "https://assets.rapidata.ai/mj_book.jpg"]
    ]

    client = RapidataClient()

    audience = client.audience.get_audience_by_id("aud_MU1GZYoESyO") # (1)!

    job_definition = client.job.create_compare_job_definition(
        name="Example Image Prompt Alignment Job",
        instruction="Which image follows the prompt more accurately?",
        datapoints=IMAGE_PAIRS,
        responses_per_datapoint=25,
        contexts=PROMPTS
    )

    job = audience.assign_job(job_definition)
    job.view()
    job.display_progress_bar()
    results = job.get_results()
    print(results)
    ```

    1. Looks up the curated **Alignment** audience by id, which already has trained labelers. A freshly created audience has no qualified labelers yet, so a job assigned to it would never collect responses — see the Advanced tab for how to build and train your own. You can browse the curated audiences and copy their ids from the [Rapidata Dashboard](https://app.rapidata.ai/audiences).

=== "Advanced"

    The advanced version builds a **custom** audience and trains labelers with qualification examples before running the job. Only labelers who pick the correct image on the examples join the audience, which raises label quality.

    !!! warning "This takes significantly longer"
        Unlike the Simple path, this first builds and trains an entirely new audience before the job can start collecting responses — expect it to take considerably longer to return results.

    ```python
    from rapidata import RapidataClient

    PROMPTS = [
        "A sign that says 'Diffusion'.",
        "A yellow flower sticking out of a green pot.",
        "hyperrealism render of a surreal alien humanoid.",
        "psychedelic duck",
        "A small blue book sitting on a large red book."
    ]

    IMAGE_PAIRS = [
        ["https://assets.rapidata.ai/flux_sign_diffusion.jpg", "https://assets.rapidata.ai/mj_sign_diffusion.jpg"],
        ["https://assets.rapidata.ai/flux_flower.jpg", "https://assets.rapidata.ai/mj_flower.jpg"],
        ["https://assets.rapidata.ai/flux_alien.jpg", "https://assets.rapidata.ai/mj_alien.jpg"],
        ["https://assets.rapidata.ai/flux_duck.jpg", "https://assets.rapidata.ai/mj_duck.jpg"],
        ["https://assets.rapidata.ai/flux_book.jpg", "https://assets.rapidata.ai/mj_book.jpg"]
    ]

    # Qualification pairs where the first (Flux) image clearly follows the prompt
    # better. The truth must point at the unambiguously better image.
    QUALIFICATION_PAIRS = [
        ["https://assets.rapidata.ai/flux_sign_diffusion.jpg", "https://assets.rapidata.ai/mj_sign_diffusion.jpg"],
        ["https://assets.rapidata.ai/flux_duck.jpg", "https://assets.rapidata.ai/mj_duck.jpg"],
        ["https://assets.rapidata.ai/flux_book.jpg", "https://assets.rapidata.ai/mj_book.jpg"],
        ["https://assets.rapidata.ai/flux_flower.jpg", "https://assets.rapidata.ai/mj_flower.jpg"],
        ["https://assets.rapidata.ai/flux_store_front.jpg", "https://assets.rapidata.ai/mj_store_front.jpg"],
        ["https://assets.rapidata.ai/flux_hand.jpg", "https://assets.rapidata.ai/mj_hand.jpg"],
        ["https://assets.rapidata.ai/flux_traffic_lights.jpg", "https://assets.rapidata.ai/mj_traffic_lights.jpg"],
        ["https://assets.rapidata.ai/flux_plane.jpg", "https://assets.rapidata.ai/mj_plane.jpg"],
    ]
    QUALIFICATION_PROMPTS = [
        "A sign that says 'Diffusion'.",
        "A psychedelic duck with glasses",
        "A small blue book sitting on a large red book.",
        "A yellow flower sticking out of a bright green pot.",
        "A store front with 'hello world' written on it.",
        "A yellow hand on a black stone.",
        "A green, yellow and red traffic light.",
        "A plane flying over a person.",
    ]

    client = RapidataClient()

    audience = client.audience.create_audience(name="Custom Prompt Alignment Audience") # (1)!
    for prompt, datapoint in zip(QUALIFICATION_PROMPTS, QUALIFICATION_PAIRS):
        audience.add_compare_example(
            instruction="Which image follows the prompt more accurately?",
            datapoint=datapoint,
            truth=datapoint[0],
            context=prompt
        )

    job_definition = client.job.create_compare_job_definition(
        name="Example Image Prompt Alignment Job",
        instruction="Which image follows the prompt more accurately?",
        datapoints=IMAGE_PAIRS,
        responses_per_datapoint=25,
        contexts=PROMPTS
    )

    job = audience.assign_job(job_definition)
    job.view()
    job.display_progress_bar()
    results = job.get_results()
    print(results)
    ```

    1. Creates a new, empty audience. The `add_compare_example` calls train and filter the labelers who join it.

    !!! note
        Review every qualification example and its truth carefully, and add more than the few shown here for production workloads — see [Custom Audiences](../audiences.md) for the full guide.
