from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting


class SwapContextInstruction(RapidataSetting):
    """
    Swap the place of the context and instruction.

    If set to true, the instruction will be shown on top and the context below. if collapsed, only the instruction will be shown.

    By default, the context will be shown on top and the instruction below.

    Args:
        value (bool): Whether to swap the place of the context and instruction.
    """

    def __init__(self, value: bool = True):
        if not isinstance(value, bool):
            raise ValueError("The value must be a boolean.")

        super().__init__(key="swap_question_and_prompt", value=value)
