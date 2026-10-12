from typing import Any, Dict, Optional

from api.services.database_service import supabase


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

    Audit logging should not interrupt the main invoice workflow
    if the log cannot be created.
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
        response = (
            supabase
            .table("audit_logs")
            .insert(data)
            .execute()
        )

        if response.data:
            return response.data[0]

        return None

    except Exception:
        return None