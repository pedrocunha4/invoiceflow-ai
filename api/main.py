import hashlib

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from api.models.invoice import InvoiceData
from api.models.invoice_status import InvoiceStatusUpdate

from api.services.ai_service import extract_invoice_data
from api.services.audit_service import create_audit_log
from api.services.make_service import send_make_event
from api.services.database_service import (
    find_invoice_by_hash,
    find_invoice_by_number,
    get_all_invoices,
    get_invoice_by_id,
    get_invoice_stats,
    save_invoice,
    update_invoice_status
)
from api.services.invoice_validation_service import (
    validate_invoice_business_rules
)
from api.services.pdf_service import extract_text_from_pdf
from api.services.storage_service import (
    build_invoice_file_path,
    upload_invoice_pdf,
    create_invoice_signed_url,
    download_invoice_pdf
)


app = FastAPI(
    title="InvoiceFlow AI API",
    description="API for intelligent invoice processing and automation.",
    version="0.1.0",
    docs_url=None
)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
SIGNED_URL_EXPIRATION = 300  # 5 minutes


# ---------------------------------------------------------
# Static files
# ---------------------------------------------------------

app.mount(
    "/icon",
    StaticFiles(directory="api/icon"),
    name="icon"
)


# ---------------------------------------------------------
# Custom Swagger UI
# ---------------------------------------------------------

@app.get("/docs", include_in_schema=False)
def custom_swagger_ui():

    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="InvoiceFlow AI API",
        swagger_favicon_url="/icon/favicon.png"
    )


# ---------------------------------------------------------
# General
# ---------------------------------------------------------

@app.get("/")
def root():

    return {
        "message": "InvoiceFlow AI API is running",
        "status": "ok"
    }


@app.get("/health")
def health_check():

    return {
        "status": "healthy"
    }


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------

@app.get("/dashboard/stats")
def dashboard_stats():

    stats = get_invoice_stats()

    return stats


# ---------------------------------------------------------
# Invoice retrieval
# ---------------------------------------------------------

@app.get("/invoices")
def list_invoices():

    invoices = get_all_invoices()

    return {
        "count": len(invoices),
        "invoices": invoices
    }


@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: int):

    invoice = get_invoice_by_id(invoice_id)

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found."
        )

    return invoice


# ---------------------------------------------------------
# Original invoice PDF
# ---------------------------------------------------------

@app.get("/invoices/{invoice_id}/pdf-url")
def get_invoice_pdf_url(invoice_id: int):

    invoice = get_invoice_by_id(invoice_id)

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found."
        )

    file_path = invoice.get("file_path")

    if not file_path:
        raise HTTPException(
            status_code=404,
            detail="Original invoice PDF is not available."
        )

    signed_url = create_invoice_signed_url(
        file_path=file_path,
        expires_in=SIGNED_URL_EXPIRATION
    )

    if not signed_url:
        raise HTTPException(
            status_code=502,
            detail="Could not generate a temporary PDF URL."
        )

    return {
        "invoice_id": invoice_id,
        "url": signed_url,
        "expires_in": SIGNED_URL_EXPIRATION
    }


@app.get("/invoices/{invoice_id}/pdf")
def view_invoice_pdf(invoice_id: int):

    invoice = get_invoice_by_id(invoice_id)

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found."
        )

    file_path = invoice.get("file_path")

    if not file_path:
        raise HTTPException(
            status_code=404,
            detail="Original invoice PDF is not available."
        )

    # Download PDF directly from private Supabase Storage
    pdf_content = download_invoice_pdf(file_path)

    if not pdf_content:
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve the original invoice PDF."
        )

    # Use original filename when available
    file_name = (
        invoice.get("file_name")
        or f"invoice_{invoice_id}.pdf"
    )

    # Prevent invalid characters in HTTP headers
    safe_file_name = (
        file_name
        .replace('"', "")
        .replace("\r", "")
        .replace("\n", "")
    )

    # Serve PDF directly in the browser
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'inline; filename="{safe_file_name}"'
            ),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff"
        }
    )


