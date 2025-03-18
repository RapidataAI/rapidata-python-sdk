from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.assets import MediaAsset
from rapidata.api_client.models.create_demographic_rapid_model import CreateDemographicRapidModel
from rapidata.api_client.models.classify_payload import ClassifyPayload
import requests
from requests.adapters import HTTPAdapter, Retry


class DemographicManager:
    def __init__(self, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
    
    def create_demographic_rapid(self, 
                                 instruction: str,
                                 answer_options: list[str],
                                 datapoint: str,
                                 key: str):
        
        media = MediaAsset(path=datapoint)
        model = CreateDemographicRapidModel(
            key=key,
            payload=ClassifyPayload(
                _t="ClassifyPayload",
                possibleCategories=answer_options,
                title=instruction
            )
        )
        session = self._get_session()
        media.session = session
        
        self._openapi_service.rapid_api.rapid_demographic_post(model=model, file=[media.to_file()])

    def _get_session(self, max_retries: int = 5, max_workers: int = 10) -> requests.Session:   
        """Get a requests session with retry logic.


        Args:
            max_retries (int): The maximum number of retries.
            max_workers (int): The maximum number of workers.

        Returns:
            requests.Session: A requests session with retry logic.
        """
        session = requests.Session()
        retries = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
            respect_retry_after_header=True
        )

        adapter = HTTPAdapter(
            pool_connections=max_workers * 2,
            pool_maxsize=max_workers * 4,
            max_retries=retries
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        return session
        