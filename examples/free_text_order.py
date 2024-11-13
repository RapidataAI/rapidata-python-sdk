'''
Free Text Order
'''

from examples.setup_client import setup_client
from rapidata import RapidataClient, FreeTextWorkflow, Settings, CountryCodes, LabelingSelection, MediaAsset


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
        .media([MediaAsset("examples/data/waiting.mp4")])
        .settings(
            Settings().free_text_minimum_characters(15).alert_on_fast_response(5000)
        )
        .selections([
            LabelingSelection(amount=1)
            ])
        # This means that only people in English speaking countries will be able to answer for this order
        .country_filter(CountryCodes.ENGLISH_SPEAKING) 
    ).create()

    return order


if __name__ == "__main__":
    rapi = setup_client()
    new_free_text_order(rapi)
