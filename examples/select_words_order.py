'''
SelectWords order with validation set
'''

from rapidata import RapidataClient

def create_validation_set(rapi: RapidataClient):
    validation_set = (
        rapi.new_validation_set(
            name="Example SelectWords Validation Set"
        ).add_rapid(
            rapi.rapid_builder.select_words_rapid()
            .instruction("Select the words you hear in the audio")
            .media("https://assets.rapidata.ai/where_did_you__today.mp3", 
                   "Where did you go today?") # the text will be split up by spaces and the labeler will be able to select the words
            .truths([0, 1, 2, 4]) # the indices of the words that are correct
            .strict_grading(True) # if True, the labeler must select all correct words to get to the next task
            .build()
        )
    ).submit()
    return validation_set

def new_select_words_order(rapi: RapidataClient, validation_set_id: str):
    order = (
        rapi.order_builder
        .select_words_order(name="Example SelectWords Order")
        .instruction("Select the words you hear in the audio")
        .media(["https://assets.rapidata.ai/openai_tts_demo.mp3"], 
               ["Hello, welcome to OpenAI's Text-to-Speech demo!"]) # the text will not be translated or shuffled
        .validation_set(validation_set_id)
        .languages(["en"]) # The languages of the task - since the text and audio will not be translated, it is beneficial to set the languages.
        .responses(25)
        .submit()
    )
    return order

if __name__ == "__main__":
    rapi = RapidataClient()
    validation_set = create_validation_set(rapi) # only call this once
    validation_set = rapi.find_validation_sets(name="Example SelectWords Validation Set")[0]
    order = new_select_words_order(rapi, validation_set.id)
    order.display_progress_bar()
    result = order.get_results()
    print(result)