# ---------------------------------------------------------
# Invoice human review
# ---------------------------------------------------------

@app.patch("/invoices/{invoice_id}/status")
def change_invoice_status(
    invoice_id: int,
    status_update: InvoiceStatusUpdate
):

    # Check if invoice exists
    invoice = get_invoice_by_id(invoice_id)

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found."
        )

    # Store previous status before updating
    previous_status = invoice.get("status")

    # Update invoice status in Supabase
    updated_invoice = update_invoice_status(
        invoice_id,
        status_update.status
    )

    if not updated_invoice:
        raise HTTPException(
            status_code=500,
            detail="Failed to update invoice status."
        )

    # Register the human review decision
    create_audit_log(
        event_type=status_update.status,
        invoice_id=invoice_id,
        source="human_review",
        file_name=updated_invoice.get("file_name"),
        file_hash=updated_invoice.get("file_hash"),
        details={
            "previous_status": previous_status,
            "new_status": status_update.status
        }
    )

    # Dispatch status change event to Make
    make_result = send_make_event(
        event_type="invoice_status_changed",
        invoice=updated_invoice
    )

    # Register Make dispatch result
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
            "error": make_result["error"]
        }
    )

    return {
        "message": "Invoice status updated successfully.",
        "invoice": updated_invoice,
        "automation_dispatched": make_result["dispatched"]
    }


# ---------------------------------------------------------
# Invoice validation
# ---------------------------------------------------------

@app.post("/invoices/validate")
def validate_invoice(invoice: InvoiceData):

    validation_result = validate_invoice_business_rules(invoice)

    return {
        "invoice": invoice,
        "validation": validation_result
    }


# ---------------------------------------------------------
# AI invoice processing
# ---------------------------------------------------------

