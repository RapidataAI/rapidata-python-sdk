from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting

class PlayVideoUntilTheEnd(RapidataSetting):
    """
    Allows users to only answer once the video has finished playing.
    The additional time gets added on top of the video duration. Can be negative to allow answers before the video ends.
    
    Args:
        additional_time (int, optional): Additional time in milliseconds. Defaults to 0.
    """
    
    def __init__(self, additional_time: int = 0):
        if additional_time < -25000 or additional_time > 25000:
            raise ValueError("The additional time must be between -25000 and 25000.")
        
        super().__init__(key="alert_on_fast_response_add_media_duration", value=additional_time)
