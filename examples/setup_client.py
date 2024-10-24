'''
Setting up the Rapidata client based on environment variables
'''

import dotenv
import os
from src.rapidata.rapidata_client.rapidata_client import RapidataClient


def setup_client():
    dotenv.load_dotenv()

    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    ENDPOINT = os.getenv("ENDPOINT")
    TOKEN_URL = os.getenv("TOKEN_URL")
    OAUTH_SCOPE = os.getenv("OAUTH_SCOPE")
    CERT_PATH = os.getenv("CERT_PATH")

    if not CLIENT_ID:
        raise Exception("CLIENT_ID not found in environment variables")

    if not CLIENT_SECRET:
        raise Exception("CLIENT_SECRET not found in environment variables")

    if not ENDPOINT:
        raise Exception("ENDPOINT not found in environment variables")

    if not TOKEN_URL:
        raise Exception("TOKEN_URL not found in environment variables")

    if not OAUTH_SCOPE:
        raise Exception("OAUTH_SCOPE not found in environment variables")

    return RapidataClient(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        endpoint=ENDPOINT,
        token_url=TOKEN_URL,
        oauth_scope=OAUTH_SCOPE,
        cert_path=CERT_PATH,
    )
