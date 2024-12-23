import os

import dotenv

from rapidata.annot.api import create_client
from rapidata.annot.consts import PRODUCTION_ENVIRONMENT, TEST_ENVIRONMENT, DOTENV_PATH

DATA_FOLDER = "/Users/marcellschneider/Documents/rapidata/rapidata-python-sdk/src/rapidata/annot/rich_annotations/Example data"
NAME = "My Image Artifact Order"
ENVIRONMENT = TEST_ENVIRONMENT

VALIDATION_SETS = {
    TEST_ENVIRONMENT: '6768a4c0566e0d4ecc52f36e',
    PRODUCTION_ENVIRONMENT: '6768a557026456ec851f51f9'
}

def main():
    dotenv.load_dotenv(DOTENV_PATH)
    images = [
        os.path.join(DATA_FOLDER, image_file) for image_file in os.listdir(DATA_FOLDER)
        if image_file.endswith(".jpg")
    ]

    client = create_client(ENVIRONMENT)
    order = client.order.create_locate_order(
        name=NAME,
        target='Tap the area where the artificially generated image has a mistake',
        datapoints=images,
        responses_per_datapoint=20,
        validation_set_id=VALIDATION_SETS[ENVIRONMENT],
    )

    order.run()


if __name__ == "__main__":
    main()
