import importlib
import tempfile
from io import BytesIO
from typing import List, Optional

from PIL import Image
import requests
import os
from models import BBox, ValidationRapid, RapidTypes
from rapidata import RapidataClient, Box
from rapidata.annot.consts import PRODUCTION_ENVIRONMENT, TEST_ENVIRONMENT
from rapidata.rapidata_client import PromptMetadata
from rapidata.rapidata_client.validation.rapids.rapids import LocateRapid, Rapid
from utils import calc_image_scale, get_next_rapid_id

modules = [
    'tempfile', 'io', 'PIL', 'requests', 'os',
    'models', 'rapidata', 'rapidata.annot.consts',
    'rapidata.rapidata_client', 'utils'
]

# Re-import the modules
for module in modules:
    importlib.reload(importlib.import_module(module))

def get_api_endpoint(path: str, env: str) -> str:
    return f"https://api.{get_env_domain(env)}/{path}"



def _create_locate_rapids(rapids: List[ValidationRapid], global_prompt: str, env: str) -> List[LocateRapid]:
    client = create_client(env)
    locate_rapids = []
    for rapid in rapids:
        annotation = rapid.annotation["objects"][0]

        x, y, width, height = annotation["left"], annotation["top"], annotation["width"], annotation["height"]
        bbox = BBox(x, y, width, height, annotation_scale=1 / calc_image_scale(rapid.image)).get_scaled()
        print(rapid.prompt)
        SUFFIX = "png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=SUFFIX) as temp_file:
            temp_file_path = temp_file.name + '.' + SUFFIX
            rapid.image.save(temp_file_path)

            rapid = client.validation.rapid.locate_rapid(
                instruction=global_prompt,
                truths=[
                    Box(
                        x_min=bbox.x,
                        x_max=bbox.x + bbox.width,
                        y_min=bbox.y,
                        y_max=bbox.y + bbox.height,
                    )
                ],
                datapoint=temp_file_path,
                metadata=[
                    PromptMetadata(
                        prompt=rapid.prompt,
                    )
                ] if rapid.prompt else [],
            )
            locate_rapids.append(rapid)

    return locate_rapids


def _create_validation_set(name:str, rapids: List[Rapid], env: str):

    client = create_client(env)

    val_set = client.validation.create_mixed_set(
        name=name,
        rapids=rapids,
        print_confirmation=False
    )
    return val_set.id

def validation_set_from_rapids(name: str, global_prompt: str, rapids: List[ValidationRapid], rapid_type: RapidTypes, env: str) -> str:

    if rapid_type == RapidTypes.LOCATE or True:
        rapids = _create_locate_rapids(rapids, global_prompt, env)
    else:
        raise ValueError(f"Unknown rapid type: {rapid_type}")

    return _create_validation_set(name, rapids, env)



def get_asset_url(asset: str, env: str):
    return f"https://assets.{get_env_domain(env)}/{asset}"


def get_image_asset(asset_name: str, env: str):
    image_url = get_asset_url(asset_name, env)

    response = requests.get(image_url)
    response.raise_for_status()

    return Image.open(BytesIO(response.content))


def get_env_domain(env: str):
    if env == PRODUCTION_ENVIRONMENT:
        return 'rapidata.ai'
    elif env == TEST_ENVIRONMENT:
        return 'rabbitdata.ch'
    raise ValueError("Unkown environment")

def create_client(env: str):
    if env == PRODUCTION_ENVIRONMENT:
        return RapidataClient(
            client_id=os.environ['CLIENT_ID'],
            client_secret=os.environ['CLIENT_SECRET'],
            enviroment=get_env_domain(env),
        )
    else:
        return RapidataClient(
            client_id=os.environ['TEST_CLIENT_ID'],
            client_secret=os.environ['TEST_CLIENT_SECRET'],
            enviroment=get_env_domain(env)
        )

def get_validation_rapids(validation_set_id: str, env: str) -> Optional[List[ValidationRapid]]:
    client = create_client(env)
    HEADERS = {
        "Authorization": client._openapi_service.api_client.configuration.api_key["bearer"],
        "accept": "text/plain",
    }

    ENDPOINT = get_api_endpoint(f"Rapid/QueryValidationRapids?validationSetId={validation_set_id}", env)
    r = requests.get(ENDPOINT, headers=HEADERS)

    if r.status_code == 404:
        return None

    return [ValidationRapid(
        name=r['asset']['fileName'],
        image=get_image_asset(r['asset']['fileName'], env),
        rapid_id=get_next_rapid_id())
            for r in r.json()['items']]

def get_validation_set_url(validation_set_id: str, env) -> str:
    return f"https://app.{get_env_domain(env)}/validation-set/detail/{validation_set_id}"
