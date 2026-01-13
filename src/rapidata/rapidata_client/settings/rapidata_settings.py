from rapidata.rapidata_client.settings import (
    AlertOnFastResponse,
    TranslationBehaviour,
    FreeTextMinimumCharacters,
    NoShuffle,
    PlayVideoUntilTheEnd,
    AllowNeitherBoth,
    SwapContextInstruction,
    MuteVideo,
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
        swap_context_instruction (SwapContextInstruction): Swap the place of the context and instruction.
        mute_video (MuteVideo): Mute the video.

    Example:
        ```python
        from rapidata import FreeTextMinimumCharacters
        settings=[FreeTextMinimumCharacters(10)]
        ```

        This can be used in a free text order to set the minimum number of characters required to submit the task.
    """

    Alert_on_fast_response = AlertOnFastResponse
    Translation_behaviour = TranslationBehaviour
    Free_text_minimum_characters = FreeTextMinimumCharacters
    No_shuffle = NoShuffle
    Play_video_until_the_end = PlayVideoUntilTheEnd
    Allow_neither_both = AllowNeitherBoth
    Swap_context_instruction = SwapContextInstruction
    Mute_video = MuteVideo

    def __str__(self) -> str:
        return f"RapidataSettings(Alert_on_fast_response={self.Alert_on_fast_response}, Translation_behaviour={self.Translation_behaviour}, Free_text_minimum_characters={self.Free_text_minimum_characters}, No_shuffle={self.No_shuffle}, Play_video_until_the_end={self.Play_video_until_the_end}, Allow_neither_both={self.Allow_neither_both}, Swap_context_instruction={self.Swap_context_instruction}, Mute_video={self.Mute_video})"

    def __repr__(self) -> str:
        return self.__str__()
