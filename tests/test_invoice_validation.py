from datetime import date

from api.models.invoice import InvoiceData
from api.services.invoice_validation_service import (
    validate_invoice_business_rules,
)


def create_invoice(
    subtotal: float,
    vat_amount: float,
    total: float,
) -> InvoiceData:

    return InvoiceData(
        supplier_name="Tech Solutions Lda",
        supplier_vat_number="PT509123456",
        invoice_number="FT-2026-001",
        invoice_date=date(2026, 10, 13),
        subtotal=subtotal,
        vat_amount=vat_amount,
        total=total,
        currency="EUR",
    )


def test_invoice_total_is_valid():

    invoice = create_invoice(
        subtotal=100.00,
        vat_amount=23.00,
        total=123.00,
    )

    result = validate_invoice_business_rules(
        invoice
    )

    assert result["is_valid"] is True
    assert result["status"] == "approved"
    assert result["errors"] == []


def test_invoice_total_mismatch_requires_review():

    invoice = create_invoice(
        subtotal=100.00,
        vat_amount=23.00,
        total=130.00,
    )

    result = validate_invoice_business_rules(
        invoice
    )

    assert result["is_valid"] is False
    assert result["status"] == "needs_review"
    assert len(result["errors"]) > 0


def test_invoice_total_with_decimals():

    invoice = create_invoice(
        subtotal=99.99,
        vat_amount=23.00,
        total=122.99,
    )

    result = validate_invoice_business_rules(
        invoice
    )

    assert result["is_valid"] is True
    assert result["errors"] == []