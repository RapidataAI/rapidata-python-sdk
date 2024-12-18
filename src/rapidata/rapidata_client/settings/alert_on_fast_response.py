from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting

class AlertOnFastResponse(RapidataSetting):
    """
    Gives an alert as a pop up on the UI when the response time is less than the milliseconds.
    
    Args:
        threshold (int): if the user responds in less than this time, an alert will be shown.
    """
    
    def __init__(self, threshold: int):
        if not isinstance(threshold, int):
            raise ValueError("The alert must be an integer.")
        if threshold < 10:
            print(f"Warning: Are you sure you want to set the threshold so low ({threshold} milliseconds)?")
        if threshold > 25000:
            raise ValueError("The alert must be less than 25000 milliseconds.")
        if threshold < 0:
            raise ValueError("The alert must be greater than or equal to 0.")
    
        super().__init__(key="alert_on_fast_response", value=threshold)
