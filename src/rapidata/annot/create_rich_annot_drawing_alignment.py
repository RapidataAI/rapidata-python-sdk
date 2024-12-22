import json
import os

import dotenv

from rapidata import LanguageFilter
from rapidata.annot.api import create_client
from rapidata.annot.consts import ALIGNMENT_PROMPT, LANGUAGES, TEST_ENVIRONMENT, DOTENV_PATH

DATA_FOLDER = "/Users/marcellschneider/Documents/rapidata/rapidata-python-sdk/src/rapidata/annot/rich_annotations/Example data"


def main():
    dotenv.load_dotenv(DOTENV_PATH)
    NAME = "TEST"

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

    client = create_client(TEST_ENVIRONMENT)
    order = client.order.create_locate_order(
        name=NAME,
        target=ALIGNMENT_PROMPT,
        datapoints=paths,
        contexts=prompts,
        responses_per_datapoint=20,
        validation_set_id="67689468785902043dcea5e2", #artificial prompts
        filters=[
            LanguageFilter(["hu"])
        ]
    )

    order.run()


if __name__ == "__main__":
    main()

