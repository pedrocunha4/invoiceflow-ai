from __future__ import annotations

import hashlib

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
)

from api.services.invoice_processing_service import (
    process_invoice_document,
)
from api.services.pdf_service import extract_text_from_pdf


router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/invoices/extract")
async def extract_invoice(
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
            detail=(
                "File is too large. Maximum size is 10 MB."
            ),
        )

    file_name = (
        file.filename
        or "invoice.pdf"
    )

    return process_invoice_document(
        content=content,
        file_name=file_name,
        content_type=file.content_type,
    )


@router.post("/invoices/upload")
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
            detail=(
                "File is too large. Maximum size is 10 MB."
            ),
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
        "text_extracted": bool(
            extracted_text
        ),
        "text_preview": (
            extracted_text[:500]
        ),
    }