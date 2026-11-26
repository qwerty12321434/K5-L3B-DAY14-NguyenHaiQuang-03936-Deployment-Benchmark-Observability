"""API key authentication for protected routes."""
from hmac import compare_digest
from typing import Annotated

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from .config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: Annotated[str | None, Security(api_key_header)]) -> str:
    expected_key = settings.agent_api_key
    if not api_key or not expected_key or not compare_digest(api_key.encode(), expected_key.encode()):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")
    return api_key
