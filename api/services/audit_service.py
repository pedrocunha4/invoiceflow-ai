import logging
from typing import Any, Dict, Optional

from api.services.supabase_client import get_supabase_client


logger = logging.getLogger(__name__)


def create_audit_log(
    event_type: str,
    invoice_id: Optional[int] = None,
    source: str = "api",
    file_name: Optional[str] = None,
    file_hash: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Create an audit log entry in Supabase.

    Audit logging is intentionally non-blocking:
    a logging failure must never interrupt the main invoice workflow.
    """

    data = {
        "invoice_id": invoice_id,
        "event_type": event_type,
        "source": source,
        "file_name": file_name,
        "file_hash": file_hash,
        "details": details or {}
    }

    try:
        supabase = get_supabase_client()

        response = (
            supabase
            .table("audit_logs")
            .insert(data)
            .execute()
        )

        if response.data:
            return response.data[0]

        return None

    except Exception as exc:
        logger.warning(
            "Audit log could not be created: %s",
            exc.__class__.__name__
        )

        return None