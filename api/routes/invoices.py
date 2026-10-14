from __future__ import annotations

from fastapi import (
    APIRouter,
    HTTPException,
)
from fastapi.responses import Response

from api.core.errors import (
    audit_database_failure,
    audit_storage_failure,
    database_http_exception,
    storage_http_exception,
)
from api.models.invoice import InvoiceData
from api.models.invoice_status import InvoiceStatusUpdate
from api.services.audit_service import create_audit_log
from api.services.database_service import (
    DatabaseServiceError,
    get_all_invoices,
    get_invoice_by_id,
    update_invoice_status,
)
from api.services.invoice_validation_service import (
    validate_invoice_business_rules,
)
from api.services.make_service import send_make_event
from api.services.storage_service import (
    StorageServiceError,
    create_invoice_signed_url,
    download_invoice_pdf,
)
from api.services.supabase_client import (
    SupabaseConfigurationError,
)


router = APIRouter()

SIGNED_URL_EXPIRATION = 300  # 5 minutes


@router.get("/invoices")
def list_invoices():
    try:
        invoices = get_all_invoices()

    except (
        SupabaseConfigurationError,
        DatabaseServiceError,
    ) as exc:
        raise database_http_exception(exc)

    return {
        "count": len(invoices),
        "invoices": invoices,
    }


@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: int):
    try:
        invoice = get_invoice_by_id(
            invoice_id,
        )

    except (
        SupabaseConfigurationError,
        DatabaseServiceError,
    ) as exc:
        raise database_http_exception(exc)

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found.",
        )

    return invoice


@router.get("/invoices/{invoice_id}/pdf-url")
def get_invoice_pdf_url(invoice_id: int):
    try:
        invoice = get_invoice_by_id(
            invoice_id,
        )

    except (
        SupabaseConfigurationError,
        DatabaseServiceError,
    ) as exc:
        raise database_http_exception(exc)

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found.",
        )

    file_path = invoice.get(
        "file_path",
    )

    if not file_path:
        raise HTTPException(
            status_code=404,
            detail=(
                "Original invoice PDF is not available."
            ),
        )

    try:
        signed_url = create_invoice_signed_url(
            file_path=file_path,
            expires_in=SIGNED_URL_EXPIRATION,
        )

    except (
        SupabaseConfigurationError,
        StorageServiceError,
    ) as exc:
        audit_storage_failure(
            operation="create_signed_url",
            exc=exc,
            invoice_id=invoice_id,
            file_name=invoice.get(
                "file_name"
            ),
            file_hash=invoice.get(
                "file_hash"
            ),
            file_path=file_path,
        )

        raise storage_http_exception(
            exc
        )

    return {
        "invoice_id": invoice_id,
        "url": signed_url,
        "expires_in": SIGNED_URL_EXPIRATION,
    }


@router.get("/invoices/{invoice_id}/pdf")
def view_invoice_pdf(invoice_id: int):
    try:
        invoice = get_invoice_by_id(
            invoice_id,
        )

    except (
        SupabaseConfigurationError,
        DatabaseServiceError,
    ) as exc:
        raise database_http_exception(exc)

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found.",
        )

    file_path = invoice.get(
        "file_path",
    )

    if not file_path:
        raise HTTPException(
            status_code=404,
            detail=(
                "Original invoice PDF is not available."
            ),
        )

    try:
        pdf_content = download_invoice_pdf(
            file_path,
        )

    except (
        SupabaseConfigurationError,
        StorageServiceError,
    ) as exc:
        audit_storage_failure(
            operation="download_invoice_pdf",
            exc=exc,
            invoice_id=invoice_id,
            file_name=invoice.get(
                "file_name"
            ),
            file_hash=invoice.get(
                "file_hash"
            ),
            file_path=file_path,
        )

        raise storage_http_exception(
            exc
        )

    file_name = (
        invoice.get("file_name")
        or f"invoice_{invoice_id}.pdf"
    )

    safe_file_name = (
        file_name
        .replace('"', "")
        .replace("\r", "")
        .replace("\n", "")
    )

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'inline; filename="{safe_file_name}"'
            ),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.patch("/invoices/{invoice_id}/status")
def change_invoice_status(
    invoice_id: int,
    status_update: InvoiceStatusUpdate,
):
    try:
        invoice = get_invoice_by_id(
            invoice_id,
        )

    except (
        SupabaseConfigurationError,
        DatabaseServiceError,
    ) as exc:
        audit_database_failure(
            operation="get_invoice_by_id",
            exc=exc,
            invoice_id=invoice_id,
        )

        raise database_http_exception(
            exc
        )

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found.",
        )

    previous_status = invoice.get(
        "status",
    )

    try:
        updated_invoice = update_invoice_status(
            invoice_id,
            status_update.status,
        )

    except (
        SupabaseConfigurationError,
        DatabaseServiceError,
    ) as exc:
        audit_database_failure(
            operation="update_invoice_status",
            exc=exc,
            invoice_id=invoice_id,
            file_name=invoice.get(
                "file_name"
            ),
            file_hash=invoice.get(
                "file_hash"
            ),
        )

        raise database_http_exception(
            exc
        )

    if not updated_invoice:
        raise HTTPException(
            status_code=500,
            detail=(
                "The invoice status could not be updated. "
                "Please try again later."
            ),
        )

    create_audit_log(
        event_type=status_update.status,
        invoice_id=invoice_id,
        source="human_review",
        file_name=updated_invoice.get(
            "file_name"
        ),
        file_hash=updated_invoice.get(
            "file_hash"
        ),
        details={
            "previous_status": previous_status,
            "new_status": status_update.status,
        },
    )

    make_result = send_make_event(
        event_type="invoice_status_changed",
        invoice=updated_invoice,
    )

    create_audit_log(
        event_type=(
            "automation_dispatched"
            if make_result["dispatched"]
            else "automation_failed"
        ),
        invoice_id=invoice_id,
        source="automation",
        file_name=updated_invoice.get(
            "file_name"
        ),
        file_hash=updated_invoice.get(
            "file_hash"
        ),
        details={
            "provider": "make",
            "make_event": (
                "invoice_status_changed"
            ),
            "invoice_status": (
                status_update.status
            ),
            "dispatched": (
                make_result["dispatched"]
            ),
            "http_status": (
                make_result["status_code"]
            ),
            "error": make_result["error"],
        },
    )

    return {
        "message": (
            "Invoice status updated successfully."
        ),
        "invoice": updated_invoice,
        "automation_dispatched": (
            make_result["dispatched"]
        ),
    }


@router.post("/invoices/validate")
def validate_invoice(
    invoice: InvoiceData,
):
    validation_result = (
        validate_invoice_business_rules(
            invoice,
        )
    )

    return {
        "invoice": invoice,
        "validation": validation_result,
    }