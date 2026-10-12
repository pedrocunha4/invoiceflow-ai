from datetime import datetime, timezone
from typing import Optional

from api.services.database_service import supabase


STORAGE_BUCKET = "invoice-documents"


def build_invoice_file_path(
    supplier_vat_number: str,
    invoice_number: str,
    original_filename: str
) -> str:
    """
    Build a structured and unique storage path for an invoice PDF.
    """

    now = datetime.now(timezone.utc)

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


def upload_invoice_pdf(
    file_path: str,
    content: bytes
) -> Optional[str]:
    """
    Upload the original invoice PDF to the private
    Supabase Storage bucket.

    Returns the stored file path when successful.
    Returns None when the upload fails.
    """

    try:
        supabase.storage.from_(STORAGE_BUCKET).upload(
            path=file_path,
            file=content,
            file_options={
                "content-type": "application/pdf",
                "upsert": "false"
            }
        )

        return file_path

    except Exception:
        return None


def create_invoice_signed_url(
    file_path: str,
    expires_in: int = 300
) -> Optional[str]:
    """
    Create a temporary signed URL for a private invoice PDF.

    Default expiration: 5 minutes.
    """

    try:
        response = (
            supabase.storage
            .from_(STORAGE_BUCKET)
            .create_signed_url(
                file_path,
                expires_in
            )
        )

        if isinstance(response, dict):
            return (
                response.get("signedURL")
                or response.get("signedUrl")
                or response.get("signed_url")
            )

        return None

    except Exception:
        return None


def download_invoice_pdf(
    file_path: str
) -> Optional[bytes]:
    """
    Download a private invoice PDF from Supabase Storage.

    Returns the PDF bytes when successful.
    Returns None when the file cannot be downloaded.
    """

    try:
        content = (
            supabase.storage
            .from_(STORAGE_BUCKET)
            .download(file_path)
        )

        return content

    except Exception:
        return None