from rapidata.rapidata_client.settings.models.translation_behaviour_options import TranslationBehaviourOptions
from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting

class TranslationBehaviour(RapidataSetting):
    """
    Defines what's the behaviour of the translation in the UI.
    Will not translate text datapoints or sentences.
    
    Args:
        value (TranslationBehaviourOptions): The translation behaviour.
    """
    
    def __init__(self, value: TranslationBehaviourOptions):
        if not isinstance(value, TranslationBehaviourOptions):
            raise ValueError("The value must be a TranslationBehaviourOptions.")
        
        super().__init__(key="translation_behaviour", value=value)

