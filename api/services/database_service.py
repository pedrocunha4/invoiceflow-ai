import os

from dotenv import load_dotenv
from supabase import create_client, Client

from api.models.invoice import InvoiceData


load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SECRET_KEY")

if not supabase_url or not supabase_key:
    raise RuntimeError(
        "SUPABASE_URL or SUPABASE_SECRET_KEY was not found."
    )

supabase: Client = create_client(
    supabase_url,
    supabase_key
)


def find_invoice_by_hash(file_hash: str):
    response = (
        supabase
        .table("invoices")
        .select("*")
        .eq("file_hash", file_hash)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def find_invoice_by_number(
    supplier_vat_number: str,
    invoice_number: str
):
    response = (
        supabase
        .table("invoices")
        .select("*")
        .eq("supplier_vat_number", supplier_vat_number)
        .eq("invoice_number", invoice_number)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def get_all_invoices():
    response = (
        supabase
        .table("invoices")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    return response.data


def get_invoice_by_id(invoice_id: int):
    response = (
        supabase
        .table("invoices")
        .select("*")
        .eq("id", invoice_id)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def save_invoice(
    file_name: str,
    file_hash: str,
    invoice: InvoiceData,
    validation: dict
):
    data = {
        "file_name": file_name,
        "file_hash": file_hash,

        "supplier_name": invoice.supplier_name,
        "supplier_vat_number": invoice.supplier_vat_number,
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.invoice_date.isoformat(),

        "subtotal": invoice.subtotal,
        "vat_amount": invoice.vat_amount,
        "total": invoice.total,
        "currency": invoice.currency,

        "status": validation["status"],
        "validation_errors": validation["errors"]
    }

    response = (
        supabase
        .table("invoices")
        .insert(data)
        .execute()
    )

    return response.data[0]


def update_invoice_status(
    invoice_id: int,
    status: str
):
    response = (
        supabase
        .table("invoices")
        .update({
            "status": status
        })
        .eq("id", invoice_id)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None