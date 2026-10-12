import hashlib

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from api.models.invoice import InvoiceData
from api.models.invoice_status import InvoiceStatusUpdate

from api.services.ai_service import (
    AIConfigurationError,
    AIResponseError,
    AIServiceError,
    AIServiceUnavailableError,
    extract_invoice_data,
)
from api.services.audit_service import create_audit_log
from api.services.make_service import send_make_event
from api.services.database_service import (
    DatabaseServiceError,
    DatabaseUnavailableError,
    find_invoice_by_hash,
    find_invoice_by_number,
    get_all_invoices,
    get_invoice_by_id,
    get_invoice_stats,
    save_invoice,
    update_invoice_status,
)
from api.services.invoice_validation_service import (
    validate_invoice_business_rules,
)
from api.services.pdf_service import extract_text_from_pdf
from api.services.storage_service import (
    StorageServiceError,
    StorageUnavailableError,
    build_invoice_file_path,
    upload_invoice_pdf,
    create_invoice_signed_url,
    download_invoice_pdf,
    delete_invoice_pdf,
)
from api.services.supabase_client import (
    SupabaseConfigurationError,
)


app = FastAPI(
    title="InvoiceFlow AI API",
    description="API for intelligent invoice processing and automation.",
    version="0.1.0",
    docs_url=None,
)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
SIGNED_URL_EXPIRATION = 300  # 5 minutes


# ---------------------------------------------------------
# Dependency error helpers
# ---------------------------------------------------------

def database_http_exception(
    exc: Exception,
) -> HTTPException:

    if isinstance(exc, DatabaseUnavailableError):
        return HTTPException(
            status_code=503,
            detail=(
                "The database service is temporarily unavailable. "
                "Please try again later."
            ),
        )

    if isinstance(exc, SupabaseConfigurationError):
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

    if isinstance(exc, StorageUnavailableError):
        return HTTPException(
            status_code=503,
            detail=(
                "The document storage service is temporarily unavailable. "
                "Please try again later."
            ),
        )

    if isinstance(exc, SupabaseConfigurationError):
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


# ---------------------------------------------------------
# Static files
# ---------------------------------------------------------

app.mount(
    "/icon",
    StaticFiles(directory="api/icon"),
    name="icon",
)


# ---------------------------------------------------------
# Custom Swagger UI
# ---------------------------------------------------------

@app.get("/docs", include_in_schema=False)
def custom_swagger_ui():

    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="InvoiceFlow AI API",
        swagger_favicon_url="/icon/favicon.png",
    )


# ---------------------------------------------------------
# General
# ---------------------------------------------------------

@app.get("/")
def root():

    return {
        "message": "InvoiceFlow AI API is running",
        "status": "ok",
    }


@app.get("/health")
def health_check():

    return {
        "status": "healthy",
    }


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------

@app.get("/dashboard/stats")
def dashboard_stats():

    try:
        return get_invoice_stats()

    except (
        SupabaseConfigurationError,
        DatabaseServiceError,
    ) as exc:
        raise database_http_exception(exc)


# ---------------------------------------------------------
# Invoice retrieval
# ---------------------------------------------------------

@app.get("/invoices")
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


@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: int):

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

    return invoice


# ---------------------------------------------------------
# Original invoice PDF
# ---------------------------------------------------------

@app.get("/invoices/{invoice_id}/pdf-url")
def get_invoice_pdf_url(invoice_id: int):

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
            file_name=invoice.get("file_name"),
            file_hash=invoice.get("file_hash"),
            file_path=file_path,
        )

        raise storage_http_exception(exc)

    return {
        "invoice_id": invoice_id,
        "url": signed_url,
        "expires_in": SIGNED_URL_EXPIRATION,
    }


@app.get("/invoices/{invoice_id}/pdf")
def view_invoice_pdf(invoice_id: int):

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


# ---------------------------------------------------------
# Invoice human review
# ---------------------------------------------------------

