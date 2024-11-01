'''
Compare order with a validation set
'''

from examples.setup_client import setup_client
from rapidata import (
    FeatureFlags,
    NaiveReferee,
    CompareWorkflow,
    RapidataClient,
    LabelingSelection,
    ValidationSelection,
    MultiAsset,
    MediaAsset,
)


def new_compare_order(rapi: RapidataClient):
    logo_path = "examples/data/rapidata_logo.png"
    concept_path = "examples/data/rapidata_concept_logo.jpg"

    # configure validation set
    validation_set = (
        rapi.new_validation_set(name="Example SimpleMatchup Validation Set")
        .add_compare_rapid(
            asset=MultiAsset([MediaAsset(logo_path), MediaAsset(concept_path)]),
            question="Which logo is the actual Rapidata logo?",
            truth=logo_path,
        )
        .create()
    )

    # configure order
    order = (
        rapi.new_order(
            name="Example SimpleMatchup Order",
        )
        .workflow(
            CompareWorkflow(
                criteria="Which logo is better?",
            )
        )
        .referee(NaiveReferee(responses=1))
        .media([
            MultiAsset([
                MediaAsset(path="examples/data/rapidata_concept_logo.jpg"), 
                MediaAsset(path="examples/data/rapidata_logo.png")
                ])]
        )
        .selections([
            ValidationSelection(amount=1, validation_set_id=validation_set.id),
            LabelingSelection(amount=1)
            ])
        .feature_flags( # This means that if someone tries to answer before 2 seconds, they will be warned. use with caution. should be the bare minimum.
            FeatureFlags().alert_on_fast_response(2000) 
        )
        .create()
    )

    return order


if __name__ == "__main__":
    rapi = setup_client()
    new_compare_order(rapi)
