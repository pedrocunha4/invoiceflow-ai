from datetime import date
from pydantic import BaseModel, Field


class InvoiceData(BaseModel):
    supplier_name: str = Field(
        ...,
        min_length=1,
        description="Supplier/company name"
    )

    supplier_vat_number: str = Field(
        ...,
        min_length=9,
        max_length=20,
        description="Supplier VAT identification number"
    )

    invoice_number: str = Field(
        ...,
        min_length=1,
        description="Invoice unique number"
    )

    invoice_date: date

    subtotal: float = Field(..., ge=0)

    vat_amount: float = Field(..., ge=0)

    total: float = Field(..., ge=0)

    currency: str = Field(
        default="EUR",
        min_length=3,
        max_length=3
    )