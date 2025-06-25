from rapidata.rapidata_client.settings import (
    AlertOnFastResponse,
    TranslationBehaviour,
    FreeTextMinimumCharacters,
    NoShuffle,
    PlayVideoUntilTheEnd,
    AllowNeitherBoth,
    )

class RapidataSettings:
    """
    Container class for all setting factory functions

    Settings can be added to an order to determine the behaviour of the task.
    
    Attributes:
        alert_on_fast_response (AlertOnFastResponse): Gives an alert as a pop up on the UI when the response time is less than the milliseconds.
        translation_behaviour (TranslationBehaviour): Defines what's the behaviour of the translation in the UI.
        free_text_minimum_characters (FreeTextMinimumCharacters): Only for free text tasks. Set the minimum number of characters a user has to type.
        no_shuffle (NoShuffle): Only for classification and compare tasks. If true, the order of the categories / images will not be shuffled and presented in the same order as specified.
        play_video_until_the_end (PlayVideoUntilTheEnd): Allows users to only answer once the video has finished playing.
        allow_neither_both (AllowNeitherBoth): Only for compare tasks. If true, the users will be able to select neither or both instead of exclusively one of the options.

    Example:
        ```python
        from rapidata import FreeTextMinimumCharacters
        settings=[FreeTextMinimumCharacters(10)]
        ```

        This can be used in a free text order to set the minimum number of characters required to submit the task. 
    """

    alert_on_fast_response = AlertOnFastResponse
    translation_behaviour = TranslationBehaviour
    free_text_minimum_characters = FreeTextMinimumCharacters
    no_shuffle = NoShuffle
    play_video_until_the_end = PlayVideoUntilTheEnd
    allow_neither_both = AllowNeitherBoth
