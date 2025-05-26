from rapidata import RapidataClient

IMAGE_URLS = ['https://assets.rapidata.ai/dalle-3_244_0.jpg',
        'https://assets.rapidata.ai/dalle-3_30_1.jpg',
        'https://assets.rapidata.ai/dalle-3_268_2.jpg',
        'https://assets.rapidata.ai/dalle-3_26_2.jpg']

PROMPTS = ['The black camera was next to the white tripod.',
        'Four cars on the street.',
        'Car is bigger than the airplane.',
        'One cat and two dogs sitting on the grass.']

PROMPTS_WITH_NO_MISTAKES = [prompt + " [No_mistakes]" for prompt in PROMPTS] # selection is split based on spaces
    
if __name__ == "__main__":
    rapi = RapidataClient()
    order = rapi.order.create_select_words_order(
        name="Detect Mistakes in Image-Text Alignment",
        instruction="The image is based on the text below. Select mistakes, i.e., words that are not aligned with the image.",
        datapoints=IMAGE_URLS,
        responses_per_datapoint=15,
        sentences=PROMPTS_WITH_NO_MISTAKES,
        filters=[
            rapi.order.filters.language(["en"]),
        ],
    ).run()
    order.display_progress_bar()
    result = order.get_results()
    print(result)

