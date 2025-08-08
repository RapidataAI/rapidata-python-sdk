from pydantic import BaseModel, Field


class _RapidataConfig(BaseModel):
    maxUploadWorkers: int = Field(default=10)
    uploadMaxRetries: int = Field(default=3)
    enableBetaFeatures: bool = False


rapidata_config = _RapidataConfig()
