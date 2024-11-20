from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.dataset.rapid_builders import ClassifyRapidQuestionBuilder, CompareRapidCriteriaBuilder, TranscriptionRapidInstructionBuilder

class BaseRapidBuilder:

    def classify_rapid(self):
        return ClassifyRapidQuestionBuilder()
    
    def compare_rapid(self):    
        return CompareRapidCriteriaBuilder()
    
    def transcription_rapid(self):
        return TranscriptionRapidInstructionBuilder()
        
