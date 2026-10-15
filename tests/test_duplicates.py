from datetime import date

from fastapi.testclient import TestClient

from api.main import app
from api.models.invoice import InvoiceData

client = TestClient(
    app,
    headers={
        "X-API-Key": "test-api-key",
    },
)


def test_duplicate_invoice_by_file_hash(
    monkeypatch,
):

    existing_invoice = {
        "id": 25,
        "file_hash": "existing-hash",
    }

    monkeypatch.setattr(
        "api.services.invoice_processing_service.find_invoice_by_hash",
        lambda file_hash: existing_invoice,
    )

    monkeypatch.setattr(
        "api.services.invoice_processing_service.create_audit_log",
        lambda **kwargs: None,
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

    assert response.status_code == 409

    detail = response.json()["detail"]

    assert detail["status"] == "duplicate"
    assert detail["reason"] == "file_hash"
    assert detail["invoice_id"] == 25


def test_duplicate_invoice_by_invoice_number(
    monkeypatch,
):

    extracted_invoice = InvoiceData(
        supplier_name="Tech Solutions Lda",
        supplier_vat_number="PT509123456",
        invoice_number="FT-2026-001",
        invoice_date=date(2026, 10, 13),
        subtotal=100.00,
        vat_amount=23.00,
        total=123.00,
        currency="EUR",
    )

    existing_invoice = {
        "id": 50,
        "supplier_vat_number": "PT509123456",
        "invoice_number": "FT-2026-001",
    }

    monkeypatch.setattr(
        "api.services.invoice_processing_service.create_audit_log",
        lambda **kwargs: None,
    )

    monkeypatch.setattr(
        "api.services.invoice_processing_service.find_invoice_by_hash",
        lambda file_hash: None,
    )

    monkeypatch.setattr(
        "api.services.invoice_processing_service.extract_text_from_pdf",
        lambda content: "Fake invoice text",
    )

    monkeypatch.setattr(
        "api.services.invoice_processing_service.extract_invoice_data",
        lambda text: extracted_invoice,
    )

    monkeypatch.setattr(
        "api.services.invoice_processing_service.find_invoice_by_number",
        lambda supplier_vat_number, invoice_number:
            existing_invoice,
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

    assert response.status_code == 409

    detail = response.json()["detail"]

    assert detail["status"] == "duplicate"
    assert detail["reason"] == "invoice_number"
    assert detail["invoice_id"] == 50