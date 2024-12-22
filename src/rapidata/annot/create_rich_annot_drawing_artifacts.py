import os
from rapidata.annot.api import create_client
from rapidata.annot.consts import ARTIFACT_PROMPT, ARTIFACT_VALIDATION_SET

DATA_FOLDER = "/Users/marcellschneider/Documents/rapidata/rapidata-python-sdk/src/rapidata/annot/rich_annotations/Example data"


def main():
    NAME = "Rich_Annotation-LineRapid-Artifacts-Validation-Prompts"

    images = [
        os.path.join(DATA_FOLDER, image_file) for image_file in os.listdir(DATA_FOLDER)
        if image_file.endswith(".jpg")
    ]

    client = create_client()
    order = client.order.create_draw_order(
        name=NAME,
        target=ARTIFACT_PROMPT,
        datapoints=images,
        responses_per_datapoint=20,
        validation_set_id=ARTIFACT_VALIDATION_SET
    )

    order.run()


if __name__ == "__main__":
    main()
