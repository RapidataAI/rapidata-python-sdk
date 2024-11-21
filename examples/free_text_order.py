'''
Free Text Order
'''

from rapidata import (
    RapidataClient, 
    CountryCodes, 
)


def new_free_text_order(rapi: RapidataClient):

    order = (rapi.create_free_text_order(name="Example Free Text Order")
             .question("Describe this video!")
             .media(["https://assets.rapidata.ai/waiting.mp4"])
             .responses(3)
             .minimum_characters(15)
             .countries(CountryCodes.ENGLISH_SPEAKING)
             .run())

    return order


if __name__ == "__main__":
    order = new_free_text_order(RapidataClient())
    order.display_progress_bar()
    results = order.get_results()
    print(results)
