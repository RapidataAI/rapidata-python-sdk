from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting

class CustomSetting(RapidataSetting):
    """
    Set a custom setting with the given key and value. Use this to enable features that do not have a dedicated method (yet)
    
    Args:
        key (str): The key for the custom setting.
        value (str): The value for the custom setting.
    """

    def __init__(self, key: str, value: str):
        if not isinstance(key, str):
            raise ValueError("The key must be a string.")
        
        super().__init__(key=key, value=value)
