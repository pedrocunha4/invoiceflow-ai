import logging
from typing import Any, Dict, List, Optional

import httpx

from api.models.invoice import InvoiceData
from api.services.supabase_client import (
    SupabaseConfigurationError,
    get_supabase_client,
)

logger = logging.getLogger(__name__)


# Database exceptions

class DatabaseServiceError(Exception):
    """Base exception for database operation failures."""


class DatabaseUnavailableError(DatabaseServiceError):
    """Temporary network or availability problem with Supabase."""


# Error handling

def _handle_database_error(
    operation: str,
    exc: Exception
) -> None:

    if isinstance(
        exc,
        (
            httpx.TimeoutException,
            httpx.RequestError,
        )
    ):
        logger.warning(
            "Supabase database unavailable during %s: %s",
            operation,
            exc.__class__.__name__
        )

        raise DatabaseUnavailableError(
            "The database service is temporarily unavailable."
        ) from exc

    logger.error(
        "Supabase database operation failed during %s: %s",
        operation,
        exc.__class__.__name__
    )

    raise DatabaseServiceError(
        "The database operation failed."
    ) from exc


# Invoice queries

def find_invoice_by_hash(
    file_hash: str
) -> Optional[Dict[str, Any]]:

    try:
        supabase = get_supabase_client()

        response = (
            supabase
            .table("invoices")
            .select("*")
            .eq("file_hash", file_hash)
            .limit(1)
            .execute()
        )

    except SupabaseConfigurationError:
        raise

    except Exception as exc:
        _handle_database_error(
            "find_invoice_by_hash",
            exc
        )

    if response.data:
        return response.data[0]

    return None


def find_invoice_by_number(
    supplier_vat_number: str,
    invoice_number: str
) -> Optional[Dict[str, Any]]:

    try:
        supabase = get_supabase_client()

        response = (
            supabase
            .table("invoices")
            .select("*")
            .eq(
                "supplier_vat_number",
                supplier_vat_number
            )
            .eq(
                "invoice_number",
                invoice_number
            )
            .limit(1)
            .execute()
        )

    except SupabaseConfigurationError:
        raise

    except Exception as exc:
        _handle_database_error(
            "find_invoice_by_number",
            exc
        )

    if response.data:
        return response.data[0]

    return None


def get_all_invoices() -> List[Dict[str, Any]]:

    try:
        supabase = get_supabase_client()

        response = (
            supabase
            .table("invoices")
            .select("*")
            .order(
                "created_at",
                desc=True
            )
            .execute()
        )

    except SupabaseConfigurationError:
        raise

    except Exception as exc:
        _handle_database_error(
            "get_all_invoices",
            exc
        )

    return response.data or []


def get_invoice_by_id(
    invoice_id: int
) -> Optional[Dict[str, Any]]:

    try:
        supabase = get_supabase_client()

        response = (
            supabase
            .table("invoices")
            .select("*")
            .eq(
                "id",
                invoice_id
            )
            .limit(1)
            .execute()
        )

    except SupabaseConfigurationError:
        raise

    except Exception as exc:
        _handle_database_error(
            "get_invoice_by_id",
            exc
        )

    if response.data:
        return response.data[0]

    return None


def save_invoice(
    file_name: str,
    file_hash: str,
    invoice: InvoiceData,
    validation: dict,
    file_path: Optional[str] = None
) -> Dict[str, Any]:

    data = {
        "file_name": file_name,
        "file_hash": file_hash,
        "file_path": file_path,

        "supplier_name":
            invoice.supplier_name,

        "supplier_vat_number":
            invoice.supplier_vat_number,

        "invoice_number":
            invoice.invoice_number,

        "invoice_date":
            invoice.invoice_date.isoformat(),

        "subtotal":
            invoice.subtotal,

        "vat_amount":
            invoice.vat_amount,

        "total":
            invoice.total,

        "currency":
            invoice.currency,

        "status":
            validation["status"],

        "validation_errors":
            validation["errors"]
    }

    try:
        supabase = get_supabase_client()

        response = (
            supabase
            .table("invoices")
            .insert(data)
            .execute()
        )

    except SupabaseConfigurationError:
        raise

    except Exception as exc:
        _handle_database_error(
            "save_invoice",
            exc
        )

    if not response.data:
        logger.error(
            "Supabase save_invoice returned no data."
        )

        raise DatabaseServiceError(
            "The database did not return the saved invoice."
        )

    return response.data[0]


def update_invoice_status(
    invoice_id: int,
    status: str
) -> Optional[Dict[str, Any]]:

    try:
        supabase = get_supabase_client()

        response = (
            supabase
            .table("invoices")
            .update({
                "status": status
            })
            .eq(
                "id",
                invoice_id
            )
            .execute()
        )

    except SupabaseConfigurationError:
        raise

    except Exception as exc:
        _handle_database_error(
            "update_invoice_status",
            exc
        )

    if response.data:
        return response.data[0]

    return None



# Dashboard stats

def get_invoice_stats() -> Dict[str, Any]:

    try:
        supabase = get_supabase_client()

        response = (
            supabase
            .table("invoices")
            .select(
                "status,total"
            )
            .execute()
        )

    except SupabaseConfigurationError:
        raise

    except Exception as exc:
        _handle_database_error(
            "get_invoice_stats",
            exc
        )

    invoices = response.data or []

    approved = 0
    needs_review = 0
    rejected = 0
    total_amount = 0.0

    for invoice in invoices:

        status = invoice.get("status")

        if status == "approved":
            approved += 1

        elif status == "needs_review":
            needs_review += 1

        elif status == "rejected":
            rejected += 1

        try:
            total_amount += float(
                invoice.get("total") or 0
            )

        except (TypeError, ValueError):
            logger.warning(
                "Invalid invoice total encountered "
                "while calculating dashboard statistics."
            )

    return {
        "total_invoices": len(invoices),
        "approved": approved,
        "needs_review": needs_review,
        "rejected": rejected,
        "total_amount": round(
            total_amount,
            2
        )
    }