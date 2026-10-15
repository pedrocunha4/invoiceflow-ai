from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

from dotenv import load_dotenv

load_dotenv()


PDF_ACCESS_TTL_SECONDS = 300


class PdfAccessTokenError(Exception):
    """Raised when a PDF access token is invalid or expired."""


def _encode_base64(data: bytes) -> str:
    return (
        base64.urlsafe_b64encode(data)
        .decode("ascii")
        .rstrip("=")
    )


def _decode_base64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)

    return base64.urlsafe_b64decode(
        value + padding
    )


def _get_secret() -> bytes:
    secret = os.getenv(
        "INVOICEFLOW_PDF_TOKEN_SECRET"
    )

    if not secret:
        raise RuntimeError(
            "PDF token secret is not configured."
        )

    return secret.encode("utf-8")


def create_pdf_access_token(
    invoice_id: int,
    ttl_seconds: int = PDF_ACCESS_TTL_SECONDS,
) -> str:
    payload = {
        "invoice_id": invoice_id,
        "exp": int(time.time()) + ttl_seconds,
    }

    payload_bytes = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    encoded_payload = _encode_base64(
        payload_bytes
    )

    signature = hmac.new(
        _get_secret(),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()

    encoded_signature = _encode_base64(
        signature
    )

    return (
        f"{encoded_payload}."
        f"{encoded_signature}"
    )


def validate_pdf_access_token(
    token: str,
    invoice_id: int,
) -> None:
    try:
        encoded_payload, encoded_signature = (
            token.split(".", 1)
        )

        expected_signature = hmac.new(
            _get_secret(),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()

        received_signature = _decode_base64(
            encoded_signature
        )

        if not hmac.compare_digest(
            expected_signature,
            received_signature,
        ):
            raise PdfAccessTokenError

        payload = json.loads(
            _decode_base64(
                encoded_payload
            ).decode("utf-8")
        )

        if int(payload["invoice_id"]) != invoice_id:
            raise PdfAccessTokenError

        if int(payload["exp"]) < int(time.time()):
            raise PdfAccessTokenError

    except (
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        PdfAccessTokenError,
    ) as exc:
        raise PdfAccessTokenError(
            "Invalid or expired PDF access token."
        ) from exc