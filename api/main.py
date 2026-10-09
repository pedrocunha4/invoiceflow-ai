from fastapi import FastAPI, UploadFile, File, HTTPException
from api.services.pdf_service import extract_text_from_pdf
from api.models.invoice import InvoiceData
from api.services.ai_service import extract_invoice_data
from api.services.invoice_validation_service import validate_invoice_business_rules
import hashlib


app = FastAPI(
    title="InvoiceFlow AI API",
    description="API for intelligent invoice processing and automation.",
    version="0.1.0"
)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


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


@app.post("/invoices/validate")
def validate_invoice(invoice: InvoiceData):

    validation_result = validate_invoice_business_rules(invoice)

    return {
        "invoice": invoice,
        "validation": validation_result
    }


@app.post("/invoices/extract")
async def extract_invoice(file: UploadFile = File(...)):

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )

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

    # Extract raw text from PDF
    extracted_text = extract_text_from_pdf(content)

    if not extracted_text.strip():
        raise HTTPException(
            status_code=422,
            detail="No readable text was found in the PDF."
        )

    try:
        # Convert unstructured PDF text into structured invoice data
        invoice = extract_invoice_data(extracted_text)

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"AI extraction failed: {str(error)}"
        )

    # Apply business validation rules
    validation_result = validate_invoice_business_rules(invoice)

    return {
        "status": "processed",
        "filename": file.filename,
        "invoice": invoice.model_dump(mode="json"),
        "validation": validation_result
    }


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