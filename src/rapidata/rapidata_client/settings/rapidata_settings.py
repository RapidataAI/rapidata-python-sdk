from rapidata.rapidata_client.settings import (
    AlertOnFastResponse,
    TranslationBehaviour,
    FreeTextMinimumCharacters,
    NoShuffle,
    PlayVideoUntilTheEnd,
    CustomSetting,
    )

class RapidataSettings:
    """
    Container class for all setting factory functions

    Settings can be added to an order to determine the behaviour of the task.
    
    Attributes:
        alert_on_fast_response (AlertOnFastResponse): The AlertOnFastResponse instance.
        translation_behaviour (TranslationBehaviour): The TranslationBehaviour instance.
        free_text_minimum_characters (FreeTextMinimumCharacters): The FreeTextMinimumCharacters instance.
        no_shuffle (NoShuffle): The NoShuffle instance.
        play_video_until_the_end (PlayVideoUntilTheEnd): The PlayVideoUntilTheEnd instance.
        custom_setting (CustomSetting): The CustomSetting instance.
    """

    alert_on_fast_response = AlertOnFastResponse
    translation_behaviour = TranslationBehaviour
    free_text_minimum_characters = FreeTextMinimumCharacters
    no_shuffle = NoShuffle
    play_video_until_the_end = PlayVideoUntilTheEnd
    custom_setting = CustomSetting

