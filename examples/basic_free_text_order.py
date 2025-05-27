from rapidata import RapidataClient

if __name__ == "__main__":
    rapi = RapidataClient()
    order = rapi.order.create_free_text_order(
        name="Example prompt generation",
        instruction="What would you like to ask an AI? please spell out the question",
        datapoints=["https://assets.rapidata.ai/ai_question.png"],
    ).run()
    order.display_progress_bar()
    results = order.get_results()
    print(results)
