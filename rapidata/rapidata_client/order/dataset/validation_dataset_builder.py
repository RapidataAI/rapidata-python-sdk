from openapi_client.models.add_validation_rapid_model import AddValidationRapidModel
from rapidata.service.openapi_service import OpenAPIService


class ValidationDatasetBuilder:

    def __init__(self, name: str, openapi_service: OpenAPIService):
        self.name = name
        self.openapi_service = openapi_service
        self.datasetId = None

    def create(self):
        result = self.openapi_service.validation_api.validation_create_validation_set_post(name=self.name)
        # self.datasetId = result.


    def classify_rapid(self, media_path: str):
        # model = {
        #     "validationSetId": self.datasetId,
        #     "truth": {"_t": "AttachCategoryTruth", "correctCategories": truths},
        #     "metadata": [],
        #     "randomCorrectProbability": len(truths)/len(categories),
        #     "payload": {
        #         "_t": "ClassifyPayload",
        #         "title": question,
        #         "possibleCategories": categories,
        #     },
        # }

        # url = f"{self.endpoint}/Validation/AddValidationRapid"

        # data = {"model": json.dumps(model)}

        # file_path = os.path.relpath(
        #     "C:\\Rapidata\\Data\\multi_lingual\\white_image.png"
        # )
        # files = {"files": (f"{text[:100]}.png", open(file_path, "rb"), "image/png")}

        # response = requests.post(url, headers=self.auth_header, files=files, data=data)
        # self.check_response(response)

        # model = AddValidationRapidModel()

        # self.openapi_service.validation_api.validation_add_validation_rapid_post()

        # return response
        pass