from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting

class AllowNeitherBoth(RapidataSetting):
    """
    Set whether to allow neither or both options.
    This setting only works for compare orders.

    Args:
        value (bool): Whether to allow neither or both options. Defaults to True.
            If this setting is not added to an order, the users won't be able to select neither or both.
    """

    def __init__(self, value: bool = True):
        super().__init__(key="compare_unsure", value=value)
