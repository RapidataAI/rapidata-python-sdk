from rapidata import RapidataClient

IMAGE_URLS = ["https://assets.rapidata.ai/midjourney-5.2_37_3.jpg", 
              "https://assets.rapidata.ai/flux-1-pro_37_0.jpg",
              "https://assets.rapidata.ai/frames-23-1-25_37_4.png",
              "https://assets.rapidata.ai/aurora-20-1-25_37_3.png"]

    
if __name__ == "__main__":
    rapi = RapidataClient()

    order = rapi.order.create_draw_order(
        name="Example Image Comparison",
        instruction="Color in all the blue books",
        datapoints=IMAGE_URLS,
        responses_per_datapoint=35,
    ).run()

    order.display_progress_bar()

    results = order.get_results()
    print(results)
