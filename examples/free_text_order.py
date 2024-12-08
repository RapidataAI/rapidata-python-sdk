'''
Free Text Order
'''

from rapidata import RapidataClient

def get_prompt_ideas(rapi: RapidataClient):

    order = (rapi.order_builder
             .free_text_order(name="Example prompt generation")
             .question("What would you like to ask an AI? please spell out the question")
             .media(["https://assets.rapidata.ai/ai_question.png"])
             .submit())

    return order


if __name__ == "__main__":
    order = get_prompt_ideas(RapidataClient())
    order.display_progress_bar()
    results = order.get_results()
    print(results)
