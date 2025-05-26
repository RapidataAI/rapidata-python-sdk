from rapidata import RapidataClient

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

if __name__ == "__main__":
    rapi = RapidataClient()
    order = rapi.order.create_compare_order(
        name="Example Image Prompt Alignment Order",
        instruction="Which image follows the prompt more accurately?",
        datapoints=IMAGE_PAIRS,
        responses_per_datapoint=25,
        contexts=PROMPTS, # prompt is the context for each image pair
    ).run()
    order.display_progress_bar()
    results = order.get_results()
    print(results)
