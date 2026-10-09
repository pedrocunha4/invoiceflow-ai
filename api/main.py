import hashlib

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from api.models.invoice import InvoiceData
from api.models.invoice_status import InvoiceStatusUpdate

from api.services.ai_service import extract_invoice_data
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


app = FastAPI(
    title="InvoiceFlow AI API",
    description="API for intelligent invoice processing and automation.",
    version="0.1.0",
    docs_url=None
)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


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
# Invoice human review
# ---------------------------------------------------------

@app.patch("/invoices/{invoice_id}/status")
def change_invoice_status(
    invoice_id: int,
    status_update: InvoiceStatusUpdate
):

    invoice = get_invoice_by_id(invoice_id)

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found."
        )

    updated_invoice = update_invoice_status(
        invoice_id,
        status_update.status
    )

    if not updated_invoice:
        raise HTTPException(
            status_code=500,
            detail="Failed to update invoice status."
        )

    return {
        "message": "Invoice status updated successfully.",
        "invoice": updated_invoice
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

    # Generate SHA-256 fingerprint
    file_hash = hashlib.sha256(content).hexdigest()

    # Check if exactly the same PDF was already processed
    existing_invoice = find_invoice_by_hash(file_hash)

    if existing_invoice:
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

    # Check if same supplier + invoice number already exists
    existing_invoice = find_invoice_by_number(
        invoice.supplier_vat_number,
        invoice.invoice_number
    )

    if existing_invoice:
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

    # Save invoice in Supabase
    saved_invoice = save_invoice(
        file_name=file.filename,
        file_hash=file_hash,
        invoice=invoice,
        validation=validation_result
    )

    return {
        "status": "processed",
        "database_id": saved_invoice["id"],
        "filename": file.filename,
        "sha256": file_hash,
        "invoice": invoice.model_dump(mode="json"),
        "validation": validation_result
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

    # Generate SHA-256 hash
    file_hash = hashlib.sha256(content).hexdigest()

    # Extract text from PDF
    extracted_text = extract_text_from_pdf(content)

    return {
        "status": "received",
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(content),
        "sha256": file_hash,
        "text_extracted": bool(extracted_text),
        "text_preview": extracted_text[:500]
    }