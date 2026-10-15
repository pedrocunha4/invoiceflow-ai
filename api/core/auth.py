from __future__ import annotations

import os
import secrets

from dotenv import load_dotenv
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

load_dotenv()


API_KEY_HEADER = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)


def require_api_key(
    api_key: str | None = Security(API_KEY_HEADER),
) -> None:
    """Validate the internal API key used by trusted clients."""

    expected_api_key = os.getenv(
        "INVOICEFLOW_API_KEY"
    )

    if not expected_api_key:
        raise HTTPException(
            status_code=500,
            detail=(
                "API authentication is not configured."
            ),
        )

    if (
        api_key is None
        or not secrets.compare_digest(
            api_key,
            expected_api_key,
        )
    ):
        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid or missing API key."
            ),
        )