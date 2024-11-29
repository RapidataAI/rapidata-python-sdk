from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.simple_builders.simple_classification_builders import ClassificationQuestionBuilder
from rapidata.rapidata_client.simple_builders.simple_compare_builders import CompareCriteriaBuilder
from rapidata.rapidata_client.simple_builders.simple_free_text_builders import FreeTextQuestionBuilder
from rapidata.rapidata_client.simple_builders.simple_select_words_builders import SelectWordsInstructionBuilder
from rapidata.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder

class BaseOrderBuilder():
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service
    
    def classify_order(self, name: str):
        return ClassificationQuestionBuilder(name, self.openapi_service)
    
    def compare_order(self, name: str):
        return CompareCriteriaBuilder(name, self.openapi_service)

    def free_text_order(self, name: str):
        return FreeTextQuestionBuilder(name, self.openapi_service)
    
    def select_words_order(self, name: str):
        return SelectWordsInstructionBuilder(name, self.openapi_service)

    def advanced_order(self, name: str):
        return RapidataOrderBuilder(name, self.openapi_service)
