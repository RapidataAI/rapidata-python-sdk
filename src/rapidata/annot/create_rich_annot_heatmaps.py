import os
from calendar import prmonth
from pathlib import Path
import dotenv
import numpy as np
import pandas as pd
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from tqdm import tqdm
from typing import List, Tuple
from rapidata.annot.api import create_client
from scipy.ndimage import gaussian_filter
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import matplotlib.font_manager as fm
from concurrent.futures import ProcessPoolExecutor, as_completed

from rapidata.annot.consts import PRODUCTION_ENVIRONMENT

LOCATE_ORDER_ID = "676e9fc7ae2d41bf9acff73d"
IMAGE_FOLDER = "/Users/marcellschneider/Documents/rapidata/rapidata-python-sdk/src/rapidata/annot/leaderboard"
TOUCH_BELL_CURVE_SIGMA_TO_IMAGE_RATIO = 1/20
ENVIRONMENT = PRODUCTION_ENVIRONMENT


def add_text_to_image(image: Image, prompt: str, font_path="Arial.ttf", font_size=40) -> Image:
    # Load the font
    font = ImageFont.truetype(font_path, font_size)

    # Split the prompt into words
    words = prompt.split()

    # Break the prompt into lines of 5 words
    lines = []
    while len(words) > 0:
        lines.append(" ".join(words[:5]))
        words = words[5:]

    # Create a drawing context
    draw = ImageDraw.Draw(image)

    img_width, img_height = image.size

    # Get the bounding box of each line
    line_heights = []
    max_line_width = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1]
        max_line_width = max(max_line_width, line_width)
        line_heights.append(line_height)

    # Calculate the new image size (width + text area, height enough for all lines)
    new_img_width = img_width + max_line_width + 10  # Padding after the image
    new_img_height = max(img_height, sum(line_heights) + (len(lines) - 1) * 5)  # Add spacing between lines

    # Create a new blank image (white background)
    new_image = Image.new("RGB", (new_img_width, new_img_height), "white")

    # Paste the original image onto the new image (left side)
    new_image.paste(image, (0, 0))

    # Create a drawing context for the new image
    draw_new = ImageDraw.Draw(new_image)

    # Position and draw each line of text on the new image
    text_x = img_width + 10  # Start 10px after the original image
    text_y = (new_img_height - sum(line_heights) - (len(lines) - 1) * 5) // 2  # Vertically center the lines

    for i, line in enumerate(lines):
        # Draw each line of text
        draw_new.text((text_x, text_y), line, font=font, fill="black")
        text_y += line_heights[i] + 5  # Add space between lines

    return new_image


def create_heatmap(image_path: Path, points: List[List[Tuple[int, int]]], output_folder, prompt):
    image = Image.open(image_path)
    width, height = image.size

    sigma = TOUCH_BELL_CURVE_SIGMA_TO_IMAGE_RATIO * min(width, height)

    xs = []
    ys = []
    heatmaps = []
    for annot in points:
        heatmap = np.zeros((height, width))
        for x, y in annot:
            x, y = min(int(x / 100 * image.width), image.width - 1), min(int(y / 100 * image.height), image.height - 1)
            xs.append(x)
            ys.append(y)
            assert 0 <= x < width and 0 <= y < height

            heatmap[y, x] += 1

        heatmap = gaussian_filter(heatmap, sigma=sigma, truncate=3)
        heatmap /= heatmap.max()
        heatmaps.append(heatmap)

    heatmap = np.array(heatmaps).mean(axis=0)

    np.save(os.path.join(output_folder, f"{image_path.name}_submissions.npy"), heatmap)
    np.save(os.path.join(output_folder, f"{image_path.name}_heatmap.npy"), heatmap)

    image = add_text_to_image(image, prompt)
    plt.imshow(image, alpha=1)
    plt.axis('off')
    plt.savefig(os.path.join(output_folder, f'{image_path.name}_original.png'), bbox_inches='tight', pad_inches=0)

    norm = mcolors.Normalize(vmin=0, vmax=1, clip=True)
    plt.imshow(heatmap, cmap='hot', alpha=0.8, interpolation='bilinear', extent=(0, width, height, 0), norm=norm)
    plt.savefig(os.path.join(output_folder, f'{image_path.name}_overlay.png'), bbox_inches='tight', pad_inches=0)
    plt.scatter(xs, ys)
    plt.savefig(os.path.join(output_folder, f'{image_path.name}_overlay_with_scatter.png'), bbox_inches='tight', pad_inches=0)
    plt.clf()


def main():
    dotenv.load_dotenv('.env')  # Ensure you load environment variables
    OUTPUT_FOLDER = f"heatmaps_prod_{LOCATE_ORDER_ID}"

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    client = create_client(ENVIRONMENT)
    order = client.order.get_order_by_id(LOCATE_ORDER_ID)
    results = order.get_results()

    df = pd.read_csv('Rapidata-Benchmark.csv').set_index('uid')
    df.index = df.index.astype(int)

    tasks = []
    for rapid in results["results"]:
        image_name = rapid["originalFileName"]
        model, UID, model_run = image_name.split("_")
        UID = int(UID)
        prompt = df.loc[UID,].prompt
        image_path = f'./leaderboard/{model}/{image_name}'

        points = [[(p['x'], int(p['y'])) for p in annots['location']] for annots in rapid["detailedResults"]]
        tasks.append((Path(image_path), points, Path(OUTPUT_FOLDER), prompt))

    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(create_heatmap, *task) for task in tasks]
        for future in tqdm(as_completed(futures), total=len(futures)):
            try:
                future.result()
            except Exception as e:
                print(f"Error processing heatmap: {e}")


if __name__ == '__main__':
    main()
