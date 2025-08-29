from pydantic import BaseModel, Field


class UploadConfig(BaseModel):
    """
    Holds the configuration for the upload process.

    Attributes:
        maxWorkers (int): The maximum number of worker threads for processing media paths. Defaults to 10.
        maxRetries (int): The maximum number of retries for failed uploads. Defaults to 3.
    """

    maxWorkers: int = Field(default=10)
    maxRetries: int = Field(default=3)
    chunkSize: int = Field(default=50)
