from pydantic import BaseModel, Field


class RapidataConfig(BaseModel):
    """
    Holds the configuration for the Rapidata client.

    To adjust the configurations used, you can modify the `rapidata_config` object.

    Args:
        maxUploadWorkers (int): The maximum number of worker threads for processing media paths. Defaults to 10.
        uploadMaxRetries (int): The maximum number of retries for failed uploads. Defaults to 3.
        enableBetaFeatures (bool): Whether to enable beta features. Defaults to False.
        minOrderDatapointsForValidation (int): The minimum number of datapoints required so that an automatic validationset gets created if no recommended was found. Defaults to 50.
        autoValidationSetSize (int): The maximum size of the auto-generated validation set. Defaults to 20.

    Example:
        ```python
        from rapidata import rapidata_config
        rapidata_config.maxUploadWorkers = 20
        ```
    """

    maxUploadWorkers: int = Field(default=10)
    uploadMaxRetries: int = Field(default=3)
    enableBetaFeatures: bool = False
    minOrderDatapointsForValidation: int = Field(default=50)
    autoValidationSetSize: int = Field(default=20)


rapidata_config = RapidataConfig()
