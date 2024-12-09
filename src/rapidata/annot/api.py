import json

from PIL import Image

from rapidata.annot.models import ValidationRapidCollection, BBox
import dotenv
import requests
import os
from rapidata import RapidataClient


def _create_validation_set(name: str, client: RapidataClient) -> str:

    HEADERS = {
        "Authorization": client.openapi_service.api_client.configuration.api_key["bearer"],
        "accept": "text/plain",
    }
    ENDPOINT = f"https://api.app.rapidata.ai/Validation/CreateValidationSet?name={name}"

    r = requests.post(ENDPOINT, headers=HEADERS)
    return r.json()['validationSetId']


def _add_rapid(validation_set_id: str, client, image: Image, box: BBox):
    data = {
        "validationSetId": validation_set_id,
        "payload": {
            "_t": "LocatePayload",
            "target": "Find the Dogs!"
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
            "xMin": box.x,
            "yMin": box.y,
            "xMax": box.x + box.width,
            "yMax": box.y + box.height,
        },
        "randomCorrectProbability": (box.width*box.height) / (image.width*image.height),
    }

    HEADERS = {
        "Authorization": client.openapi_service.api_client.configuration.api_key["bearer"],
    }
    ENDPOINT = f"https://api.app.rapidata.ai/Validation/AddValidationRapid"

    r = requests.post(ENDPOINT, json=data, headers=HEADERS)
    print(str(r.content))
    return r.json()['validationSetId']


def create_rapidata_validation_set(name: str, collection: ValidationRapidCollection):
    dotenv.load_dotenv('/Users/sneccello/Documents/rapidata/data_doctor/ranking_poc/.env')
    client = RapidataClient(
        client_id=os.environ['CLIENT_ID'],
        client_secret=os.environ['CLIENT_SECRET'],
    )

if __name__ == '__main__':

    dotenv.load_dotenv('/Users/sneccello/Documents/rapidata/data_doctor/ranking_poc/.env')
    client = RapidataClient(
        client_id=os.environ['CLIENT_ID'],
        client_secret=os.environ['CLIENT_SECRET'],
    )


    #r = requests.post(ENDPOINT, headers=HEADERS)
    val_set_id = "67576eaa547528b23c2deaa6" #_create_validation_set(client, test)

    _add_rapid(val_set_id, client,
               Image.open("/Users/sneccello/Documents/rapidata/rapidata-python-sdk/src/rapidata/annot/panda.png"),
               BBox(0, 0, 100, 100, 1))





