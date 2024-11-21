from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.dataset.rapid_builders import ClassifyRapidQuestionBuilder, CompareRapidCriteriaBuilder, TranscriptionRapidInstructionBuilder

class BaseRapidBuilder:
    """Base class for creating different types of rapids.
    
    This class provides factory methods to create specific rapids
    """

    def classify_rapid(self):
        """Creates a classification rapid.
        
        Returns:
            ClassifyRapidQuestionBuilder: A builder for creating the classification question.
        """
        return ClassifyRapidQuestionBuilder()
    
    def compare_rapid(self):    
        """Creates a compare rapid.
        
        Returns:
            CompareRapidCriteriaBuilder: A builder for creating a comparison criteria.
        """
        return CompareRapidCriteriaBuilder()
    
    def transcription_rapid(self):
        """Creates a transcription rapid.
        
        Returns:
            TranscriptionRapidInstructionBuilder: A builder for creating the transcription instruction.
        """
        return TranscriptionRapidInstructionBuilder()
        
