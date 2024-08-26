from openapi_client.models.add_validation_rapid_model import AddValidationRapidModel
from openapi_client.models.add_validation_rapid_model_payload import (
    AddValidationRapidModelPayload,
)
from openapi_client.models.add_validation_rapid_model_truth import (
    AddValidationRapidModelTruth,
)
from openapi_client.models.attach_category_truth import AttachCategoryTruth
from openapi_client.models.classify_payload import ClassifyPayload
from rapidata.service.openapi_service import OpenAPIService


class ValidationDatasetBuilder:

    def __init__(self, name: str, openapi_service: OpenAPIService):
        self.name = name
        self.openapi_service = openapi_service
        self.validationSetId: str | None = None

    def create(self):
        result = (
            self.openapi_service.validation_api.validation_create_validation_set_post(
                name=self.name
            )
        )
        self.validationSetId = result.id

    def classify_rapid(
        self, media_path: str, question: str, categories: list[str], truths: list[str]
    ):
        if self.validationSetId is None:
            raise ValueError("ValidataionSet ID is not set. Call create() first.")

        model = {
            "validationSetId": self.validationSetId,
            "truth": {"_t": "AttachCategoryTruth", "correctCategories": truths},
            "metadata": [],
            "randomCorrectProbability": len(truths) / len(categories),
            "payload": {
                "_t": "ClassifyPayload",
                "title": question,
                "possibleCategories": categories,
            },
        }

        payload = ClassifyPayload(
            _t="ClassifyPaylod", possibleCategories=categories, title=question
        )
        model_truth = AttachCategoryTruth(
            correctCategories=truths, _t="AttachCategoryTruth"
        )

        model = AddValidationRapidModel(
            validationSetId=self.validationSetId,
            payload=AddValidationRapidModelPayload(payload),
            metadata=[],
            randomCorrectProbability=len(truths) / len(categories),
            truth=AddValidationRapidModelTruth(model_truth),
        )

        response = (
            self.openapi_service.validation_api.validation_add_validation_rapid_post(
                model=model, files=[media_path]
            )
        )
