from pydantic import BaseModel, Field


class UploadConfig(BaseModel):
    """
    Holds the configuration for the upload process.

    Args:
        maxUploadWorkers (int): The maximum number of worker threads for processing media paths. Defaults to 10.
        uploadMaxRetries (int): The maximum number of retries for failed uploads. Defaults to 3.
    """

    maxUploadWorkers: int = Field(default=10)
    uploadMaxRetries: int = Field(default=3)
