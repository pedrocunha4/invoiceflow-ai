from fastapi import FastAPI, UploadFile, File, HTTPException
from api.services.pdf_service import extract_text_from_pdf
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