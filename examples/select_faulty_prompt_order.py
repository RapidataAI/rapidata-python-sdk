'''
SelectWords order with validation set
'''

from rapidata import RapidataClient

def get_urls_and_prompts():
    links = ['https://assets.rapidata.ai/dalle-3_244_0.jpg',
            'https://assets.rapidata.ai/dalle-3_30_1.jpg',
            'https://assets.rapidata.ai/dalle-3_268_2.jpg',
            'https://assets.rapidata.ai/dalle-3_26_2.jpg']
    
    prompts = ['The black camera was next to the white tripod.',
            'Four cars on the street.',
            'Car is bigger than the airplane.',
            'One cat and two dogs sitting on the grass.']
    
    return links, prompts

def new_select_words_order(rapi: RapidataClient):
    links, prompts = get_urls_and_prompts()
    
    prompts_with_no_mistakes = [prompt + " [No_mistakes]" for prompt in prompts] # selection is split based on spaces

    order = rapi.order.create_select_words_order(
        name="Detect Mistakes in Image-Text Alignment",
        instruction="The image is based on the text below. Select mistakes, i.e., words that are not aligned with the image.",
        datapoints=links,
        responses_per_datapoint=15,
        sentences=prompts_with_no_mistakes,
        filters=[
            rapi.order.filters.language(["en"]),
        ],
        validation_set_id="6761a86eef7af86285630ea8" # in this example, the validation set has already been created
    ).run()
    
    return order

if __name__ == "__main__":
    rapi = RapidataClient()
    order = new_select_words_order(rapi)
    order.display_progress_bar()
    result = order.get_results()
    print(result)

