# Select Words Job Example

To learn about the basics of creating a job, please refer to the [quickstart guide](../quickstart.md).

In a select words job, labelers are shown a datapoint together with a sentence split up by spaces, and select the words that match your instruction. A big part of image generation is following the prompt accurately — in this example, labelers select the words of the prompt that are not correctly depicted in the image.

Like any other job, a select words job can be assigned to any audience — a ready-to-go curated one, or a custom audience you train with qualification examples.

=== "Simple"

    The simple version runs straight away on a **curated** audience — a pre-existing pool of labelers, ready to work immediately — so the job starts collecting responses right away.

    ```python
    from rapidata import RapidataClient

    IMAGE_URLS = [
        "https://assets.rapidata.ai/dalle-3_244_0.jpg",
        "https://assets.rapidata.ai/dalle-3_30_1.jpg",
        "https://assets.rapidata.ai/dalle-3_268_2.jpg",
        "https://assets.rapidata.ai/dalle-3_26_2.jpg",
    ]

    PROMPTS = [
        "The black camera was next to the white tripod.",
        "Four cars on the street.",
        "Car is bigger than the airplane.",
        "One cat and two dogs sitting on the grass.",
    ]

    PROMPTS_WITH_NO_MISTAKES = [
        prompt + " [No_mistakes]" for prompt in PROMPTS
    ] # (1)!

    client = RapidataClient()

    audience = client.audience.get_audience_by_id("global") # (2)!

    job_definition = client.job.create_select_words_job_definition(
        name="Image-Text Alignment Example",
        instruction="The image is based on the text below. Select mistakes, i.e., words that are not aligned with the image.",
        datapoints=IMAGE_URLS,
        sentences=PROMPTS_WITH_NO_MISTAKES, # (3)!
        responses_per_datapoint=15,
    )

    job_definition.preview()

    job = audience.assign_job(job_definition)
    job.display_progress_bar()
    results = job.get_results()
    print(results)
    ```

    1. The selection is split based on spaces. Appending a `[No_mistakes]` token gives labelers an explicit way to say the prompt is depicted correctly.
    2. The global audience (id `global`) already has labelers ready to work, so the job starts collecting responses immediately. You can assign a select words job to any audience — browse them in the [Rapidata Dashboard](https://app.rapidata.ai/audiences).
    3. Each sentence is matched to the datapoint at the same list index, so the lists must have the same length.

=== "Advanced"

    The advanced version builds a **custom** audience and trains labelers with qualification examples before running the job. Each example carries the indices of the words a correct labeler should select; only labelers who select them join the audience, which raises label quality.

    !!! warning "This takes significantly longer"
        Unlike the Simple path, this first builds and trains an entirely new audience before the job can start collecting responses — expect it to take considerably longer to return results.

    ```python
    from rapidata import RapidataClient

    IMAGE_URLS = [
        "https://assets.rapidata.ai/dalle-3_244_0.jpg",
        "https://assets.rapidata.ai/dalle-3_30_1.jpg",
        "https://assets.rapidata.ai/dalle-3_268_2.jpg",
        "https://assets.rapidata.ai/dalle-3_26_2.jpg",
    ]

    PROMPTS = [
        "The black camera was next to the white tripod.",
        "Four cars on the street.",
        "Car is bigger than the airplane.",
        "One cat and two dogs sitting on the grass.",
    ]

    PROMPTS_WITH_NO_MISTAKES = [
        prompt + " [No_mistakes]" for prompt in PROMPTS
    ]

    # Each example pairs an image with the sentence shown to the labeler and
    # the indices of the words a correct labeler should select (0-based, split
    # by spaces). The image is generated from a correct prompt; the sentence
    # then plants a single mismatching word the labeler must catch. For the two
    # correctly-depicted images the truth is the trailing [No_mistakes] token.
    EXAMPLES = [
        ("https://assets.rapidata.ai/22f0c7c5-d085-4360-acce-f42ecf0b8804.png",
         "a white cat lying on a sandy beach [No_mistakes]",  # depicts a black cat
         [1]),
        ("https://assets.rapidata.ai/f4709f2f-40a1-40e3-a338-7acff5495c28.png",
         "a green apple resting on a wooden kitchen table [No_mistakes]",  # depicts a red apple
         [1]),
        ("https://assets.rapidata.ai/8406992c-aea6-41d1-8736-8038bf3621d9.png",
         "five yellow balloons floating above a birthday cake [No_mistakes]",  # depicts three balloons
         [0]),
        ("https://assets.rapidata.ai/cffc8a44-5155-43bf-807c-5c358edb9481.png",
         "a square mirror hanging on a bedroom wall [No_mistakes]",  # depicts a round mirror
         [1]),
        ("https://assets.rapidata.ai/20afca97-9736-4311-9ad8-efe74d3a6886.png",
         "a metal chair standing in an empty white room [No_mistakes]",  # depicts a wooden chair
         [1]),
        ("https://assets.rapidata.ai/4618bd82-fef3-420e-a417-9f72dd8d08b3.png",
         "a small motorcycle parked next to a tall building [No_mistakes]",  # correctly depicted
         [9]),
        ("https://assets.rapidata.ai/26ab1e0b-19b5-4f2e-a4b6-d5e319931064.png",
         "a dog sitting under a large oak tree [No_mistakes]",  # correctly depicted
         [8]),
    ]

    client = RapidataClient()

    audience = client.audience.create_audience(name="Image-Text Alignment Audience") # (1)!
    for datapoint, sentence, truths in EXAMPLES:
        audience.add_select_words_example(
            instruction="The image is based on the text below. Select mistakes, i.e., words that are not aligned with the image.",
            datapoint=datapoint,
            sentence=sentence,
            truths=truths,
        )

    job_definition = client.job.create_select_words_job_definition(
        name="Image-Text Alignment Example",
        instruction="The image is based on the text below. Select mistakes, i.e., words that are not aligned with the image.",
        datapoints=IMAGE_URLS,
        sentences=PROMPTS_WITH_NO_MISTAKES,
        responses_per_datapoint=15,
    )

    job_definition.preview()

    job = audience.assign_job(job_definition)
    job.display_progress_bar()
    results = job.get_results()
    print(results)
    ```

    1. Creates a new, empty audience. The `add_select_words_example` calls train and filter the labelers who join it.

    !!! note
        Review every qualification example and its truth words carefully, and add more than the few shown here for production workloads — see [Custom Audiences](../audiences.md) for the full guide.
