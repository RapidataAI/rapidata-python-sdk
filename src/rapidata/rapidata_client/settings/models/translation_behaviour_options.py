from enum import Enum

class TranslationBehaviourOptions(Enum):
    """The options for the translation behaviour setting.
    
    Attributes:
        BOTH: Show both the original and the translated text.
            May clutter the screen if the options are too long.
        ONLY_ORIGINAL: Show only the original text.
        ONLY_TRANSLATED: Show only the translated text."""
    
    BOTH = "both"
    ONLY_ORIGINAL = "only original"
    ONLY_TRANSLATED = "only translated"
