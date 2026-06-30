"""API key authentication dependency."""

import os

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("API_KEY", "dev-key")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(key: str | None = Security(api_key_header)) -> str:
    """Raise HTTP 403 if the key is missing or invalid."""
    if not key or key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing or invalid API key",
        )
    return key
