from datetime import date

import pytest
from pydantic import ValidationError

from api.models.invoice import InvoiceData


def test_valid_invoice_model():

    invoice = InvoiceData(
        supplier_name="Tech Solutions Lda",
        supplier_vat_number="PT509123456",
        invoice_number="FT-2026-001",
        invoice_date=date(2026, 10, 13),
        subtotal=100.00,
        vat_amount=23.00,
        total=123.00,
        currency="EUR",
    )

    assert invoice.supplier_name == "Tech Solutions Lda"
    assert invoice.supplier_vat_number == "PT509123456"
    assert invoice.invoice_number == "FT-2026-001"
    assert invoice.subtotal == 100.00
    assert invoice.vat_amount == 23.00
    assert invoice.total == 123.00
    assert invoice.currency == "EUR"


def test_negative_total_is_rejected():

    with pytest.raises(ValidationError):

        InvoiceData(
            supplier_name="Tech Solutions Lda",
            supplier_vat_number="PT509123456",
            invoice_number="FT-2026-001",
            invoice_date=date(2026, 10, 13),
            subtotal=100.00,
            vat_amount=23.00,
            total=-123.00,
            currency="EUR",
        )


def test_invalid_currency_length_is_rejected():

    with pytest.raises(ValidationError):

        InvoiceData(
            supplier_name="Tech Solutions Lda",
            supplier_vat_number="PT509123456",
            invoice_number="FT-2026-001",
            invoice_date=date(2026, 10, 13),
            subtotal=100.00,
            vat_amount=23.00,
            total=123.00,
            currency="EU",
        )


def test_invalid_invoice_date_is_rejected():

    with pytest.raises(ValidationError):

        InvoiceData(
            supplier_name="Tech Solutions Lda",
            supplier_vat_number="PT509123456",
            invoice_number="FT-2026-001",
            invoice_date="not-a-date",
            subtotal=100.00,
            vat_amount=23.00,
            total=123.00,
            currency="EUR",
        )