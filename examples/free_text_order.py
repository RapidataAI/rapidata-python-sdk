from examples.setup_client import setup_client
from rapidata.rapidata_client import RapidataClient
from rapidata.rapidata_client.feature_flags import FeatureFlags
from rapidata.rapidata_client.workflow import FreeTextWorkflow
from rapidata.rapidata_client.country_codes import CountryCodes


def new_free_text_order(rapi: RapidataClient):
    order = (
        rapi.new_order(
            name="Example Video Free Text Order",
        )
        .workflow(
            FreeTextWorkflow(
                question="Describe this video!",
            )
        )
        .media(["examples/data/waiting.mp4"])
        .feature_flags(
            FeatureFlags().free_text_minimum_characters(15).alert_on_fast_response(5)
        )
        .country_filter(CountryCodes.ENGLISH_SPEAKING)
    ).create()


if __name__ == "__main__":
    rapi = setup_client()
    new_free_text_order(rapi)