@app.patch("/invoices/{invoice_id}/status")
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

        raise database_http_exception(exc)

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
            file_name=invoice.get("file_name"),
            file_hash=invoice.get("file_hash"),
        )

        raise database_http_exception(exc)

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
        file_name=updated_invoice.get("file_name"),
        file_hash=updated_invoice.get("file_hash"),
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
        file_name=updated_invoice.get("file_name"),
        file_hash=updated_invoice.get("file_hash"),
        details={
            "provider": "make",
            "make_event": "invoice_status_changed",
            "invoice_status": status_update.status,
            "dispatched": make_result["dispatched"],
            "http_status": make_result["status_code"],
            "error": make_result["error"],
        },
    )

    return {
        "message": "Invoice status updated successfully.",
        "invoice": updated_invoice,
        "automation_dispatched": make_result["dispatched"],
    }


# ---------------------------------------------------------
# Invoice validation
# ---------------------------------------------------------

@app.post("/invoices/validate")
def validate_invoice(invoice: InvoiceData):

    validation_result = (
        validate_invoice_business_rules(
            invoice,
        )
    )

    return {
        "invoice": invoice,
        "validation": validation_result,
    }


# ---------------------------------------------------------
# AI invoice processing
# ---------------------------------------------------------

@app.post("/invoices/extract")
async def extract_invoice(
    file: UploadFile = File(...),
):

    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed.",
        )

    # Read file
    content = await file.read()

    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File is too large. Maximum size is 10 MB.",
        )

    file_name = (
        file.filename
        or "invoice.pdf"
    )

    # Generate SHA-256 fingerprint
    file_hash = hashlib.sha256(
        content,
    ).hexdigest()

    # Register received document
    create_audit_log(
        event_type="invoice_received",
        source="api",
        file_name=file_name,
        file_hash=file_hash,
        details={
            "content_type": file.content_type,
            "size_bytes": len(content),
        },
    )

    # -----------------------------------------------------
    # Duplicate check by file hash
    # -----------------------------------------------------

    try:
        existing_invoice = find_invoice_by_hash(
            file_hash,
        )

    except (
        SupabaseConfigurationError,
        DatabaseServiceError,
    ) as exc:

        audit_database_failure(
            operation="find_invoice_by_hash",
            exc=exc,
            file_name=file_name,
            file_hash=file_hash,
        )

        raise database_http_exception(exc)

    if existing_invoice:

        create_audit_log(
            event_type="duplicate_detected",
            invoice_id=existing_invoice["id"],
            source="api",
            file_name=file_name,
            file_hash=file_hash,
            details={
                "reason": "file_hash",
                "message": (
                    "This PDF has already been processed."
                ),
            },
        )

        raise HTTPException(
            status_code=409,
            detail={
                "status": "duplicate",
                "reason": "file_hash",
                "message": (
                    "This PDF has already been processed."
                ),
                "invoice_id": existing_invoice["id"],
            },
        )

    # -----------------------------------------------------
    # PDF extraction
    # -----------------------------------------------------

    extracted_text = extract_text_from_pdf(
        content,
    )

    if not extracted_text.strip():
        raise HTTPException(
            status_code=422,
            detail=(
                "No readable text was found in the PDF."
            ),
        )

    # -----------------------------------------------------
    # AI extraction
    # -----------------------------------------------------

    try:
        invoice = extract_invoice_data(
            extracted_text,
        )

    except ValidationError:

        create_audit_log(
            event_type="ai_processing_failed",
            source="ai",
            file_name=file_name,
            file_hash=file_hash,
            details={
                "error_type": "validation_error",
                "retryable": False,
            },
        )

        raise HTTPException(
            status_code=422,
            detail=(
                "The uploaded PDF does not contain a valid invoice "
                "or the required invoice fields could not be extracted."
            ),
        )

    except AIServiceUnavailableError:

        create_audit_log(
            event_type="ai_processing_failed",
            source="ai",
            file_name=file_name,
            file_hash=file_hash,
            details={
                "error_type": "service_unavailable",
                "retryable": True,
            },
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "The AI service is temporarily unavailable. "
                "Please try again later."
            ),
        )

    except AIConfigurationError:

        create_audit_log(
            event_type="ai_processing_failed",
            source="ai",
            file_name=file_name,
            file_hash=file_hash,
            details={
                "error_type": "configuration_error",
                "retryable": False,
            },
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "The AI service is currently unavailable. "
                "Please try again later."
            ),
        )

    except AIResponseError:

        create_audit_log(
            event_type="ai_processing_failed",
            source="ai",
            file_name=file_name,
            file_hash=file_hash,
            details={
                "error_type": "invalid_ai_response",
                "retryable": False,
            },
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "The AI service returned an invalid response. "
                "Please try again later."
            ),
        )

    except AIServiceError:

        create_audit_log(
            event_type="ai_processing_failed",
            source="ai",
            file_name=file_name,
            file_hash=file_hash,
            details={
                "error_type": "ai_service_error",
                "retryable": False,
            },
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "The invoice could not be processed by the AI service. "
                "Please try again later."
            ),
        )

    except Exception:

        create_audit_log(
            event_type="ai_processing_failed",
            source="ai",
            file_name=file_name,
            file_hash=file_hash,
            details={
                "error_type": "unexpected_error",
                "retryable": False,
            },
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "The invoice could not be processed due to an internal "
                "service error. Please try again later."
            ),
        )

    create_audit_log(
        event_type="ai_extracted",
        source="ai",
        file_name=file_name,
        file_hash=file_hash,
        details={
            "supplier_name": invoice.supplier_name,
            "supplier_vat_number": invoice.supplier_vat_number,
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date.isoformat(),
            "subtotal": invoice.subtotal,
            "vat_amount": invoice.vat_amount,
            "total": invoice.total,
            "currency": invoice.currency,
        },
    )

    # -----------------------------------------------------
    # Duplicate check by supplier + invoice number
    # -----------------------------------------------------

    try:
        existing_invoice = find_invoice_by_number(
            invoice.supplier_vat_number,
            invoice.invoice_number,
        )

    except (
        SupabaseConfigurationError,
        DatabaseServiceError,
    ) as exc:

        audit_database_failure(
            operation="find_invoice_by_number",
            exc=exc,
            file_name=file_name,
            file_hash=file_hash,
        )

        raise database_http_exception(exc)

    if existing_invoice:

        create_audit_log(
            event_type="duplicate_detected",
            invoice_id=existing_invoice["id"],
            source="api",
            file_name=file_name,
            file_hash=file_hash,
            details={
                "reason": "invoice_number",
                "supplier_vat_number":
                    invoice.supplier_vat_number,
                "invoice_number":
                    invoice.invoice_number,
                "message": (
                    "An invoice with this supplier and "
                    "invoice number already exists."
                ),
            },
        )

        raise HTTPException(
            status_code=409,
            detail={
                "status": "duplicate",
                "reason": "invoice_number",
                "message": (
                    "An invoice with this supplier and "
                    "invoice number already exists."
                ),
                "invoice_id": existing_invoice["id"],
            },
        )

    # -----------------------------------------------------
    # Business validation
    # -----------------------------------------------------

    validation_result = (
        validate_invoice_business_rules(
            invoice,
        )
    )

    create_audit_log(
        event_type="validation_completed",
        source="validation",
        file_name=file_name,
        file_hash=file_hash,
        details={
            "is_valid":
                validation_result["is_valid"],
            "status":
                validation_result["status"],
            "errors":
                validation_result["errors"],
        },
    )

    # -----------------------------------------------------
    # Document Storage
    # -----------------------------------------------------

    file_path = build_invoice_file_path(
        supplier_vat_number=(
            invoice.supplier_vat_number
        ),
        invoice_number=(
            invoice.invoice_number
        ),
        original_filename=file_name,
    )

    try:
        stored_file_path = upload_invoice_pdf(
            file_path=file_path,
            content=content,
        )

    except (
        SupabaseConfigurationError,
        StorageServiceError,
    ) as exc:

        audit_storage_failure(
            operation="upload_invoice_pdf",
            exc=exc,
            file_name=file_name,
            file_hash=file_hash,
            file_path=file_path,
        )

        raise storage_http_exception(exc)

    # -----------------------------------------------------
    # Save invoice in database
    # -----------------------------------------------------

    try:
        saved_invoice = save_invoice(
            file_name=file_name,
            file_hash=file_hash,
            invoice=invoice,
            validation=validation_result,
            file_path=stored_file_path,
        )

    except (
        SupabaseConfigurationError,
        DatabaseServiceError,
    ) as exc:

        # Compensating action:
        # if the PDF was already uploaded but the database
        # insert fails, remove the PDF to avoid an orphan file.
        try:
            delete_invoice_pdf(
                stored_file_path,
            )

        except (
            SupabaseConfigurationError,
            StorageServiceError,
        ):
            # Do not hide the original database failure.
            # The storage service already logs its own failure.
            pass

        audit_database_failure(
            operation="save_invoice",
            exc=exc,
            file_name=file_name,
            file_hash=file_hash,
        )

        raise database_http_exception(exc)

    # -----------------------------------------------------
    # Audit successful document storage
    # -----------------------------------------------------

    create_audit_log(
        event_type="document_stored",
        invoice_id=saved_invoice["id"],
        source="storage",
        file_name=file_name,
        file_hash=file_hash,
        details={
            "bucket": "invoice-documents",
            "file_path": stored_file_path,
            "content_type": "application/pdf",
            "size_bytes": len(content),
        },
    )

    # -----------------------------------------------------
    # Audit invoice creation
    # -----------------------------------------------------

    create_audit_log(
        event_type="invoice_created",
        invoice_id=saved_invoice["id"],
        source="api",
        file_name=file_name,
        file_hash=file_hash,
        details={
            "status":
                saved_invoice["status"],
            "supplier_name":
                saved_invoice["supplier_name"],
            "supplier_vat_number":
                saved_invoice["supplier_vat_number"],
            "invoice_number":
                saved_invoice["invoice_number"],
            "total":
                saved_invoice["total"],
            "currency":
                saved_invoice["currency"],
            "file_path":
                saved_invoice.get("file_path"),
        },
    )

    # -----------------------------------------------------
    # Make automation
    # -----------------------------------------------------

    make_result = send_make_event(
        event_type="invoice_processed",
        invoice=saved_invoice,
    )

    create_audit_log(
        event_type=(
            "automation_dispatched"
            if make_result["dispatched"]
            else "automation_failed"
        ),
        invoice_id=saved_invoice["id"],
        source="automation",
        file_name=file_name,
        file_hash=file_hash,
        details={
            "provider": "make",
            "make_event": "invoice_processed",
            "invoice_status":
                saved_invoice["status"],
            "dispatched":
                make_result["dispatched"],
            "http_status":
                make_result["status_code"],
            "error":
                make_result["error"],
        },
    )

    return {
        "status": "processed",
        "database_id": saved_invoice["id"],
        "filename": file_name,
        "sha256": file_hash,
        "invoice": invoice.model_dump(
            mode="json",
        ),
        "validation": validation_result,
        "file_path": stored_file_path,
        "automation_dispatched":
            make_result["dispatched"],
    }


# ---------------------------------------------------------
# Raw PDF upload / extraction test
# ---------------------------------------------------------

@app.post("/invoices/upload")
async def upload_invoice(
    file: UploadFile = File(...),
):

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed.",
        )

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File is too large. Maximum size is 10 MB.",
        )

    file_name = (
        file.filename
        or "invoice.pdf"
    )

    file_hash = hashlib.sha256(
        content,
    ).hexdigest()

    extracted_text = extract_text_from_pdf(
        content,
    )

    return {
        "status": "received",
        "filename": file_name,
        "content_type": file.content_type,
        "size_bytes": len(content),
        "sha256": file_hash,
        "text_extracted": bool(extracted_text),
        "text_preview": extracted_text[:500],
    }