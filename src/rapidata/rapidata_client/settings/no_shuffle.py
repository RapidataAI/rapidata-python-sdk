from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting

class NoShuffle(RapidataSetting):
    """
    Only for classify tasks. If true, the order of the categories will be the same.

    If this is not added to the order, it shuffling will be active.
    
    Args:
        value (bool, optional): Whether to disable shuffling. Defaults to True for function call.
    """
    def __init__(self, value: bool = True):
        if not isinstance(value, bool):
            raise ValueError("The value must be a boolean.")
        
        super().__init__(key="no_shuffle", value=value)
