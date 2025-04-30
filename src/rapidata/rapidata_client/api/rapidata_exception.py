from typing import Optional, Any
from rapidata.api_client.api_client import ApiClient, rest, ApiResponse, ApiResponseT
from rapidata.api_client.exceptions import ApiException
import json
from rapidata.rapidata_client.logging import logger

class RapidataError(Exception):
    """Custom error class for Rapidata API errors."""
    
    def __init__(
        self, 
        status_code: Optional[int] = None, 
        message: str | None = None, 
        original_exception: Exception | None = None,
        details: Any = None
    ):
        self.status_code = status_code
        self.message = message
        self.original_exception = original_exception
        self.details = details
        
        # Create a nice error message
        error_msg = "Rapidata API Error"
        if status_code:
            error_msg += f" ({status_code})"
        if message:
            error_msg += f": {message}"
            
        super().__init__(error_msg)

    def __str__(self):
        """Return a string representation of the error."""        
        # Extract information from message if available
        title = None
        errors = None
        trace_id = None
        
        # Try to extract from details if available and is a dict
        if self.details and isinstance(self.details, dict):
            title = self.details.get('title')
            errors = self.details.get('errors')
            trace_id = self.details.get('traceId')
        
        # Build the error string
        error_parts = []
        
        # Main error line
        if title:
            error_parts.append(f"{title}")
        else:
            error_parts.append(f"{self.message or 'Unknown error'}")
        
        # Reasons
        if errors:
            if isinstance(errors, dict):
                error_parts.append(f"Reasons: {json.dumps({'errors': errors})}")
            else:
                error_parts.append(f"Reasons: {errors}")
        
        # Trace ID
        if trace_id:
            error_parts.append(f"Trace Id: {trace_id}")
        else:
            error_parts.append("Trace Id: N/A")
        
        return "\n".join(error_parts)

class RapidataApiClient(ApiClient):
    """Custom API client that wraps errors in RapidataError."""

    def response_deserialize(
        self,
        response_data: rest.RESTResponse,
        response_types_map: Optional[dict[str, ApiResponseT]] = None
    ) -> ApiResponse[ApiResponseT]:
        """Override the response_deserialize method to catch and convert exceptions."""
        try:
            return super().response_deserialize(response_data, response_types_map)
        except ApiException as e:
            status_code = getattr(e, 'status', None)
            message = str(e)
            details = None
            
            # Extract more detailed error message from response body if available
            if hasattr(e, 'body') and e.body:
                try:
                    body_json = json.loads(e.body)
                    if isinstance(body_json, dict):
                        if 'message' in body_json:
                            message = body_json['message']
                        elif 'error' in body_json:
                            message = body_json['error']
                        
                        # Store the full error details for debugging
                        details = body_json
                except (json.JSONDecodeError, AttributeError):
                    # If we can't parse the body as JSON, use the original message
                    pass
            
            error_formatted =  RapidataError(
                status_code=status_code, 
                message=message, 
                original_exception=e,
                details=details
            )
            logger.error(f"Error: {error_formatted}")
            raise error_formatted from None
