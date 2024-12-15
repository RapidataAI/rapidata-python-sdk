import os

from rapidata import LanguageFilter
from rapidata.annot.api import create_client


DATA_FOLDER = "/Users/marcellschneider/Documents/rapidata/rapidata-python-sdk/src/rapidata/annot/rich_annotations/Example data"
OUTPUT_DIR = "output"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    NAME = "Rich_Annotation-LineRapid-Artifacts-Validation"

    images = [
        os.path.join(DATA_FOLDER, image_file) for image_file in os.listdir(DATA_FOLDER)
        if image_file.endswith(".jpg")
    ]

    client = create_client()
    order = client.order.create_draw_order(
        name=NAME,
        target="Paint the area with your finger where the artificially generated image has a mistake",
        datapoints=images,
        responses_per_datapoint=20,
        validation_set_id="675ae78cd53e277218a8b639",
    )

    order.run()


if __name__ == "__main__":
    main()

