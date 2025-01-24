'''
SelectWords order with validation set
'''

from rapidata import RapidataClient

def create_validation_set(rapi: RapidataClient):
    validation_set = rapi.validation.create_select_words_set(
        name="Example SelectWords Validation Set",
        instruction="Select the words you hear in the audio",
        datapoints=["https://assets.rapidata.ai/where_did_you__today.mp3"],
        sentences=["Where did you go today?"],
        truths=[[0, 1, 2, 4]],
        required_completeness=1,
        required_precision=1,
    )
    return validation_set

def new_select_words_order(rapi: RapidataClient, validation_set_id: str):
    order = rapi.order.create_select_words_order(
        name="Example SelectWords Order",
        instruction="Select the words you hear in the audio",
        datapoints=["https://assets.rapidata.ai/openai_tts_demo.mp3"],
        sentences=["Hello, welcome to OpenAI's Text-to-Speech demo!"],
        validation_set_id=validation_set_id,
        responses_per_datapoint=25,
        filters=[
            rapi.order.filters.language(["en"])
        ]
    ).run()
    
    return order

if __name__ == "__main__":
    rapi = RapidataClient()
    validation_set = create_validation_set(rapi) # only call this once
    validation_set = rapi.validation.find_validation_sets(name="Example SelectWords Validation Set")[0]
    order = new_select_words_order(rapi, validation_set.id)
    order.display_progress_bar()
    result = order.get_results()
    print(result)

