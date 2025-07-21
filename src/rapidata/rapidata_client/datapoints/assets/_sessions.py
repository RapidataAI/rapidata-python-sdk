import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class SessionManager:
    _session = None
    
    @classmethod
    def get_session(cls, ) -> requests.Session:
        """Get a singleton requests session with retry logic.

        Returns:
            requests.Session: A singleton requests session with retry logic.
        """
        if cls._session is None:
            max_retries: int = 5 
            max_workers: int = 10
            cls._session = requests.Session()
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
            cls._session.mount('http://', adapter)
            cls._session.mount('https://', adapter)

        return cls._session
