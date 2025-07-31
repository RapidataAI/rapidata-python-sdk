class _RapidataConfig:
    def __init__(self):
        self.__maxUploadWorkers: int = 10
        self.__uploadMaxRetries: int = 3

    @property
    def max_upload_workers(self) -> int:
        return self.__maxUploadWorkers

    @max_upload_workers.setter
    def max_upload_workers(self, value: int) -> None:
        if value < 1:
            raise ValueError("max_upload_workers must be greater than 0")
        self.__maxUploadWorkers = value

    @property
    def upload_max_retries(self) -> int:
        return self.__uploadMaxRetries

    @upload_max_retries.setter
    def upload_max_retries(self, value: int) -> None:
        if value < 1:
            raise ValueError("upload_max_retries must be greater than 0")
        self.__uploadMaxRetries = value

    def __str__(self) -> str:
        return f"RapidataConfig(max_upload_workers={self.__maxUploadWorkers}, upload_max_retries={self.__uploadMaxRetries})"

    def __repr__(self) -> str:
        return self.__str__()


rapidata_config = _RapidataConfig()
