from rapidata import RapidataClient, NoShuffle

# List of image URLs representing different emotions
IMAGE_URLS: list[str] = [
    "https://assets.rapidata.ai/tshirt-4o.png",   # Related T-Shirt with the text "Running on caffeine & dreams"
    "https://assets.rapidata.ai/tshirt-aurora.jpg",   # Related T-shirt with the text "Running on caffeine & dreams"
    "https://assets.rapidata.ai/teamleader-aurora.jpg",   # Unrelated image
]

CONTEXTS: list[str] = [
    "A t-shirt with the text 'Running on caffeine & dreams'"
] * len(IMAGE_URLS) # Each image will have the same context to be rated by

if __name__ == "__main__":
    rapi = RapidataClient()

    # Create a classification order for emotions based on the images
    order = rapi.order.create_classification_order(
        name="Likert Scale Example",  
        instruction="How well does the image match the description?",
        answer_options=["1: Not at all", 
                        "2: A little", 
                        "3: Moderately", 
                        "4: Very well", 
                        "5: Perfectly"], 
        contexts=CONTEXTS,
        datapoints=IMAGE_URLS,
        responses_per_datapoint=25,
        settings=[NoShuffle()]  # Do not shuffle the answer options
    ).run()  # Execute the order
    
    # Display a progress bar for the order
    order.display_progress_bar()
    
    # Retrieve and print the results of the classification
    results = order.get_results()
    print(results)
