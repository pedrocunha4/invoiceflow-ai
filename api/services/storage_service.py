import logging
from datetime import datetime, timezone

import httpx

from api.services.supabase_client import (
    SupabaseConfigurationError,
    get_supabase_client,
)


logger = logging.getLogger(__name__)

STORAGE_BUCKET = "invoice-documents"


# ---------------------------------------------------------------------------
# Storage exceptions
# ---------------------------------------------------------------------------

class StorageServiceError(Exception):
    """Base exception for Supabase Storage failures."""


class StorageUnavailableError(StorageServiceError):
    """Temporary connection or availability failure."""


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def _handle_storage_error(
    operation: str,
    exc: Exception
) -> None:

    if isinstance(
        exc,
        (
            httpx.TimeoutException,
            httpx.RequestError,
        )
    ):
        logger.warning(
            "Supabase Storage unavailable during %s: %s",
            operation,
            exc.__class__.__name__
        )

        raise StorageUnavailableError(
            "The document storage service is temporarily unavailable."
        ) from exc

    logger.error(
        "Supabase Storage operation failed during %s: %s",
        operation,
        exc.__class__.__name__
    )

    raise StorageServiceError(
        "The document storage operation failed."
    ) from exc


# ---------------------------------------------------------------------------
# File path
# ---------------------------------------------------------------------------

def build_invoice_file_path(
    supplier_vat_number: str,
    invoice_number: str,
    original_filename: str
) -> str:
    """
    Build a structured and unique storage path for an invoice PDF.
    """

    now = datetime.now(
        timezone.utc
    )

    safe_vat = (
        str(supplier_vat_number)
        .strip()
        .replace("/", "-")
    )

    safe_invoice_number = (
        str(invoice_number)
        .strip()
        .replace("/", "-")
        .replace("\\", "-")
        .replace(" ", "_")
    )

    filename = (
        f"{safe_invoice_number}__{original_filename}"
        .replace("/", "-")
        .replace("\\", "-")
    )

    return (
        f"{now.year}/"
        f"{now.month:02d}/"
        f"{safe_vat}/"
        f"{filename}"
    )


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def upload_invoice_pdf(
    file_path: str,
    content: bytes
) -> str:
    """
    Upload the original invoice PDF to the private
    Supabase Storage bucket.
    """

    try:
        supabase = get_supabase_client()

        supabase.storage.from_(
            STORAGE_BUCKET
        ).upload(
            path=file_path,
            file=content,
            file_options={
                "content-type": "application/pdf",
                "upsert": "false"
            }
        )

        return file_path

    except SupabaseConfigurationError:
        raise

    except Exception as exc:
        _handle_storage_error(
            "upload_invoice_pdf",
            exc
        )


# ---------------------------------------------------------------------------
# Signed URL
# ---------------------------------------------------------------------------

def create_invoice_signed_url(
    file_path: str,
    expires_in: int = 300
) -> str:
    """
    Create a temporary signed URL for a private invoice PDF.
    """

    try:
        supabase = get_supabase_client()

        response = (
            supabase.storage
            .from_(STORAGE_BUCKET)
            .create_signed_url(
                file_path,
                expires_in
            )
        )

    except SupabaseConfigurationError:
        raise

    except Exception as exc:
        _handle_storage_error(
            "create_invoice_signed_url",
            exc
        )

    if isinstance(response, dict):

        signed_url = (
            response.get("signedURL")
            or response.get("signedUrl")
            or response.get("signed_url")
        )

        if signed_url:
            return signed_url

    logger.error(
        "Supabase Storage returned no signed URL."
    )

    raise StorageServiceError(
        "Could not create a signed URL."
    )


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download_invoice_pdf(
    file_path: str
) -> bytes:
    """
    Download a private invoice PDF from Supabase Storage.
    """

    try:
        supabase = get_supabase_client()

        content = (
            supabase.storage
            .from_(STORAGE_BUCKET)
            .download(file_path)
        )

    except SupabaseConfigurationError:
        raise

    except Exception as exc:
        _handle_storage_error(
            "download_invoice_pdf",
            exc
        )

    if not content:
        logger.error(
            "Supabase Storage returned an empty PDF."
        )

        raise StorageServiceError(
            "The stored PDF could not be retrieved."
        )

    return content

def delete_invoice_pdf(
    file_path: str
) -> None:

    try:
        supabase = get_supabase_client()

        supabase.storage.from_(
            STORAGE_BUCKET
        ).remove([
            file_path
        ])

    except SupabaseConfigurationError:
        raise

    except Exception as exc:
        _handle_storage_error(
            "delete_invoice_pdf",
            exc
        )