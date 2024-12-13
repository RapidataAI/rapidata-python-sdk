from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting

class FreeTextMinimumCharacters(RapidataSetting):

    def __init__(self, value: int):
        """Set the minimum number of characters a user has to type.
        
        Args:
            value (int): The minimum number of characters for free text."""
        
        if value < 0:
            raise ValueError("The minimum number of characters must be greater than or equal to 0.")
        if value > 20:
            print(f"Warning: Are you sure you want to set the minimum number of characters at {value}?")
        super().__init__(key="free_text_minimum_characters", value=value)
