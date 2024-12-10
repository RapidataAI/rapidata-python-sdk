"""
Compare order with a validation set
"""

from rapidata import RapidataClient

def prepare_validation_urls():
    base_url = "https://assets.rapidata.ai/"
    validation_image_pairs = [ # list of image pairs with the first one that follows the prompt accurately
        [
            "2 cats sitting on both sides of a dog", # prompt
            f"{base_url}2_cats_1_dog.jpg", # image1
            f"{base_url}2_dogs_1_cat.jpg", # image2
        ],
        [
            "girl wearing a futuristic costume without her face being covered by a mask",
            f"{base_url}girl_without_mask.jpg",
            f"{base_url}girl_with_mask.jpg",
        ],
        [
            "a train traveling fast through a forest",
            f"{base_url}train_normal.jpg",
            f"{base_url}train_surfing.jpg",
        ],
    ]
    return validation_image_pairs

def prepare_order_urls():
    base_url = "https://assets.rapidata.ai/"
    
    prompts = ["A sign that says 'Diffusion'.",
               "A yellow flower sticking out of a green pot.",
               "hyperrealism render of a surreal alien humanoid.",
               "psychedelic duck",
               "A small blue book sitting on a large red book."] # list of prompts to be matched with images
    
    images = ["sign_diffusion.jpg",
              "flower.jpg",
              "alien.jpg",
              "duck.jpg",
              "book.jpg"] # list of images to be matched with prompts
    
    image_urls = [[f"{base_url}flux_{image}", f"{base_url}mj_{image}"] for image in images] # list of image pairs to be matched with prompts

    return prompts, image_urls

def create_validation_set(rapi: RapidataClient):
    validation_image_pairs = prepare_validation_urls()
    
    return rapi.validation.create_compare_set(
        name="Example Image Prompt Alignment Validation Set",
        criteria="Which image follows the prompt more accurately?",
        prompts=[datapoint[0] for datapoint in validation_image_pairs],
        datapoints=[[datapoint[1], datapoint[2]] for datapoint in validation_image_pairs],
        truth=[datapoint[1] for datapoint in validation_image_pairs]
    )


def get_prompt_image_alignment(rapi: RapidataClient, validatation_set_id: str):
    prompts, image_urls = prepare_order_urls()

    order = rapi.order.create_compare_order(
        name="Example Image Prompt Alignment Order",
        criteria="Which image follows the prompt more accurately?",
        datapoints=image_urls,
        responses_per_datapoint=25,
        prompts=prompts,
        validation_set_id=validatation_set_id
    ).run()

    return order


if __name__ == "__main__":
    rapi = RapidataClient()
    validation_set = create_validation_set(rapi) # only call this once
    validation_set = rapi.validation.find_validation_sets(name="Example Image Prompt Alignment Validation Set")[0]
    order = get_prompt_image_alignment(rapi, validation_set.id)
    order.display_progress_bar()
    results = order.get_results()
    print(results)
