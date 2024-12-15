import json
import os

from PIL import Image, ImageFont
from PIL import ImageDraw
from pydantic.experimental.pipeline import validate_as_deferred

from rapidata import LanguageFilter
from rapidata.annot.api import create_client
from rapidata.rapidata_client.filter import RapidataFilter

DATA_FOLDER = "/Users/marcellschneider/Documents/rapidata/rapidata-python-sdk/src/rapidata/annot/rich_annotations/Example data"
OUTPUT_DIR = "output"
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    NAME = "Rich_Annotation-LineRapid-Alignment-Validation"

    for image_file in os.listdir(DATA_FOLDER):
        if not image_file.endswith(".jpg"):
            continue

        image_path = os.path.join(DATA_FOLDER, image_file)
        json_path = image_path.replace(".jpg", ".json")
        with open(json_path) as json_file:
            prompt = json.load(json_file)["prompt"].replace(" .", ".").title()

        image = Image.open(image_path)

        font_size = 30
        font = ImageFont.truetype(os.path.join("rich_annotations", "Courier New.ttf"), font_size)

        draw = ImageDraw.Draw(image)

        words = prompt.split()
        lines = []
        line = []

        for word in words:
            line.append(word)
            if len(line) == 4:
                lines.append(' '.join(line))
                line = []

        if line:
            lines.append(' '.join(line))

        max_line_length = max([draw.textbbox((0, 0), line, font=font)[2] for line in lines])
        image_width, image_height = image.size

        # Add space for the text above the original image
        text_height = sum([draw.textbbox((0, 0), line, font=font)[3] for line in lines])
        new_image_height = image_height + text_height + 40  # 40 pixels padding between text and image

        # Create a new image with extra space at the top
        new_image = Image.new("RGB", (image_width, new_image_height), (255, 255, 255))

        # Paste the original image into the new image
        new_image.paste(image, (0, text_height + 40))

        # Calculate the text position (centered horizontally)
        text_x = (image_width - max_line_length) / 2
        text_y = 20  # Starting Y position for the text

        # Draw the text on the new image
        for line in lines:
            draw = ImageDraw.Draw(new_image)
            draw.text((text_x, text_y), line, font=font, fill="black")
            text_y += draw.textbbox((0, 0), line, font=font)[3]

        new_image.save(os.path.join(OUTPUT_DIR, image_file))

    client = create_client()
    order = client.order.create_draw_order(
        name=NAME,
        target="Paint the area with your finger where the image does not match the description",
        datapoints=[os.path.join(OUTPUT_DIR, image_file) for image_file in os.listdir(OUTPUT_DIR)],
        responses_per_datapoint=20,
        validation_set_id="675aeb67892adfad2d4401d6",
        filters=[
            LanguageFilter(["en"])
        ]
    )


    order.run()


if __name__ == "__main__":
    main()

