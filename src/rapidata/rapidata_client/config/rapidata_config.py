from pydantic import BaseModel, Field

from rapidata.rapidata_client.config.logging_config import LoggingConfig
from rapidata.rapidata_client.config.order_config import OrderConfig
from rapidata.rapidata_client.config.upload_config import UploadConfig


class RapidataConfig(BaseModel):
    """
    Holds the configuration for the Rapidata client.

    To adjust the configurations used, you can modify the `rapidata_config` object.

    Attributes:
        enableBetaFeatures (bool): Whether to enable beta features. Defaults to False.
        upload (UploadConfig): The configuration for the upload process.
            Such as the maximum number of worker threads for processing media paths and the maximum number of retries for failed uploads.
        order (OrderConfig): The configuration for the order process.
            Such as the minimum number of datapoints required so that an automatic validationset gets created if no recommended was found.
        logging (LoggingConfig): The configuration for the logging process.
            Such as the logging level and the logging file.

    Example:
        ```python
        from rapidata import rapidata_config
        rapidata_config.upload.maxUploadWorkers = 20
        ```
    """

    enableBetaFeatures: bool = False
    upload: UploadConfig = Field(default_factory=UploadConfig)
    order: OrderConfig = Field(default_factory=OrderConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


rapidata_config = RapidataConfig()
