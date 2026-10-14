from datetime import date

from fastapi.testclient import TestClient

from api.core.errors import (
    database_http_exception,
    storage_http_exception,
)
from api.main import app
from api.models.invoice import InvoiceData
from api.services.ai_service import (
    AIServiceUnavailableError,
)
from api.services.database_service import (
    DatabaseServiceError,
    DatabaseUnavailableError,
)
from api.services.storage_service import (
    StorageServiceError,
    StorageUnavailableError,
)
from api.services.supabase_client import (
    SupabaseConfigurationError,
)


client = TestClient(app)


# ---------------------------------------------------------
# Database error mapping
# ---------------------------------------------------------

def test_database_unavailable_returns_503():

    error = DatabaseUnavailableError(
        "Database unavailable"
    )

    http_error = database_http_exception(
        error
    )

    assert http_error.status_code == 503
    assert (
        "temporarily unavailable"
        in http_error.detail
    )


def test_database_operation_error_returns_502():

    error = DatabaseServiceError(
        "Database operation failed"
    )

    http_error = database_http_exception(
        error
    )

    assert http_error.status_code == 502


def test_database_configuration_error_returns_500():

    error = SupabaseConfigurationError(
        "Missing configuration"
    )

    http_error = database_http_exception(
        error
    )

    assert http_error.status_code == 500


# ---------------------------------------------------------
# Storage error mapping
# ---------------------------------------------------------

def test_storage_unavailable_returns_503():

    error = StorageUnavailableError(
        "Storage unavailable"
    )

    http_error = storage_http_exception(
        error
    )

    assert http_error.status_code == 503
    assert (
        "temporarily unavailable"
        in http_error.detail
    )


def test_storage_operation_error_returns_502():

    error = StorageServiceError(
        "Storage operation failed"
    )

    http_error = storage_http_exception(
        error
    )

    assert http_error.status_code == 502


# ---------------------------------------------------------
# AI error handling
# ---------------------------------------------------------

def test_ai_unavailable_returns_503(
    monkeypatch,
):

    monkeypatch.setattr(
        "api.routes.processing.create_audit_log",
        lambda **kwargs: None,
    )

    monkeypatch.setattr(
        "api.routes.processing.find_invoice_by_hash",
        lambda file_hash: None,
    )

    monkeypatch.setattr(
        "api.routes.processing.extract_text_from_pdf",
        lambda content: "Fake invoice text",
    )

    def raise_ai_unavailable(text):
        raise AIServiceUnavailableError(
            "AI unavailable"
        )

    monkeypatch.setattr(
        "api.routes.processing.extract_invoice_data",
        raise_ai_unavailable,
    )

    response = client.post(
        "/invoices/extract",
        files={
            "file": (
                "invoice.pdf",
                b"%PDF-1.4 fake invoice",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 503

    assert response.json()["detail"] == (
        "The AI service is temporarily unavailable. "
        "Please try again later."
    )


# ---------------------------------------------------------
# Storage rollback
# ---------------------------------------------------------

def test_pdf_is_deleted_when_database_save_fails(
    monkeypatch,
):

    extracted_invoice = InvoiceData(
        supplier_name="Tech Solutions Lda",
        supplier_vat_number="PT509123456",
        invoice_number="FT-2026-999",
        invoice_date=date(2026, 10, 13),
        subtotal=100.00,
        vat_amount=23.00,
        total=123.00,
        currency="EUR",
    )

    stored_path = (
        "2026/10/PT509123456/"
        "FT-2026-999__invoice.pdf"
    )

    deleted_files = []

    # Audit calls inside processing.py
    monkeypatch.setattr(
        "api.routes.processing.create_audit_log",
        lambda **kwargs: None,
    )

    # Audit calls performed by core error helpers
    monkeypatch.setattr(
        "api.core.errors.create_audit_log",
        lambda **kwargs: None,
    )

    # No duplicate by hash
    monkeypatch.setattr(
        "api.routes.processing.find_invoice_by_hash",
        lambda file_hash: None,
    )

    # Fake PDF extraction
    monkeypatch.setattr(
        "api.routes.processing.extract_text_from_pdf",
        lambda content: "Fake invoice text",
    )

    # Fake AI result
    monkeypatch.setattr(
        "api.routes.processing.extract_invoice_data",
        lambda text: extracted_invoice,
    )

    # No duplicate by invoice number
    monkeypatch.setattr(
        "api.routes.processing.find_invoice_by_number",
        lambda supplier_vat_number, invoice_number: None,
    )

    # Fake business validation
    monkeypatch.setattr(
        "api.routes.processing.validate_invoice_business_rules",
        lambda invoice: {
            "is_valid": True,
            "status": "approved",
            "errors": [],
        },
    )

    # Fake storage path
    monkeypatch.setattr(
        "api.routes.processing.build_invoice_file_path",
        lambda **kwargs: stored_path,
    )

    # Pretend Storage upload succeeded
    monkeypatch.setattr(
        "api.routes.processing.upload_invoice_pdf",
        lambda file_path, content: stored_path,
    )

    # Simulate database failure after Storage upload
    def fail_database_save(**kwargs):
        raise DatabaseServiceError(
            "Database insert failed"
        )

    monkeypatch.setattr(
        "api.routes.processing.save_invoice",
        fail_database_save,
    )

    # Capture rollback instead of touching Supabase
    def fake_delete_invoice_pdf(
        file_path,
    ):
        deleted_files.append(
            file_path
        )

    monkeypatch.setattr(
        "api.routes.processing.delete_invoice_pdf",
        fake_delete_invoice_pdf,
    )

    response = client.post(
        "/invoices/extract",
        files={
            "file": (
                "invoice.pdf",
                b"%PDF-1.4 fake invoice",
                "application/pdf",
            )
        },
    )

    # Database failure is returned safely
    assert response.status_code == 502

    # Most important assertion:
    # the uploaded PDF was removed
    assert deleted_files == [
        stored_path
    ]