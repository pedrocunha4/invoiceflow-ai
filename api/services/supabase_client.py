import logging
import os
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

logger = logging.getLogger(__name__)


class SupabaseConfigurationError(Exception):
    """Supabase configuration is missing or invalid."""


_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Return a shared Supabase client.

    The client is created lazily so a configuration problem does not
    crash the application during module import.
    """

    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SECRET_KEY")

    if not supabase_url or not supabase_key:
        logger.error(
            "Supabase configuration error: required environment "
            "variables are missing."
        )

        raise SupabaseConfigurationError(
            "Supabase is not configured."
        )

    try:
        _supabase_client = create_client(
            supabase_url,
            supabase_key
        )

        return _supabase_client

    except Exception as exc:
        logger.error(
            "Supabase client initialization failed: %s",
            exc.__class__.__name__
        )

        raise SupabaseConfigurationError(
            "Supabase could not be initialized."
        ) from exc