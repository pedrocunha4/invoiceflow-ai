from __future__ import annotations

import hashlib

from fastapi import HTTPException
from pydantic import ValidationError

from api.core.errors import (
    audit_database_failure,
    audit_storage_failure,
    database_http_exception,
    storage_http_exception,
)
from api.services.ai_service import (
    AIConfigurationError,
    AIResponseError,
    AIServiceError,
    AIServiceUnavailableError,
    extract_invoice_data,
)
from api.services.audit_service import create_audit_log
from api.services.database_service import (
    DatabaseServiceError,
    find_invoice_by_hash,
    find_invoice_by_number,
    save_invoice,
)
from api.services.invoice_validation_service import (
    validate_invoice_business_rules,
)
from api.services.make_service import send_make_event
from api.services.pdf_service import extract_text_from_pdf
from api.services.storage_service import (
    StorageServiceError,
    build_invoice_file_path,
    delete_invoice_pdf,
    upload_invoice_pdf,
)
from api.services.supabase_client import (
    SupabaseConfigurationError,
)


def process_invoice_document(
    *,
    content: bytes,
    file_name: str,
    content_type: str,
) -> dict:
    """Run the complete invoice-processing workflow."""

    file_hash = hashlib.sha256(
        content,
    ).hexdigest()

    create_audit_log(
        event_type="invoice_received",
        source="api",
        file_name=file_name,
        file_hash=file_hash,
        details={
            "content_type": content_type,
            "size_bytes": len(content),
        },
    )

    # Duplicate check by file hash
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

    # PDF extraction
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

    # AI extraction
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
            "supplier_vat_number": (
                invoice.supplier_vat_number
            ),
            "invoice_number": invoice.invoice_number,
            "invoice_date": (
                invoice.invoice_date.isoformat()
            ),
            "subtotal": invoice.subtotal,
            "vat_amount": invoice.vat_amount,
            "total": invoice.total,
            "currency": invoice.currency,
        },
    )

    # Duplicate check by supplier + invoice number
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
                "supplier_vat_number": (
                    invoice.supplier_vat_number
                ),
                "invoice_number": (
                    invoice.invoice_number
                ),
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

    # Business validation

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
            "is_valid": (
                validation_result["is_valid"]
            ),
            "status": (
                validation_result["status"]
            ),
            "errors": (
                validation_result["errors"]
            ),
        },
    )

    # Document storage

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

    # Save invoice in database

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
        try:
            delete_invoice_pdf(
                stored_file_path,
            )

        except (
            SupabaseConfigurationError,
            StorageServiceError,
        ):
            pass

        audit_database_failure(
            operation="save_invoice",
            exc=exc,
            file_name=file_name,
            file_hash=file_hash,
        )

        raise database_http_exception(exc)

    # Audit successful document storage

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

    # Audit invoice creation

    create_audit_log(
        event_type="invoice_created",
        invoice_id=saved_invoice["id"],
        source="api",
        file_name=file_name,
        file_hash=file_hash,
        details={
            "status": (
                saved_invoice["status"]
            ),
            "supplier_name": (
                saved_invoice["supplier_name"]
            ),
            "supplier_vat_number": (
                saved_invoice["supplier_vat_number"]
            ),
            "invoice_number": (
                saved_invoice["invoice_number"]
            ),
            "total": (
                saved_invoice["total"]
            ),
            "currency": (
                saved_invoice["currency"]
            ),
            "file_path": (
                saved_invoice.get("file_path")
            ),
        },
    )

    # Make automation

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
            "invoice_status": (
                saved_invoice["status"]
            ),
            "dispatched": (
                make_result["dispatched"]
            ),
            "http_status": (
                make_result["status_code"]
            ),
            "error": (
                make_result["error"]
            ),
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
        "automation_dispatched": (
            make_result["dispatched"]
        ),
    }