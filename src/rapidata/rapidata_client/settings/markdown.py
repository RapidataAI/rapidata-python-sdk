from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting


class Markdown(RapidataSetting):
    """
    Enable markdown rendering for text assets. Defaults to True.

    Args:
        value (bool): Whether to enable markdown rendering for text assets.
    """

    def __init__(self, value: bool = True):
        if not isinstance(value, bool):
            raise ValueError("The value must be a boolean.")
        super().__init__(key="use_text_asset_markdown", value=value)
