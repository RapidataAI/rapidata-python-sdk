import os
from io import BytesIO

import dotenv
import numpy as np
import requests
from PIL import Image
import matplotlib.pyplot as plt
from rapidata.annot.api import create_client
import seaborn as sns
from scipy.ndimage import gaussian_filter

from rapidata.annot.consts import PRODUCTION_ENVIRONMENT, TEST_ENVIRONMENT, DOTENV_PATH

LOCATE_ORDER_ID = "6769269efd1e06f7615767fc"
IMAGE_FOLDER = "/Users/marcellschneider/Documents/rapidata/rapidata-python-sdk/src/rapidata/annot/rich_annotations/Example data"
# heatmaps uses a gaussian curve with a sigma. This parameter controls,
# what should be the sigma compared to min(image.width, image.height)
# e.g. TOUCH_BELL_CURVE_SIGMA_TO_IMAGE_RATIO=0.5 if the image is (300, 500) the sigma will be 150
# basically comes down how fat the finger is
TOUCH_BELL_CURVE_SIGMA_TO_IMAGE_RATIO = 0.1
ENVIRONMENT = TEST_ENVIRONMENT

def create_heatmap(image_path, points, output_path):
    image = Image.open(image_path)

    width, height = image.size

    heatmap = np.zeros((height, width))

    for (x, y) in points:
        x, y = int(x/100*image.width), int(y/100*image.height)
        if 0 <= x < width and 0 <= y < height:
            heatmap[y, x] += 1  # Increase intensity at the point

    heatmap = np.clip(heatmap, 0, 1)

    heatmap = gaussian_filter(heatmap, sigma=100)
    plt.imshow(image, alpha=1)
    plt.imshow(heatmap, cmap='hot', alpha=0.5, interpolation='bilinear', extent=(0, width, height, 0))
    plt.axis('off')

    plt.savefig(output_path, format='png', bbox_inches='tight', pad_inches=0)


def main():
    dotenv.load_dotenv(DOTENV_PATH)
    OUTPUT_FOLDER = f"heatmaps_{LOCATE_ORDER_ID}"

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    client = create_client(ENVIRONMENT)
    order = client.order.get_order_by_id(LOCATE_ORDER_ID)
    results = order.get_results()

    for rapid in results["results"]:
        image_name = rapid["originalFileName"]
        image_path = os.path.join(IMAGE_FOLDER, image_name)

        points = [(int(p['x']), int(p['y'])) for p in rapid["aggregatedResults"]]
        create_heatmap(image_path, points, os.path.join(OUTPUT_FOLDER, image_name))


if __name__ == '__main__':
    main()