@app.post("/invoices/extract")
async def extract_invoice(file: UploadFile = File(...)):

    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )

    # Read file
    content = await file.read()

    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty."
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File is too large. Maximum size is 10 MB."
        )

    file_name = file.filename or "invoice.pdf"

    # Generate SHA-256 fingerprint
    file_hash = hashlib.sha256(content).hexdigest()

    # Register that the invoice document was received
    create_audit_log(
        event_type="invoice_received",
        source="api",
        file_name=file_name,
        file_hash=file_hash,
        details={
            "content_type": file.content_type,
            "size_bytes": len(content)
        }
    )

    # Check if exactly the same PDF was already processed
    existing_invoice = find_invoice_by_hash(file_hash)

    if existing_invoice:

        create_audit_log(
            event_type="duplicate_detected",
            invoice_id=existing_invoice["id"],
            source="api",
            file_name=file_name,
            file_hash=file_hash,
            details={
                "reason": "file_hash",
                "message": "This PDF has already been processed."
            }
        )

        raise HTTPException(
            status_code=409,
            detail={
                "status": "duplicate",
                "reason": "file_hash",
                "message": "This PDF has already been processed.",
                "invoice_id": existing_invoice["id"]
            }
        )

    # Extract raw text from PDF
    extracted_text = extract_text_from_pdf(content)

    if not extracted_text.strip():
        raise HTTPException(
            status_code=422,
            detail="No readable text was found in the PDF."
        )

    try:
        # Convert PDF text into structured invoice data using AI
        invoice = extract_invoice_data(extracted_text)

    except ValidationError:
        raise HTTPException(
            status_code=422,
            detail=(
                "The uploaded PDF does not contain a valid invoice "
                "or the required invoice fields could not be extracted."
            )
        )

    except Exception:
        raise HTTPException(
            status_code=502,
            detail=(
                "The invoice could not be processed by the AI service. "
                "Please try again later."
            )
        )

    # Register successful AI extraction
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
            "currency": invoice.currency
        }
    )

    # Check if same supplier + invoice number already exists
    existing_invoice = find_invoice_by_number(
        invoice.supplier_vat_number,
        invoice.invoice_number
    )

    if existing_invoice:

        create_audit_log(
            event_type="duplicate_detected",
            invoice_id=existing_invoice["id"],
            source="api",
            file_name=file_name,
            file_hash=file_hash,
            details={
                "reason": "invoice_number",
                "supplier_vat_number": invoice.supplier_vat_number,
                "invoice_number": invoice.invoice_number,
                "message": (
                    "An invoice with this supplier and "
                    "invoice number already exists."
                )
            }
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
                "invoice_id": existing_invoice["id"]
            }
        )

    # Apply business validation rules
    validation_result = validate_invoice_business_rules(invoice)

    # Register business validation result
    create_audit_log(
        event_type="validation_completed",
        source="validation",
        file_name=file_name,
        file_hash=file_hash,
        details={
            "is_valid": validation_result["is_valid"],
            "status": validation_result["status"],
            "errors": validation_result["errors"]
        }
    )

    # Build private Supabase Storage path
    file_path = build_invoice_file_path(
        supplier_vat_number=invoice.supplier_vat_number,
        invoice_number=invoice.invoice_number,
        original_filename=file_name
    )

    # Upload original PDF to private Supabase Storage
    stored_file_path = upload_invoice_pdf(
        file_path=file_path,
        content=content
    )

    if not stored_file_path:

        create_audit_log(
            event_type="document_storage_failed",
            source="storage",
            file_name=file_name,
            file_hash=file_hash,
            details={
                "bucket": "invoice-documents",
                "file_path": file_path
            }
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "The invoice was extracted successfully, but the "
                "original PDF could not be stored."
            )
        )

    # Save invoice in Supabase database
    saved_invoice = save_invoice(
        file_name=file_name,
        file_hash=file_hash,
        invoice=invoice,
        validation=validation_result,
        file_path=stored_file_path
    )

    # Register successful PDF storage
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
            "size_bytes": len(content)
        }
    )

    # Register invoice creation
    create_audit_log(
        event_type="invoice_created",
        invoice_id=saved_invoice["id"],
        source="api",
        file_name=file_name,
        file_hash=file_hash,
        details={
            "status": saved_invoice["status"],
            "supplier_name": saved_invoice["supplier_name"],
            "supplier_vat_number": saved_invoice["supplier_vat_number"],
            "invoice_number": saved_invoice["invoice_number"],
            "total": saved_invoice["total"],
            "currency": saved_invoice["currency"],
            "file_path": saved_invoice.get("file_path")
        }
    )

    # Dispatch processed invoice event to Make
    make_result = send_make_event(
        event_type="invoice_processed",
        invoice=saved_invoice
    )

    # Register Make dispatch result
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
            "invoice_status": saved_invoice["status"],
            "dispatched": make_result["dispatched"],
            "http_status": make_result["status_code"],
            "error": make_result["error"]
        }
    )

    return {
        "status": "processed",
        "database_id": saved_invoice["id"],
        "filename": file_name,
        "sha256": file_hash,
        "invoice": invoice.model_dump(mode="json"),
        "validation": validation_result,
        "file_path": stored_file_path,
        "automation_dispatched": make_result["dispatched"]
    }


# ---------------------------------------------------------
# Raw PDF upload / extraction test
# ---------------------------------------------------------

@app.post("/invoices/upload")
async def upload_invoice(file: UploadFile = File(...)):

    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )

    # Read file
    content = await file.read()

    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty."
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File is too large. Maximum size is 10 MB."
        )

    file_name = file.filename or "invoice.pdf"

    # Generate SHA-256 hash
    file_hash = hashlib.sha256(content).hexdigest()

    # Extract text from PDF
    extracted_text = extract_text_from_pdf(content)

    return {
        "status": "received",
        "filename": file_name,
        "content_type": file.content_type,
        "size_bytes": len(content),
        "sha256": file_hash,
        "text_extracted": bool(extracted_text),
        "text_preview": extracted_text[:500]
    }