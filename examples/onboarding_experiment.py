import sys
sys.path.append('src')
from rapidata.rapidata_client import RapidataClient

def create_demographic_order(rapi: RapidataClient):
    order = rapi.demographic.create_demographic_rapid()

if __name__ == "__main__":
    client = RapidataClient()
    demographic = create_demographic_order(client)
    print(results)
