"""API key authentication dependency."""

import os

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

API_KEY = os.getenv("API_KEY", "")


async def verify_api_key(key: str | None = Security(api_key_header)) -> str:
    """
    Validate the ``X-API-Key`` header against the configured ``API_KEY``.

    Raises:
        HTTPException: 403 when the key is missing or invalid.
    """
    if not key or key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key",
        )
    return key
