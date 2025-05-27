from rapidata import RapidataClient, RapidataSettings

IMAGE_URLS = ["https://assets.rapidata.ai/eac11c3e-ad57-402b-90ed-23378d2ff869.jpg",
              "https://assets.rapidata.ai/04e7e3c6-5554-47ca-bdb2-950e48ac3e6c.jpg",
              "https://assets.rapidata.ai/91d9913c-b399-47f8-ad19-767798cc951c.jpg",
              "https://assets.rapidata.ai/d1cbf51d-7712-4819-96b4-20e030c573de.jpg"]

    
if __name__ == "__main__":

    rapi = RapidataClient()

    order = rapi.order.create_locate_order(
        name="Artifact detection example",
        instruction="Look close, find incoherent errors, like senseless or malformed objects, incomprehensible details, or visual glitches? Tap to select.",
        datapoints=IMAGE_URLS,
        responses_per_datapoint=35,
        settings=[RapidataSettings.alert_on_fast_response(2500)], # This is optional, it will alert you if the annotators are responding before 2.5 seconds
        validation_set_id="6768a557026456ec851f51f9" # in this example, the validation set has already been created
    ).run()
