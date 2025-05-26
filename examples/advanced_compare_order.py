from rapidata import RapidataClient

# ===== TASK CONFIGURATION =====
INSTRUCTION: str = "Which image follows the prompt more accurately?"

# ===== VALIDATION DATA =====
# This validation set helps ensure quality responses by providing known examples
VALIDATION_PROMPTS: list[str] = [
    "2 cats sitting on both sides of a dog",
    "girl wearing a futuristic costume without her face being covered by a mask",
    "a train traveling fast through a forest",
]

VALIDATION_IMAGE_PAIRS: list[list[str]] = [
    ["https://assets.rapidata.ai/2_cats_1_dog.jpg", "https://assets.rapidata.ai/2_dogs_1_cat.jpg"],
    ["https://assets.rapidata.ai/girl_without_mask.jpg", "https://assets.rapidata.ai/girl_with_mask.jpg"],
    ["https://assets.rapidata.ai/train_normal.jpg", "https://assets.rapidata.ai/train_surfing.jpg"],
]

VALIDATION_TRUTHS: list[str] = [
    "https://assets.rapidata.ai/2_cats_1_dog.jpg",     # First image: 2 cats, 1 dog
    "https://assets.rapidata.ai/girl_without_mask.jpg", # First image: girl without mask
    "https://assets.rapidata.ai/train_normal.jpg",     # First image: normal train through forest
]

# ===== REAL TASK DATA =====
# Prompts to be matched with images
PROMPTS: list[str] = [
    "A sign that says 'Diffusion'.",
    "A yellow flower sticking out of a green pot.",
    "hyperrealism render of a surreal alien humanoid.",
    "psychedelic duck",
    "A small blue book sitting on a large red book."
]

# Image pairs to be matched with prompts (flux vs midjourney versions)
IMAGE_PAIRS: list[list[str]] = [
    ["https://assets.rapidata.ai/flux_sign_diffusion.jpg", "https://assets.rapidata.ai/mj_sign_diffusion.jpg"],
    ["https://assets.rapidata.ai/flux_flower.jpg", "https://assets.rapidata.ai/mj_flower.jpg"],
    ["https://assets.rapidata.ai/flux_alien.jpg", "https://assets.rapidata.ai/mj_alien.jpg"],
    ["https://assets.rapidata.ai/flux_duck.jpg", "https://assets.rapidata.ai/mj_duck.jpg"],
    ["https://assets.rapidata.ai/flux_book.jpg", "https://assets.rapidata.ai/mj_book.jpg"]
]


def create_validation_set(client: RapidataClient) -> str:
    """
    Create a validation set to ensure quality responses.

    Args:
        client: The RapidataClient instance

    Returns:
        The validation set ID
    """
    validation_set = client.validation.create_compare_set(
        name="Example Image Prompt Alignment Validation Set",
        instruction=INSTRUCTION,
        contexts=VALIDATION_PROMPTS,
        datapoints=VALIDATION_IMAGE_PAIRS,
        truths=VALIDATION_TRUTHS
    )
    return validation_set.id


def main():
    client = RapidataClient()

    validation_set_id = create_validation_set(client)

    order = client.order.create_compare_order(
        name="Example Image Prompt Alignment Order",
        instruction=INSTRUCTION,
        datapoints=IMAGE_PAIRS,
        contexts=PROMPTS,
        responses_per_datapoint=25,
        validation_set_id=validation_set_id
    ).run()

    order.display_progress_bar()
    
    results = order.get_results()
    print(results)


if __name__ == "__main__":
    main()
