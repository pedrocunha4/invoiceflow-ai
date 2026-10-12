import os
from datetime import datetime, timezone
from typing import Any, Dict

import requests
from dotenv import load_dotenv


load_dotenv()

MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")
MAKE_WEBHOOK_API_KEY = os.getenv("MAKE_WEBHOOK_API_KEY")


def send_make_event(
    event_type: str,
    invoice: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Send an invoice event to the Make webhook.

    A successful HTTP response only means that Make accepted
    the webhook request. It does not guarantee that the Make
    scenario completed successfully.
    """

    if not MAKE_WEBHOOK_URL or not MAKE_WEBHOOK_API_KEY:
        return {
            "dispatched": False,
            "status_code": None,
            "error": "Make webhook is not configured."
        }

    payload = {
        "event": event_type,
        "source": "invoiceflow-ai",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "invoice": invoice
    }

    headers = {
        "Content-Type": "application/json",
        "x-make-apikey": MAKE_WEBHOOK_API_KEY
    }

    try:
        response = requests.post(
            MAKE_WEBHOOK_URL,
            json=payload,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

        return {
            "dispatched": True,
            "status_code": response.status_code,
            "error": None
        }

    except requests.RequestException as exc:
        status_code = (
            exc.response.status_code
            if exc.response is not None
            else None
        )

        return {
            "dispatched": False,
            "status_code": status_code,
            "error": str(exc)
        }