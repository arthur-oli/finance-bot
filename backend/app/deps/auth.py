import hmac
import os
from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(_header)) -> str:
    secret = os.environ.get("API_SECRET_KEY", "")
    if not api_key or not hmac.compare_digest(api_key.encode(), secret.encode()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")
    return api_key
