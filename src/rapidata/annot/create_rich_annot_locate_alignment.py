import json
import os

import dotenv

from rapidata import LanguageFilter
from rapidata.annot.api import create_client
from rapidata.annot.consts import TEST_ENVIRONMENT, DOTENV_PATH, PRODUCTION_ENVIRONMENT

DATA_FOLDER = "/Users/marcellschneider/Documents/rapidata/rapidata-python-sdk/src/rapidata/annot/rich_annotations/Example data"
NAME = "My Image Alignment Order"


def main():
    dotenv.load_dotenv(DOTENV_PATH)

    prompts = []
    paths = []

    for image_file in os.listdir(DATA_FOLDER):
        if not image_file.endswith(".jpg"):
            continue

        image_path = os.path.join(DATA_FOLDER, image_file)
        json_path = image_path.replace(".jpg", ".json")
        with open(json_path) as json_file:
            prompt = json.load(json_file)["prompt"].replace(" .", ".").title()

        prompts.append(prompt)
        paths.append(image_path)

    client = create_client(PRODUCTION_ENVIRONMENT)
    order = client.order.create_locate_order(
        name=NAME,
        target="Tap the area where the image does not match the description",
        datapoints=paths,
        contexts=prompts,
        responses_per_datapoint=20,
        validation_set_id="67689e58026456ec851f51f8", #hand made prompts prod
        filters=[
            LanguageFilter(["en"])
        ]
    )

    order.run()


if __name__ == "__main__":
    main()

