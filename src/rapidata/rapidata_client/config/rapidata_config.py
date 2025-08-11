from pydantic import BaseModel, Field


class RapidataConfig(BaseModel):
    """
    Holds the configuration for the Rapidata client.

    To adjust the configurations used, you can modify the `rapidata_config` object.
    For example:
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
