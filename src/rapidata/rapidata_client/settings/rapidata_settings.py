from rapidata.rapidata_client.settings.alert_on_fast_response import AlertOnFastResponse
from rapidata.rapidata_client.settings.translation_behaviour import TranslationBehaviour
from rapidata.rapidata_client.settings.free_text_minimum_characters import FreeTextMinimumCharacters
from rapidata.rapidata_client.settings.no_shuffle import NoShuffle
from rapidata.rapidata_client.settings.play_video_until_the_end import PlayVideoUntilTheEnd
from rapidata.rapidata_client.settings.allow_neither_both import AllowNeitherBoth
from rapidata.rapidata_client.settings.swap_context_instruction import SwapContextInstruction
from rapidata.rapidata_client.settings.mute_video import MuteVideo


class RapidataSettings:
    """
    Container class for all setting factory functions

    Settings can be added to an order to determine the behaviour of the task.

    Attributes:
        AlertOnFastResponse (AlertOnFastResponse): Gives an alert as a pop up on the UI when the response time is less than the milliseconds.
        TranslationBehaviour (TranslationBehaviour): Defines what's the behaviour of the translation in the UI.
        FreeTextMinimumCharacters (FreeTextMinimumCharacters): Only for free text tasks. Set the minimum number of characters a user has to type.
        NoShuffle (NoShuffle): Only for classification and compare tasks. If true, the order of the categories / images will not be shuffled and presented in the same order as specified.
        PlayVideoUntilTheEnd (PlayVideoUntilTheEnd): Allows users to only answer once the video has finished playing.
        AllowNeitherBoth (AllowNeitherBoth): Only for compare tasks. If true, the users will be able to select neither or both instead of exclusively one of the options.
        SwapContextInstruction (SwapContextInstruction): Swap the place of the context and instruction.
        MuteVideo (MuteVideo): Mute the video.

    Example:
        ```python
        from rapidata import FreeTextMinimumCharacters
        settings=[FreeTextMinimumCharacters(10)]
        ```

        This can be used in a free text order to set the minimum number of characters required to submit the task.
    """

    AlertOnFastResponse = AlertOnFastResponse
    TranslationBehaviour = TranslationBehaviour
    FreeTextMinimumCharacters = FreeTextMinimumCharacters
    NoShuffle = NoShuffle
    PlayVideoUntilTheEnd = PlayVideoUntilTheEnd
    AllowNeitherBoth = AllowNeitherBoth
    SwapContextInstruction = SwapContextInstruction
    MuteVideo = MuteVideo

    def __str__(self) -> str:
        return f"RapidataSettings(AlertOnFastResponse={self.AlertOnFastResponse}, TranslationBehaviour={self.TranslationBehaviour}, FreeTextMinimumCharacters={self.FreeTextMinimumCharacters}, NoShuffle={self.NoShuffle}, PlayVideoUntilTheEnd={self.PlayVideoUntilTheEnd}, AllowNeitherBoth={self.AllowNeitherBoth}, SwapContextInstruction={self.SwapContextInstruction}, MuteVideo={self.MuteVideo})"

    def __repr__(self) -> str:
        return self.__str__()
