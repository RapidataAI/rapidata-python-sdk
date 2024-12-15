import json
import tempfile
from io import BytesIO
from typing import List, Optional
import dotenv
from PIL import Image
import requests
import os
from models import BBox, ValidationRapid, RapidTypes
from rapidata import RapidataClient, Box
from rapidata.annot.consts import DOMAIN, DOTENV_PATH, ENV
from rapidata.rapidata_client.validation.rapids.rapids import LocateRapid, Rapid
from utils import calc_image_scale


def get_api_endpoint(path: str) -> str:
    return f"https://api.{DOMAIN}/{path}"


def create_validation_set_depr(name: str) -> str:


    HEADERS = {
        "Authorization": client.openapi_service.api_client.configuration.api_key["bearer"],
        "accept": "text/plain",
    }
    ENDPOINT = get_api_endpoint(f"Validation/CreateValidationSet?name={name}")

    r = requests.post(ENDPOINT, headers=HEADERS)

    return r.json()['validationSetId']


def _add_rapid(validation_set_id: str, rapid_type: RapidTypes, prompt: str, image: Image, box: BBox, filename: str) -> str:
    client = create_client()

    data = {
        "validationSetId": validation_set_id,
        "payload": {
            "_t": f"{rapid_type.value}Payload",
            "target": prompt
        },
        "metadata": [
            {
                "_t": "PrivateTextMetadataInput",
                "text": "idk whats this for",
                "identifier": "idk whats this for2"
            }
        ],
        "truth": {
            "_t": "BoundingBoxTruth",
            "xMin": box.x / image.width,
            "yMin": box.y / image.height,
            "xMax": (box.x + box.width) / image.width,
            "yMax": (box.y + box.height) / image.height,
        },
        "randomCorrectProbability": (box.width * box.height) / (image.width * image.height),
    }

    HEADERS = {
        "Authorization": client.openapi_service.api_client.configuration.api_key["bearer"]
    }

    ENDPOINT = get_api_endpoint("Validation/AddValidationRapid")

    suffix = filename.split('.')[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file_path = temp_file.name + '.' + suffix
        image.save(temp_file_path)

    files = {
        'files': (os.path.basename(temp_file_path), open(temp_file_path, 'rb'), 'image/jpeg')
    }

    data = {
        'model': json.dumps(data)
    }

    try:
        # Make the request
        r = requests.post(ENDPOINT, data=data, files=files, headers=HEADERS)
        r.raise_for_status()  # Will raise an exception for bad status codes
        return r.json()['rapidId']
    finally:
        # Clean up: Close the file and remove the temporary file
        files['files'][1].close()  # Close the file handler
        os.remove(temp_file_path)  # Delete the temporary file


def _create_locate_rapids(rapids: List[ValidationRapid]) -> List[LocateRapid]:
    client = create_client()
    locate_rapids = []
    for rapid in rapids:
        annotation = rapid.annotation["objects"][0]

        x, y, width, height = annotation["left"], annotation["top"], annotation["width"], annotation["height"]
        bbox = BBox(x, y, width, height, annotation_scale=1 / calc_image_scale(rapid.image)).get_scaled()

        SUFFIX = "png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=SUFFIX) as temp_file:
            temp_file_path = temp_file.name + '.' + SUFFIX
            rapid.image.save(temp_file_path)

            rapid = client.validation.rapid.build_draw_rapid(
                target=rapid.prompt,
                truths=[
                    Box(
                        x_min=bbox.x,
                        x_max=bbox.x + bbox.width,
                        y_min=bbox.y,
                        y_max=bbox.y + bbox.height,
                    )
                ],
                datapoint=temp_file_path
            )
            locate_rapids.append(rapid)

    return locate_rapids


def _create_validation_set(name:str, rapids: List[Rapid]):

    client = create_client()
    val_set = client.validation.create_rapid_set(
        name=name,
        rapids=rapids,
        print_confirmation=False
    )
    return val_set.id

def validation_set_from_rapids(name: str, rapids: List[ValidationRapid], rapid_type: RapidTypes) -> str:

    if rapid_type == RapidTypes.LOCATE:
        rapids = _create_locate_rapids(rapids)
    else:
        raise ValueError("Unknown rapid type")

    return _create_validation_set(name, rapids)



def add_rapids_to_validation_set(rapids: List[ValidationRapid], rapid_type: RapidTypes, validation_set_id: str):
    for rapid in rapids:
        image = rapid.image
        annotation = rapid.annotation['objects'][0]
        x, y, width, height = annotation["left"], annotation["top"], annotation["width"], annotation["height"]
        bbox = BBox(x, y, width, height, annotation_scale=1 / calc_image_scale(image))
        rapid_id = _add_rapid(validation_set_id, rapid_type, rapid.prompt, image, bbox.get_scaled(), rapid.name)
        rapid.local_rapid_id = rapid_id


def get_asset_url(asset: str):
    return f"https://assets.{DOMAIN}/{asset}"


def get_image_asset(asset_name: str):
    image_url = get_asset_url(asset_name)

    response = requests.get(image_url)
    response.raise_for_status()

    return Image.open(BytesIO(response.content))


def create_client():
    dotenv.load_dotenv(DOTENV_PATH, override=True)
    if ENV == 'prod':
        return RapidataClient(
            client_id=os.environ['CLIENT_ID'],
            client_secret=os.environ['CLIENT_SECRET'],
            enviroment=DOMAIN,
        )
    else:
        return RapidataClient(
            client_id=os.environ['TEST_CLIENT_ID'],
            client_secret=os.environ['TEST_CLIENT_SECRET'],
            enviroment=DOMAIN
        )

def get_validation_rapids(validation_set_id: str) -> Optional[List[ValidationRapid]]:
    client = create_client()
    HEADERS = {
        "Authorization": client.openapi_service.api_client.configuration.api_key["bearer"],
        "accept": "text/plain",
    }

    ENDPOINT = get_api_endpoint(f"Rapid/QueryValidationRapids?validationSetId={validation_set_id}")
    r = requests.get(ENDPOINT, headers=HEADERS)

    if r.status_code == 404:
        return None

    return [ValidationRapid(name=r['asset']['fileName'], image=get_image_asset(r['asset']['fileName']))
            for r in r.json()['items']]

def get_validation_set_url(validation_set_id: str) -> str:
    return f"https://app.{DOMAIN}/validation-set/detail/{validation_set_id}"
