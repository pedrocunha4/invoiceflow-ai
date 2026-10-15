from __future__ import annotations

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Request,
)
from fastapi.responses import RedirectResponse, Response

from api.core.auth import require_api_key
from api.core.errors import (
    audit_database_failure,
    audit_storage_failure,
    database_http_exception,
    storage_http_exception,
)
from api.core.pdf_access import (
    PDF_ACCESS_TTL_SECONDS,
    PdfAccessTokenError,
    create_pdf_access_token,
    validate_pdf_access_token,
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
    download_invoice_pdf,
)
from api.services.supabase_client import (
    SupabaseConfigurationError,
)

router = APIRouter(
    dependencies=[
        Depends(require_api_key),
    ],
)

pdf_view_router = APIRouter()


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
def get_invoice_pdf_url(
    invoice_id: int,
    request: Request,
):
    try:
        invoice = get_invoice_by_id(invoice_id)
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

    file_path = invoice.get("file_path")

    if not file_path:
        raise HTTPException(
            status_code=404,
            detail="Original invoice PDF is not available.",
        )

    try:
        token = create_pdf_access_token(
            invoice_id=invoice_id,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail="PDF access is not configured.",
        ) from exc

    pdf_open_url = request.url_for(
        "open_invoice_pdf_with_token",
        invoice_id=str(invoice_id),
    )

    return {
        "invoice_id": invoice_id,
        "url": f"{pdf_open_url}?token={token}",
        "expires_in": PDF_ACCESS_TTL_SECONDS,
    }


@pdf_view_router.get(
    "/invoices/{invoice_id}/pdf-open",
    include_in_schema=False,
    name="open_invoice_pdf_with_token",
)
def open_invoice_pdf_with_token(
    invoice_id: int,
    token: str,
    request: Request,
):
    try:
        validate_pdf_access_token(
            token=token,
            invoice_id=invoice_id,
        )
    except PdfAccessTokenError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired PDF access token.",
        ) from exc

    pdf_view_url = request.url_for(
        "view_invoice_pdf_with_cookie",
        invoice_id=str(invoice_id),
    )

    response = RedirectResponse(
        url=str(pdf_view_url),
        status_code=303,
    )

    response.set_cookie(
        key="invoiceflow_pdf_access",
        value=token,
        max_age=PDF_ACCESS_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        path=f"/invoices/{invoice_id}/pdf-view",
    )

    return response

@pdf_view_router.get(
    "/invoices/{invoice_id}/pdf-view",
    include_in_schema=False,
    name="view_invoice_pdf_with_cookie",
)
def view_invoice_pdf_with_cookie(
    invoice_id: int,
    pdf_access_token: str | None = Cookie(
        default=None,
        alias="invoiceflow_pdf_access",
    ),
):
    if not pdf_access_token:
        raise HTTPException(
            status_code=401,
            detail="Missing PDF access token.",
        )

    try:
        validate_pdf_access_token(
            token=pdf_access_token,
            invoice_id=invoice_id,
        )
    except PdfAccessTokenError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired PDF access token.",
        ) from exc

    try:
        invoice = get_invoice_by_id(invoice_id)
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

    file_path = invoice.get("file_path")

    if not file_path:
        raise HTTPException(
            status_code=404,
            detail="Original invoice PDF is not available.",
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
            file_name=invoice.get("file_name"),
            file_hash=invoice.get("file_hash"),
            file_path=file_path,
        )

        raise storage_http_exception(exc)

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