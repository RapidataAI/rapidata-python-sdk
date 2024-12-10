'''
Classify order with a validation set
'''

from rapidata import RapidataClient


def get_emotions_of_images_order(rapi: RapidataClient):
    base_url = "https://assets.rapidata.ai/dalle-3_"
    emotions = ["anger", "disgust", "happiness", "sadness"]
    generated_images_urls = [f"{base_url}{emotion}.webp" for emotion in emotions]
    # Configure order

    order = rapi.order.create_classification_order(
        name="emotions from images",
        question="What emotions do you feel when looking at the image?",
        options=["happy", "sad", "angry", "surprised", "disgusted", "scared", "neutral"],
        datapoints=generated_images_urls,
        responses_per_datapoint=50
        ).run()

    return order


if __name__ == "__main__":
    order = get_emotions_of_images_order(RapidataClient())
    order.display_progress_bar()
    results = order.get_results()
    print(results)
