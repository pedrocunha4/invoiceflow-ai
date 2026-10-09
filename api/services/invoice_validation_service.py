from api.models.invoice import InvoiceData


def validate_invoice_business_rules(invoice: InvoiceData) -> dict:
    errors = []

    expected_total = round(invoice.subtotal + invoice.vat_amount, 2)
    actual_total = round(invoice.total, 2)

    if expected_total != actual_total:
        errors.append(
            f"Total mismatch: expected {expected_total:.2f} "
            f"but received {actual_total:.2f}."
        )

    if errors:
        return {
            "is_valid": False,
            "status": "needs_review",
            "errors": errors
        }

    return {
        "is_valid": True,
        "status": "approved",
        "errors": []
    }