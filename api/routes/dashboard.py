from __future__ import annotations

from fastapi import APIRouter

from api.core.errors import database_http_exception
from api.services.database_service import (
    DatabaseServiceError,
    get_invoice_stats,
)
from api.services.supabase_client import (
    SupabaseConfigurationError,
)

router = APIRouter()


@router.get("/dashboard/stats")
def dashboard_stats():
    try:
        return get_invoice_stats()

    except (
        SupabaseConfigurationError,
        DatabaseServiceError,
    ) as exc:
        raise database_http_exception(exc)