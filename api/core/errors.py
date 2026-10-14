from __future__ import annotations

from fastapi import HTTPException

from api.services.audit_service import create_audit_log
from api.services.database_service import (
    DatabaseUnavailableError,
)
from api.services.storage_service import (
    StorageUnavailableError,
)
from api.services.supabase_client import (
    SupabaseConfigurationError,
)


def database_http_exception(
    exc: Exception,
) -> HTTPException:
    """Convert database service errors into HTTP responses."""

    if isinstance(
        exc,
        DatabaseUnavailableError,
    ):
        return HTTPException(
            status_code=503,
            detail=(
                "The database service is temporarily unavailable. "
                "Please try again later."
            ),
        )

    if isinstance(
        exc,
        SupabaseConfigurationError,
    ):
        return HTTPException(
            status_code=500,
            detail=(
                "The database service is currently unavailable. "
                "Please try again later."
            ),
        )

    return HTTPException(
        status_code=502,
        detail=(
            "The database operation could not be completed. "
            "Please try again later."
        ),
    )


def storage_http_exception(
    exc: Exception,
) -> HTTPException:
    """Convert document-storage errors into HTTP responses."""

    if isinstance(
        exc,
        StorageUnavailableError,
    ):
        return HTTPException(
            status_code=503,
            detail=(
                "The document storage service is temporarily unavailable. "
                "Please try again later."
            ),
        )

    if isinstance(
        exc,
        SupabaseConfigurationError,
    ):
        return HTTPException(
            status_code=500,
            detail=(
                "The document storage service is currently unavailable. "
                "Please try again later."
            ),
        )

    return HTTPException(
        status_code=502,
        detail=(
            "The document storage operation could not be completed. "
            "Please try again later."
        ),
    )


def audit_database_failure(
    operation: str,
    exc: Exception,
    invoice_id: int | None = None,
    file_name: str | None = None,
    file_hash: str | None = None,
) -> None:
    """Record a database operation failure in the audit log."""

    create_audit_log(
        event_type="database_operation_failed",
        invoice_id=invoice_id,
        source="database",
        file_name=file_name,
        file_hash=file_hash,
        details={
            "operation": operation,
            "error_type": exc.__class__.__name__,
            "retryable": isinstance(
                exc,
                DatabaseUnavailableError,
            ),
        },
    )


def audit_storage_failure(
    operation: str,
    exc: Exception,
    invoice_id: int | None = None,
    file_name: str | None = None,
    file_hash: str | None = None,
    file_path: str | None = None,
) -> None:
    """Record a document-storage failure in the audit log."""

    create_audit_log(
        event_type="document_storage_failed",
        invoice_id=invoice_id,
        source="storage",
        file_name=file_name,
        file_hash=file_hash,
        details={
            "operation": operation,
            "error_type": exc.__class__.__name__,
            "retryable": isinstance(
                exc,
                StorageUnavailableError,
            ),
            "bucket": "invoice-documents",
            "file_path": file_path,
        },
    )