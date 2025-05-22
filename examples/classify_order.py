from rapidata import RapidataClient

# List of image URLs representing different emotions
IMAGE_URLS: list[str] = [
    "https://assets.rapidata.ai/dalle-3_anger.webp",   # Image representing anger
    "https://assets.rapidata.ai/dalle-3_disgust.webp",  # Image representing disgust
    "https://assets.rapidata.ai/dalle-3_happiness.webp", # Image representing happiness
    "https://assets.rapidata.ai/dalle-3_sadness.webp"    # Image representing sadness
]

if __name__ == "__main__":
    # Create a Rapidata client instance
    rapi = RapidataClient()

    # Create a classification order for emotions based on the images
    order = rapi.order.create_classification_order(
        name="Emotions from Images",  # Title of the order
        instruction="What emotion do you feel when you look at this image?",  # Instruction for the user
        answer_options=["happy", "sad", "angry", "surprised", "disgusted", "scared", "neutral"],  # Possible answers
        datapoints=IMAGE_URLS,  # Images to classify
        responses_per_datapoint=25  # Number of responses for each image
    ).run()  # Execute the order

    # To preview the order, you can uncomment the following line:
    # order.preview()

    # To open the order in the browser, you can uncomment the following line:
    # order.view()

    # Display the progress of the order
    order.display_progress_bar()
    
    # Retrieve and print the results of the classification
    results = order.get_results()
    print(results)
